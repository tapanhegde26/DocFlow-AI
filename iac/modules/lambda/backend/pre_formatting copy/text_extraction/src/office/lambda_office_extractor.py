import json
import boto3
import zipfile
import io
import os
import tempfile
import uuid
import xml.etree.ElementTree as ET
import re
import hashlib
from datetime import datetime
from collections import defaultdict

# Import libraries with error handling
try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    print("Warning: openpyxl not available")

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: PIL/pytesseract not available")

s3_client = boto3.client('s3')

# Configuration
MAX_RESPONSE_SIZE = 100 * 1024  # 100KB
EXTRACTED_TEXT_BUCKET = os.environ.get('EXTRACTED_TEXT_BUCKET', 'default-extracted-text-bucket')
MAX_IMAGES_TO_PROCESS = 100

def generate_content_hash(extracted_text_by_page):
    """Generate SHA-256 hash of extracted text content"""
    try:
        # Combine all text from all pages
        combined_text = ""
        for page_data in extracted_text_by_page:
            combined_text += page_data.get('text', '')
        
        # Normalize text (remove extra whitespace, convert to lowercase)
        normalized_text = ' '.join(combined_text.split()).lower()
        
        # Generate SHA-256 hash
        content_hash = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
        
        print(f"Generated content hash: {content_hash} for text length: {len(normalized_text)}")
        return content_hash
    
    except Exception as e:
        print(f"Error generating content hash: {str(e)}")
        # Return a default hash if error occurs
        return hashlib.sha256(b"error_generating_hash").hexdigest()

