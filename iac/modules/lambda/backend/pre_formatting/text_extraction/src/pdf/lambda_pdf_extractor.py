import json
import boto3
import tempfile
import os
import uuid
import hashlib
import io
from datetime import datetime
from collections import defaultdict


# Import libraries with error handling
try:
   import fitz  # PyMuPDF
   PYMUPDF_AVAILABLE = True
except ImportError:
   PYMUPDF_AVAILABLE = False
   print("Warning: PyMuPDF not available")


try:
   from PIL import Image
   import pytesseract
   OCR_AVAILABLE = True
except ImportError:
   OCR_AVAILABLE = False
   print("Warning: PIL/pytesseract not available")


try:
   import PyPDF2
   PYPDF2_AVAILABLE = True
except ImportError:
   PYPDF2_AVAILABLE = False
   print("Warning: PyPDF2 not available")


s3_client = boto3.client('s3')
textract_client = boto3.client('textract')


# Configuration
MAX_RESPONSE_SIZE = 100 * 1024  # 100KB
EXTRACTED_TEXT_BUCKET = os.environ.get('EXTRACTED_TEXT_BUCKET', 'default-extracted-text-bucket')
TEXTRACT_MAX_SIZE = 10 * 1024 * 1024  # 10MB limit
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
       file_type = event_data.get('file_type', '').lower()
       file_size = event_data.get('file_size', 0)
       #client_name = os.path.splitext(os.path.basename(s3_key))[0]
       client_name = event_data.get('client_name')
       txn_id = event_data.get('txn_id')
       print(f"Extracted client name: {client_name}")

       if not s3_bucket or not s3_key:
           raise ValueError("Missing required parameters: bucket_name and object_key")


       if file_type != 'pdf':
           raise ValueError(f"This function only handles PDF files, received: {file_type}")


       print(f"Processing PDF file: {s3_bucket}/{s3_key}, size: {file_size} bytes")


       # Create folder structure
       timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
       original_filename = os.path.splitext(os.path.basename(s3_key))[0]
       base_folder = f"{timestamp}_{uuid.uuid4().hex[:8]}_{original_filename}"
       text_folder = f"{client_name}/{base_folder}/extracted_text"
       images_folder = f"{client_name}/{base_folder}/extracted_images"


       # Get file content
       response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
       file_content = response['Body'].read()


       # Extract text and images from PDF
       extracted_text_by_page, extracted_images = extract_pdf_content(file_content, s3_bucket, s3_key, file_size)
       # Generate content hash for duplicate detection
       content_hash = generate_content_hash(extracted_text_by_page)

       # Generate content hash for duplicate detection
       content_hash = generate_content_hash(extracted_text_by_page)

       # Group images by page
       images_by_page = defaultdict(list)
       for img_data in extracted_images:
           page_num = img_data.get('page', 1)
           images_by_page[page_num].append(img_data)


       # Store extracted text files and combine with image data
       combined_page_data = []
       total_images = 0
      
       for i, page_data in enumerate(extracted_text_by_page):
           page_num = page_data.get('page', i+1)
          
           # Store text file
           text_key = f"{text_folder}/page_{page_num}.txt"
           s3_client.put_object(
               Bucket=EXTRACTED_TEXT_BUCKET,
               Key=text_key,
               Body=page_data['text'].encode('utf-8'),
               ContentType='text/plain'
           )


           # Store images for this page and create image details
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


           # Combine text and image data for this page
           combined_page_data.append({
               "page": page_num,
               "text_s3_path": f"s3://{EXTRACTED_TEXT_BUCKET}/{text_key}",
               "text": page_data['text'],
               "image_details": image_details,
               "image_count": len(image_details)
           })


       # Create summary JSON
       summary = {
           'status': 'SUCCESS',
           'file_type': file_type,
           'original_file': f"s3://{s3_bucket}/{s3_key}",
           'timestamp_text_extraction': datetime.utcnow().isoformat(),
           'text_s3_bucket':f"s3://{EXTRACTED_TEXT_BUCKET}",
           'text_s3_key': text_key,
           'client_name': client_name,
           'txn_id' : txn_id,
           'content_hash': content_hash,
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


   except Exception as e:
       print(f"Error: {str(e)}")
       import traceback
       traceback.print_exc()
       return {
           'statusCode': 500,
           'body': {'status': 'ERROR', 'error': str(e)}
       }


def extract_pdf_content(file_content, s3_bucket, s3_key, file_size):
   """Extract text and images from PDF using PyMuPDF with OCR"""
   extracted_text = []
   extracted_images = []


   # Try PyMuPDF first for better image extraction with OCR
   if PYMUPDF_AVAILABLE:
       try:
           with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
               temp_file.write(file_content)
               temp_file.flush()
              
               pdf_document = fitz.open(temp_file.name)
              
               # Extract text by page
               for page_num in range(len(pdf_document)):
                   page = pdf_document[page_num]
                   page_text = page.get_text()
                   extracted_text.append({
                       "page": page_num + 1,
                       "text": page_text.strip() if page_text.strip() else "(No text on this page)"
                   })
              
               # Extract images with OCR text detection
               extracted_images = extract_images_with_ocr(pdf_document)
               pdf_document.close()
               os.unlink(temp_file.name)
              
       except Exception as e:
           print(f"PyMuPDF failed: {e}, falling back to other methods")
           if file_size <= TEXTRACT_MAX_SIZE:
               extracted_text, extracted_images = fallback_textract_extraction(s3_bucket, s3_key, file_content)
           elif PYPDF2_AVAILABLE:
               extracted_text = extract_pdf_text_by_page(file_content)
               extracted_images = extract_images_from_pdf_pypdf2(file_content)
   else:
       # Fallback to Textract or PyPDF2
       if file_size <= TEXTRACT_MAX_SIZE:
           extracted_text, extracted_images = fallback_textract_extraction(s3_bucket, s3_key, file_content)
       elif PYPDF2_AVAILABLE:
           extracted_text = extract_pdf_text_by_page(file_content)
           extracted_images = extract_images_from_pdf_pypdf2(file_content)


   return extracted_text, extracted_images


def extract_images_with_ocr(pdf_document):
   """Extract images from PDF with OCR text detection using PyMuPDF"""
   images = []
   seen_hashes = set()
  
   print(f"Processing PDF with {len(pdf_document)} pages for image extraction with OCR")
  
   for page_num in range(len(pdf_document)):
       page = pdf_document[page_num]
       image_list = page.get_images(full=True)
      
       for img_index, img in enumerate(image_list):
           if len(images) >= MAX_IMAGES_TO_PROCESS:
               break
              
           xref = img[0]
              
           try:
               base_image = pdf_document.extract_image(xref)
               image_bytes = base_image["image"]
               image_ext = base_image["ext"]
              
               # Skip duplicates
               if is_duplicate_image(image_bytes, seen_hashes):
                   continue
              
               # Skip very small images
               if len(image_bytes) < 1000:
                   continue
              
               filename = f"pdf_page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
              
               image_info = {
                   'filename': filename,
                   'data': image_bytes,
                   'content_type': f'image/{image_ext}',
                   'page': page_num + 1,
                   'size_bytes': len(image_bytes),
                   'width': base_image.get("width", 0),
                   'height': base_image.get("height", 0),
                   'colorspace': base_image.get("colorspace", "unknown"),
                   'xref': xref
               }
              
               # Analyze image content and check for text
               if OCR_AVAILABLE:
                   content_analysis = analyze_image_content(image_bytes)
                   has_text, detected_text = has_text_content(image_bytes)
                  
                   # Calculate page coverage
                   coverage = (image_info['width'] * image_info['height']) / (page.rect.width * page.rect.height)
                  
                   # Skip background templates
                   if is_background_template(image_info, page.rect, content_analysis):
                       print(f"Skipping background: {filename}")
                       continue
                  
                   # Only keep images with text or significant content
                   if has_text or (coverage < 0.8 and len(image_bytes) > 10000):
                       image_info['detected_text'] = detected_text
                       image_info['text_length'] = len(detected_text)
                       image_info['content_analysis'] = content_analysis
                       image_info['page_coverage'] = coverage
                       images.append(image_info)
                       print(f"Added image with text: {filename} - '{detected_text[:50]}...'")
               else:
                   # Without OCR, keep all non-small images
                   images.append(image_info)
                  
           except Exception as img_error:
               print(f"Error extracting image {xref} from page {page_num + 1}: {str(img_error)}")


   print(f"Total images extracted: {len(images)}")
   return images


def analyze_image_content(image_bytes):
   """Analyze image content for complexity and color distribution"""
   try:
       image = Image.open(io.BytesIO(image_bytes))
       if image.mode != 'RGB':
           image = image.convert('RGB')
      
       # Get unique colors
       colors = image.getcolors(maxcolors=256*256*256)
       unique_colors = len(colors) if colors else 0
      
       # Calculate dominant color ratio
       if colors:
           total_pixels = sum(count for count, color in colors)
           dominant_color_ratio = max(count for count, color in colors) / total_pixels
       else:
           dominant_color_ratio = 1.0
      
       # Determine complexity
       is_complex = unique_colors > 50 and dominant_color_ratio < 0.8
      
       return {
           'is_complex': is_complex,
           'unique_colors': unique_colors,
           'dominant_color_ratio': dominant_color_ratio
       }
   except:
       return {'is_complex': True, 'unique_colors': 0, 'dominant_color_ratio': 0}


def has_text_content(image_bytes, min_text_length=5):
   """Check if image contains text using OCR"""
   try:
       pil_image = Image.open(io.BytesIO(image_bytes))
       # Use OCR with optimized config for text detection
       text = pytesseract.image_to_string(pil_image, config='--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ').strip()
       return len(text) >= min_text_length, text
   except Exception as e:
       print(f"OCR error: {str(e)}")
       return False, ""


def is_background_template(image_info, page_rect, content_analysis):
   """Enhanced background detection using multiple criteria"""
   width, height = image_info['width'], image_info['height']
   page_width, page_height = page_rect.width, page_rect.height
  
   coverage = (width * height) / (page_width * page_height)
  
   # High coverage images are background IF they meet additional criteria
   if coverage > 0.8:
       # Check if it's a simple/template image
       if (content_analysis['unique_colors'] < 20 or
           content_analysis['dominant_color_ratio'] > 0.9):
           return True
      
       # Very large file size suggests it's actual content (photo/diagram)
       if image_info['size_bytes'] > 100000:  # >100KB
           return False
  
   return False


def is_duplicate_image(image_bytes, seen_hashes):
   """Check if image is a duplicate using hash"""
   image_hash = hashlib.md5(image_bytes).hexdigest()
   if image_hash in seen_hashes:
       return True
   seen_hashes.add(image_hash)
   return False


def fallback_textract_extraction(s3_bucket, s3_key, file_content):
   """Fallback to Textract extraction"""
   extracted_text = []
   extracted_images = []
  
   try:
       response = textract_client.analyze_document(
           Document={'S3Object': {'Bucket': s3_bucket, 'Name': s3_key}},
           FeatureTypes=['TABLES', 'FORMS']
       )
      
       # Group blocks by page
       pages = {}
       for block in response['Blocks']:
           page_num = block.get('Page', 1)
           if page_num not in pages:
               pages[page_num] = []
           pages[page_num].append(block)
      
       # Extract text by page
       for page_num in sorted(pages.keys()):
           page_text = []
           for block in pages[page_num]:
               if block['BlockType'] == 'LINE':
                   page_text.append(block['Text'])
           extracted_text.append({
               "page": page_num,
               "text": '\n'.join(page_text)
           })
      
       # Extract images using PyPDF2 as fallback
       if PYPDF2_AVAILABLE:
           extracted_images = extract_images_from_pdf_pypdf2(file_content)
          
   except Exception as e:
       print(f"Textract extraction failed: {e}")
       if PYPDF2_AVAILABLE:
           extracted_text = extract_pdf_text_by_page(file_content)
           extracted_images = extract_images_from_pdf_pypdf2(file_content)
  
   return extracted_text, extracted_images


def extract_images_from_pdf_pypdf2(file_content):
   images = []
   try:
       pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
       print(f"Processing PDF with {len(pdf_reader.pages)} pages for image extraction (PyPDF2)")
      
       image_count = 0
       for page_num, page in enumerate(pdf_reader.pages, 1):
           if image_count >= MAX_IMAGES_TO_PROCESS:
               break
              
           try:
               if hasattr(page, 'images') and page.images:
                   for img_name in page.images:
                       if image_count >= MAX_IMAGES_TO_PROCESS:
                           break
                       try:
                           img_obj = page.images[img_name]
                           if hasattr(img_obj, 'data') and img_obj.data:
                               img_data = img_obj.data
                           elif hasattr(img_obj, '_data') and img_obj._data:
                               img_data = img_obj._data
                           else:
                               continue
                              
                           img_format = 'png'
                           if hasattr(img_obj, 'image_filter'):
                               if img_obj.image_filter == '/DCTDecode':
                                   img_format = 'jpg'
                                  
                           image_info = {
                               'filename': f"pdf_page_{page_num}_img_{image_count + 1}.{img_format}",
                               'data': img_data,
                               'content_type': f'image/{img_format}',
                               'page': page_num,
                               'size_bytes': len(img_data),
                               'detected_text': '',
                               'text_length': 0
                           }
                           images.append(image_info)
                           image_count += 1
                          
                       except Exception as img_error:
                           print(f"Error extracting image {img_name} from page {page_num}: {str(img_error)}")
                          
           except Exception as page_error:
               print(f"Error processing page {page_num} for images: {str(page_error)}")
              
       print(f"Total images extracted from PDF (PyPDF2): {len(images)}")
   except Exception as e:
       print(f"Error extracting images from PDF (PyPDF2): {str(e)}")
  
   return images


def extract_pdf_text_by_page(file_content):
   try:
       pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
       extracted_text = []
       for page_num, page in enumerate(pdf_reader.pages, 1):
           try:
               page_text = page.extract_text()
               extracted_text.append({
                   "page": page_num,
                   "text": page_text.strip() if page_text.strip() else "(No text on this page)"
               })
           except Exception as e:
               extracted_text.append({
                   "page": page_num,
                   "text": f"Error extracting page: {str(e)}"
               })
       return extracted_text
   except Exception as e:
       return [{"page": 1, "text": f"Error extracting PDF: {str(e)}"}]