def lambda_handler(event, context):
    try:
        # Handle nested body structure
        if 'body' in event:
            event_data = event['body'] if isinstance(event['body'], dict) else event
        else:
            event_data = event

        s3_bucket = event_data.get('bucket_name') or event_data.get('s3_bucket')
        s3_key = event_data.get('object_key') or event_data.get('s3_key')
        txn_id = event_data.get('txn_id'),
        file_type = event_data.get('file_type', '').lower()
        file_size = event_data.get('file_size', 0)
        # Extract client name from object_key
        #client_name = os.path.splitext(os.path.basename(s3_key))[0]
        client_name = event_data.get('client_name')
        print(f"Extracted client name: {client_name}")
        if not s3_bucket or not s3_key:
            raise ValueError("Missing required parameters: bucket_name and object_key")

        if file_type not in ['docx', 'xlsx', 'pptx']:
            raise ValueError(f"This function only handles Office files (docx, xlsx, pptx), received: {file_type}")

        print(f"Processing Office file: {s3_bucket}/{s3_key}, type: {file_type}, size: {file_size} bytes")

        # Create folder structure
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        original_filename = os.path.splitext(os.path.basename(s3_key))[0]
        base_folder = f"{timestamp}_{uuid.uuid4().hex[:8]}_{original_filename}"
        text_folder = f"{client_name}/{base_folder}/extracted_text"
        images_folder = f"{client_name}/{base_folder}/extracted_images"

        # Get file content
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        file_content = response['Body'].read()

        # Extract text and images from Office document
        extracted_text_by_page, extracted_images = extract_office_content(file_content, file_type)
        
        # Generate content hash for duplicate detection
        content_hash = generate_content_hash(extracted_text_by_page)

        # Group images by page/slide (similar to PDF logic)
        images_by_page = defaultdict(list)
        for img_data in extracted_images:
            page_num = img_data.get('page', img_data.get('slide_number', 1))
            images_by_page[page_num].append(img_data)

        # Store extracted text files and combine with image data
        combined_page_data = []
        total_images = 0

        for i, page_data in enumerate(extracted_text_by_page):
            page_num = page_data.get('page', i+1)
            
            # Store text file
            text_key = f"{text_folder}/page_{page_num}.txt"
            #text_key = ""
            s3_client.put_object(
                Bucket=EXTRACTED_TEXT_BUCKET,
                Key=text_key,
                Body=page_data['text'].encode('utf-8'),
                ContentType='text/plain'
            )

            # Store images for this page/slide and create image details
            page_images = images_by_page.get(page_num, [])
            image_details = []
            
            for img_data in page_images:
                img_key = f"{images_folder}/{img_data['filename']}"
                s3_client.put_object(
                    Bucket=EXTRACTED_TEXT_BUCKET,
                    Key=img_key,
                    Body=img_data['data'],
                    ContentType=img_data.get('content_type', 'image/png')
                )
                
                image_details.append({
                    "filename": img_data['filename'],
                    "s3_path": f"s3://{EXTRACTED_TEXT_BUCKET}/{img_key}",
                    "detected_text": img_data.get('detected_text', ''),
                    "text_length": img_data.get('text_length', 0),
                    "size_bytes": img_data.get('size_bytes', 0),
                    "width": img_data.get('width', 0),
                    "height": img_data.get('height', 0),
                    "content_type": img_data.get('content_type', 'image/png')
                })
                total_images += 1

            # Combine text and image data for this page (similar to PDF structure)
            page_entry = {
                "page": page_num,
                "text_s3_path": f"s3://{EXTRACTED_TEXT_BUCKET}/{text_key}",
                "text": page_data['text'],
                "image_details": image_details,
                "image_count": len(image_details)
            }
            
            # Add file-type specific fields
            if file_type == 'xlsx':
                page_entry["sheet_name"] = page_data.get('sheet_name', f'Sheet{page_num}')
            elif file_type == 'pptx':
                page_entry["slide_number"] = page_data.get('slide_number', page_num)
            
            combined_page_data.append(page_entry)
        """
        # Create summary JSON (matching PDF structure)
        summary = {
            'status': 'SUCCESS',
            'file_type': file_type,
            'original_file': f"s3://{s3_bucket}/{s3_key}",
            'timestamp_text_extraction': datetime.utcnow().isoformat(),
            'text_s3_bucket':f"s3://{EXTRACTED_TEXT_BUCKET}",
            'text_s3_key': text_key,
            'txn_id' : txn_id,
            'client_name' : client_name,
            'total_pages': len(extracted_text_by_page),
            'total_images': total_images,
            'text_folder': f"s3://{EXTRACTED_TEXT_BUCKET}/{text_folder}/",
            'images_folder': f"s3://{EXTRACTED_TEXT_BUCKET}/{images_folder}/",
            'extracted_text_by_page': combined_page_data
        }

        # Store summary JSON
        summary_key = f"{client_name}/{base_folder}/extraction_summary.json"
        s3_client.put_object(
            Bucket=EXTRACTED_TEXT_BUCKET,
            Key=summary_key,
            Body=json.dumps(summary, indent=2).encode('utf-8'),
            ContentType='application/json'
        )

        return {
            'statusCode': 200,
            'body': {
                **summary,
                'summary_s3_path': f"s3://{EXTRACTED_TEXT_BUCKET}/{summary_key}"
            }
        }
        """
            # Create FULL summary JSON with all data (for S3 storage)
        full_summary = {
            'status': 'SUCCESS',
            'file_type': file_type,
            'original_file': f"s3://{s3_bucket}/{s3_key}",
            'timestamp_text_extraction': datetime.utcnow().isoformat(),
            'text_s3_bucket': f"s3://{EXTRACTED_TEXT_BUCKET}",
            'text_s3_key': text_key,
            'txn_id': txn_id,
            'content_hash': content_hash,
            'client_name': client_name,
            'total_pages': len(extracted_text_by_page),
            'total_images': total_images,
            'text_folder': f"s3://{EXTRACTED_TEXT_BUCKET}/{text_folder}/",
            'images_folder': f"s3://{EXTRACTED_TEXT_BUCKET}/{images_folder}/",
            'extracted_text_by_page': combined_page_data  # This contains all the large text data
        }

        # Store FULL summary JSON in S3
        summary_key = f"{client_name}/{base_folder}/extraction_summary.json"
        s3_client.put_object(
            Bucket=EXTRACTED_TEXT_BUCKET,
            Key=summary_key,
            Body=json.dumps(full_summary, indent=2).encode('utf-8'),
            ContentType='application/json'
        )

        # Create LIGHTWEIGHT response for Step Functions (without large text content)
        lightweight_response = {
            'status': 'SUCCESS',
            'file_type': file_type,
            'original_file': f"s3://{s3_bucket}/{s3_key}",
            'timestamp_text_extraction': datetime.utcnow().isoformat(),
            'text_s3_bucket': f"s3://{EXTRACTED_TEXT_BUCKET}",
            'text_s3_key': text_key,
            'txn_id': txn_id,
            'content_hash': content_hash,
            'content_hash': content_hash,
            'client_name': client_name,
            'total_pages': len(extracted_text_by_page),
            'total_images': total_images,
            'text_folder': f"s3://{EXTRACTED_TEXT_BUCKET}/{text_folder}/",
            'images_folder': f"s3://{EXTRACTED_TEXT_BUCKET}/{images_folder}/",
            'summary_s3_path': f"s3://{EXTRACTED_TEXT_BUCKET}/{summary_key}",
            # Include only essential metadata, NOT the full text content
            'pages_summary': [
                {
                    'page': page['page'],
                    'text_s3_path': page['text_s3_path'],
                    'text_length': len(page['text']),
                    'text_preview': page['text'][:200] + "..." if len(page['text']) > 200 else page['text'],
                    'image_count': page['image_count'],
                    'sheet_name': page.get('sheet_name'),
                    'slide_number': page.get('slide_number'),
                    'image_summary': [
                        {
                            'filename': img['filename'],
                            's3_path': img['s3_path'],
                            'size_bytes': img['size_bytes'],
                            'text_length': img['text_length'],
                            'width': img['width'],
                            'height': img['height']
                        }
                        for img in page.get('image_details', [])
                    ]
                }
                for page in combined_page_data
            ]
        }

        return {
            'statusCode': 200,
            'body': lightweight_response
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': {'status': 'ERROR', 'error': str(e)}
        }

def extract_office_content(file_content, file_type):
    """Extract text and images from Office files"""
    extracted_text = []
    extracted_images = []
    
    try:
        with zipfile.ZipFile(io.BytesIO(file_content), 'r') as zip_file:
            # Extract images first
            extracted_images = extract_images_from_office_file_enhanced(zip_file, file_type)
            
            # Extract text
            if file_type == 'docx':
                extracted_text = extract_docx_text_by_page(zip_file)
            elif file_type == 'xlsx':
                extracted_text = extract_xlsx_text_by_sheet_enhanced(zip_file)
            elif file_type == 'pptx':
                extracted_text = extract_pptx_text_by_slide(zip_file)
                
    except Exception as e:
        extracted_text = [{"page": 1, "text": f"Error extracting {file_type}: {str(e)}"}]
        
    return extracted_text, extracted_images

def extract_images_from_office_file_enhanced(zip_file, file_type):
    """Extract images from Office files with enhanced metadata and OCR"""
    images = []
    media_folders = {
        'docx': 'word/media/',
        'xlsx': 'xl/media/',
        'pptx': 'ppt/media/'
    }
    
    media_folder = media_folders.get(file_type, '')
    if not media_folder:
        return images

    all_files = zip_file.namelist()
    media_files = [f for f in all_files if f.startswith(media_folder)]
    
    location_map = {}
    if file_type == 'pptx':
        location_map = create_pptx_image_slide_mapping(zip_file)
    
    image_count = 0
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']
    seen_hashes = set()
    
    for file_info in zip_file.filelist:
        if (file_info.filename.startswith(media_folder) and
            not file_info.filename.endswith('/') and
            any(file_info.filename.lower().endswith(ext) for ext in image_extensions)):
            
            if image_count >= MAX_IMAGES_TO_PROCESS:
                break
                
            try:
                image_data = zip_file.read(file_info.filename)
                
                # Skip duplicates (similar to PDF logic)
                if is_duplicate_image(image_data, seen_hashes):
                    continue
                
                # Skip very small images
                if len(image_data) < 1000:
                    continue
                
                filename = os.path.basename(file_info.filename)
                ext = os.path.splitext(filename)[1].lower()
                
                content_type_map = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.tiff': 'image/tiff',
                    '.webp': 'image/webp'
                }
                
                # Get image dimensions
                width, height = get_image_dimensions(image_data)
                
                image_info = {
                    'filename': f"{file_type}_{image_count+1}_{filename}",
                    'data': image_data,
                    'content_type': content_type_map.get(ext, 'image/png'),
                    'original_path': file_info.filename,
                    'size_bytes': len(image_data),
                    'width': width,
                    'height': height,
                    'detected_text': '',
                    'text_length': 0
                }
                
                # Add OCR text detection (similar to PDF logic)
                if OCR_AVAILABLE:
                    has_text, detected_text = has_text_content(image_data)
                    image_info['detected_text'] = detected_text
                    image_info['text_length'] = len(detected_text)
                
                # Add location info
                if file_type == 'pptx':
                    slide_num = location_map.get(filename)
                    image_info['slide_number'] = slide_num
                    image_info['page'] = slide_num
                elif file_type == 'docx':
                    image_info['page'] = 1  # For DOCX, treat as single page
                elif file_type == 'xlsx':
                    image_info['page'] = 1  # For XLSX, we'll need to enhance this later
                
                images.append(image_info)
                image_count += 1
                
            except Exception as e:
                print(f"Error extracting image {file_info.filename}: {str(e)}")
    
    print(f"Total images extracted from {file_type}: {len(images)}")
    return images

def get_image_dimensions(image_data):
    """Get image dimensions using PIL"""
    try:
        if not OCR_AVAILABLE:
            return 0, 0
        
        image = Image.open(io.BytesIO(image_data))
        return image.size  # Returns (width, height)
    except Exception as e:
        print(f"Error getting image dimensions: {str(e)}")
        return 0, 0

def has_text_content(image_data, min_text_length=5):
    """Check if image contains text using OCR (same as PDF logic)"""
    try:
        if not OCR_AVAILABLE:
            return False, ""
        
        pil_image = Image.open(io.BytesIO(image_data))
        # Use OCR with optimized config for text detection
        text = pytesseract.image_to_string(pil_image, config='--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ').strip()
        return len(text) >= min_text_length, text
    except Exception as e:
        print(f"OCR error: {str(e)}")
        return False, ""

def is_duplicate_image(image_bytes, seen_hashes):
    """Check if image is a duplicate using hash (same as PDF logic)"""
    image_hash = hashlib.md5(image_bytes).hexdigest()
    if image_hash in seen_hashes:
        return True
    seen_hashes.add(image_hash)
    return False

# Keep all your existing text extraction functions unchanged
def extract_xlsx_text_by_sheet_enhanced(zip_file):
    """Enhanced XLSX text extraction with shared strings support"""
    extracted_text = []
    
    try:
        # First, load shared strings
        shared_strings = load_shared_strings(zip_file)
        
        # Get worksheet files
        workbook_files = [f for f in zip_file.namelist() if f.startswith('xl/worksheets/')]
        workbook_files.sort()
        
        for i, sheet_file in enumerate(workbook_files, 1):
            try:
                sheet_xml = zip_file.read(sheet_file)
                root = ET.fromstring(sheet_xml)
                
                # Extract all text content from the sheet
                text_content = extract_sheet_text_content(root, shared_strings)
                
                # Get sheet name if available
                sheet_name = get_sheet_name(zip_file, i-1) or f"Sheet{i}"
                
                extracted_text.append({
                    "page": i,
                    "sheet_name": sheet_name,
                    "text": text_content if text_content.strip() else "No data in sheet"
                })
                
            except Exception as e:
                extracted_text.append({
                    "page": i,
                    "sheet_name": f"Sheet{i}",
                    "text": f"Error extracting sheet: {str(e)}"
                })
                
    except Exception as e:
        extracted_text = [{"page": 1, "text": f"Error extracting XLSX: {str(e)}"}]
        
    return extracted_text

def load_shared_strings(zip_file):
    """Load shared strings from XLSX file"""
    shared_strings = {}
    
    try:
        if 'xl/sharedStrings.xml' in zip_file.namelist():
            shared_strings_xml = zip_file.read('xl/sharedStrings.xml')
            root = ET.fromstring(shared_strings_xml)
            
            for i, si in enumerate(root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si')):
                text_parts = []
                
                # Handle simple text
                t_elem = si.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                if t_elem is not None and t_elem.text:
                    text_parts.append(t_elem.text)
                
                # Handle rich text
                for r in si.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}r'):
                    t_elem = r.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                    if t_elem is not None and t_elem.text:
                        text_parts.append(t_elem.text)
                
                if text_parts:
                    shared_strings[str(i)] = ''.join(text_parts)
                    
    except Exception as e:
        print(f"Error loading shared strings: {str(e)}")
        
    return shared_strings

def extract_sheet_text_content(root, shared_strings):
    """Extract text content from a worksheet"""
    text_parts = []
    rows = {}
    
    # Group cells by row
    for cell in root.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
        cell_ref = cell.get('r', '')
        if cell_ref:
            # Extract row number from cell reference (e.g., 'A1' -> 1)
            row_match = re.search(r'(\d+)', cell_ref)
            if row_match:
                row_num = int(row_match.group(1))
                if row_num not in rows:
                    rows[row_num] = []
                
                # Get cell value
                cell_value = get_cell_value(cell, shared_strings)
                if cell_value:
                    rows[row_num].append(cell_value)
    
    # Convert rows to text
    for row_num in sorted(rows.keys()):
        if rows[row_num]:
            row_text = '\t'.join(rows[row_num])
            if row_text.strip():
                text_parts.append(row_text)
    
    return '\n'.join(text_parts)

def get_cell_value(cell, shared_strings):
    """Extract value from a cell element"""
    value_elem = cell.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
    
    if value_elem is None or not value_elem.text:
        return ""
    
    cell_type = cell.get('t', '')
    
    # If it's a shared string, look it up
    if cell_type == 's':
        return shared_strings.get(value_elem.text, value_elem.text)
    
    # For inline strings
    elif cell_type == 'inlineStr':
        is_elem = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is')
        if is_elem is not None:
            t_elem = is_elem.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
            if t_elem is not None and t_elem.text:
                return t_elem.text
    
    # For other types (numbers, dates, etc.)
    return value_elem.text

def get_sheet_name(zip_file, sheet_index):
    """Get the actual sheet name from workbook.xml"""
    try:
        if 'xl/workbook.xml' in zip_file.namelist():
            workbook_xml = zip_file.read('xl/workbook.xml')
            root = ET.fromstring(workbook_xml)
            
            sheets = root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet')
            if sheet_index < len(sheets):
                return sheets[sheet_index].get('name', f'Sheet{sheet_index + 1}')
                
    except Exception as e:
        print(f"Error getting sheet name: {str(e)}")
        
    return None

def create_pptx_image_slide_mapping(zip_file):
    """Create mapping between images and slide numbers in PPTX"""
    image_slide_map = {}
    
    try:
        slide_rels_files = [f for f in zip_file.namelist() if f.startswith('ppt/slides/_rels/slide') and f.endswith('.xml.rels')]
        
        for rels_file in slide_rels_files:
            slide_match = re.search(r'slide(\d+)\.xml\.rels', rels_file)
            if slide_match:
                slide_number = int(slide_match.group(1))
                
                try:
                    rels_xml = zip_file.read(rels_file)
                    root = ET.fromstring(rels_xml)
                    
                    for relationship in root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                        target = relationship.get('Target')
                        if target and target.startswith('../media/'):
                            image_name = os.path.basename(target)
                            image_slide_map[image_name] = slide_number
                            
                except Exception as e:
                    print(f"Error processing slide relationships {rels_file}: {str(e)}")
                    
    except Exception as e:
        print(f"Error creating image-slide mapping: {str(e)}")
        
    return image_slide_map

def extract_docx_text_by_page(zip_file):
    """Extract DOCX text (treating as single page for now)"""
    try:
        if 'word/document.xml' in zip_file.namelist():
            document_xml = zip_file.read('word/document.xml')
            text_content = extract_text_from_xml(document_xml)
            return [{"page": 1, "text": '\n'.join(text_content)}]
    except Exception as e:
        return [{"page": 1, "text": f"Error extracting DOCX: {str(e)}"}]
        
    return [{"page": 1, "text": "No content found"}]

def extract_pptx_text_by_slide(zip_file):
    """Extract PPTX text by slide"""
    extracted_text = []
    
    try:
        slide_files = [f for f in zip_file.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
        slide_files.sort(key=lambda x: int(re.findall(r'slide(\d+)\.xml', x)[0])
                         if re.findall(r'slide(\d+)\.xml', x) else 0)
        
        for slide_file in slide_files:
            slide_num = int(re.findall(r'slide(\d+)\.xml', slide_file)[0])
            
            try:
                slide_xml = zip_file.read(slide_file)
                slide_text = extract_text_from_pptx_slide(slide_xml)
                
                extracted_text.append({
                    "page": slide_num,
                    "slide_number": slide_num,
                    "text": '\n'.join(slide_text) if slide_text else "No text on slide"
                })
                
            except Exception as e:
                extracted_text.append({
                    "page": slide_num,
                    "slide_number": slide_num,
                    "text": f"Error extracting slide: {str(e)}"
                })
                
    except Exception as e:
        extracted_text = [{"page": 1, "text": f"Error extracting PPTX: {str(e)}"}]
        
    return extracted_text

def extract_text_from_xml(xml_content):
    """Extract text from Word XML content"""
    try:
        root = ET.fromstring(xml_content)
        namespaces = {
            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        }
        
        text_elements = []
        paragraphs = root.findall('.//w:p', namespaces)
        
        for para in paragraphs:
            para_text = []
            runs = para.findall('.//w:r', namespaces)
            for run in runs:
                text_nodes = run.findall('.//w:t', namespaces)
                for text_node in text_nodes:
                    if text_node.text:
                        para_text.append(text_node.text)
            
            paragraph_content = ''.join(para_text).strip()
            if paragraph_content:
                text_elements.append(paragraph_content)
        
        return text_elements
        
    except Exception as e:
        print(f"Error extracting text from XML: {str(e)}")
        return []

def extract_text_from_pptx_slide(xml_content):
    """Extract text from PowerPoint slide XML content"""
    try:
        root = ET.fromstring(xml_content)
        namespaces = {
            'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
        }
        
        text_elements = []
        paragraphs = root.findall('.//a:p', namespaces)
        
        for para in paragraphs:
            para_text = []
            runs = para.findall('.//a:t', namespaces)
            for run in runs:
                if run.text:
                    para_text.append(run.text)
            
            paragraph_content = ''.join(para_text).strip()
            if paragraph_content:
                text_elements.append(paragraph_content)
        
        return text_elements
        
    except Exception as e:
        print(f"Error extracting text from PowerPoint slide XML: {str(e)}")
        return []