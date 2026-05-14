import json
import boto3
import re
import logging
import os
from datetime import datetime

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("Logger initialized.")

s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime')  # Placeholder, not used here

TEXT_STD_BUCKET = os.environ.get('TEXT_STD_BUCKET', 'default-text-std-bucket')

def lambda_handler(event, context):
    logger.info("Lambda handler 'text_standardizer' invoked.")
    logger.debug("Received event: %s", json.dumps(event))
    
    try:
        body = event.get('body', {})
        file_type = body.get('file_type')
        if not file_type:
            raise KeyError("file_type")
        
        # Initialize variables
        extracted_text = None
        bucket = None
        key = None
        client_name = body.get('client_name')
        txn_id = body.get('txn_id')
        # Extract duplicate detection information
        duplicate_detection = body.get('duplicate_detection', {})
        content_hash = duplicate_detection.get('content_hash')
        is_duplicate = duplicate_detection.get('is_duplicate', False)
        
        # Validate required fields
        if not content_hash:
            raise ValueError("content_hash is missing from duplicate_detection")
        timestamp_text_extraction_processed_at = event.get('timestamp_text_extraction_processed_at')
        
        """
        # Step 1: Attempt to load full text from S3 if available
        if body.get("text_stored_in_s3"):
            bucket = body.get("text_s3_bucket")
            key = body.get("text_s3_key")
            if not bucket or not key:
                raise KeyError("text_s3_bucket or text_s3_key")
            logger.info(f"Loading extracted text from S3: s3://{bucket}/{key}")
            response = s3_client.get_object(Bucket=bucket, Key=key)
            extracted_text = response["Body"].read().decode("utf-8")
        else:
            # Check for direct extracted_text field first
            extracted_text = body.get("extracted_text")
            
            # If not found, try to build from extracted_text_by_page
            if not extracted_text and body.get("extracted_text_by_page"):
                logger.info("Building extracted text from page-based extraction")
                extracted_text = build_text_from_pages(body["extracted_text_by_page"])
        
        if not extracted_text:
            raise KeyError("extracted_text")
        """
        
        # Step 1: Handle the new lightweight response structure
        extracted_text = None
        
        # First priority: Load full text from the summary S3 file if available
        if body.get("summary_s3_path"):
            logger.info("Loading full extraction data from summary S3 file")
            summary_s3_path = body["summary_s3_path"]
            # Parse S3 path: s3://bucket/key
            if summary_s3_path.startswith("s3://"):
                path_parts = summary_s3_path[5:].split("/", 1)
                summary_bucket = path_parts[0]
                summary_key = path_parts[1]
                
                try:
                    response = s3_client.get_object(Bucket=summary_bucket, Key=summary_key)
                    full_summary = json.loads(response["Body"].read().decode("utf-8"))
                    
                    # Build text from the full summary data
                    if full_summary.get("extracted_text_by_page"):
                        logger.info("Building extracted text from full summary pages")
                        extracted_text = build_text_from_pages(full_summary["extracted_text_by_page"])
                except Exception as e:
                    logger.warning(f"Failed to load from summary S3 path: {str(e)}")
        
        # Second priority: Try individual page files from pages_summary
        if not extracted_text and body.get("pages_summary"):
            logger.info("Loading text from individual page files")
            extracted_text = load_text_from_page_files(body["pages_summary"])
        
        # Third priority: Legacy support - load from text_s3_bucket/key
        if not extracted_text and body.get("text_s3_bucket") and body.get("text_s3_key"):
            bucket = body["text_s3_bucket"].replace("s3://", "")
            key = body["text_s3_key"]
            logger.info(f"Loading extracted text from S3: s3://{bucket}/{key}")
            try:
                response = s3_client.get_object(Bucket=bucket, Key=key)
                extracted_text = response["Body"].read().decode("utf-8")
            except Exception as e:
                logger.warning(f"Failed to load from text_s3_bucket/key: {str(e)}")
        
        # Fourth priority: Direct extracted_text field (legacy)
        if not extracted_text:
            extracted_text = body.get("extracted_text")
        
        # Fifth priority: Build from pages_summary previews (fallback)
        if not extracted_text and body.get("pages_summary"):
            logger.info("Building extracted text from page previews (fallback)")
            extracted_text = build_text_from_page_previews(body["pages_summary"])
        
        if not extracted_text:
            raise KeyError("extracted_text")
            
        
        logger.info(f"Starting text standardization for file type: '{file_type}'")
        logger.debug(f"Original extracted text length: {len(extracted_text)} characters")
        
        standardized_text = standardize_text(extracted_text, file_type)
        
        # Use the designated text extraction bucket for output
        output_bucket = TEXT_STD_BUCKET
        
        # Generate output key based on original file
        original_s3_key = body.get("s3_key", "") or body.get("original_file", "")
        if original_s3_key:
            # Extract filename without extension from the original key
            filename_with_ext = original_s3_key.split("/")[-1]
            base_name = filename_with_ext.rsplit(".", 1)[0]
            # Clean the filename for S3 key (remove special characters)
            clean_base_name = re.sub(r'[^a-zA-Z0-9\-_]', '_', base_name)
            standardized_key = f"{client_name}/standardized/{clean_base_name}_standardized.txt"
        else:
            # Fallback if no original key is provided
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            standardized_key = f"{client_name}/standardized/document_{timestamp}_standardized.txt"
        
        logger.info(f"Uploading standardized text to s3://{output_bucket}/{standardized_key}")
        
        # Upload standardized text to S3
        s3_client.put_object(
            Bucket=output_bucket,
            Key=standardized_key,
            Body=standardized_text.encode("utf-8"),
            ContentType="text/plain",
            Metadata={
                'original-bucket': body.get('s3_bucket', ''),
                'original-key': body.get('s3_key', ''),
                'original-file': body.get('original_file', ''),
                'file-type': file_type,
                'processing-timestamp': datetime.now().isoformat(),
                'total-pages': str(body.get('total_pages', 0))
            }
        )
        
        response_payload = {
            'statusCode': 200,
            'file_type': file_type,
            'original_file': body.get('original_file', ''),
            'text_s3_bucket': output_bucket,
            'text_s3_key': standardized_key,
            'client_name': body.get('client_name'),
            'txn_id': txn_id,
            'content_hash':content_hash,
            'is_duplicate': is_duplicate,
            'timestamp_text_standardization': datetime.now().isoformat(),
            'timestamp_text_extraction': body.get('timestamp_text_extraction', ''),
            'standardized_text_length': len(standardized_text),
            'total_pages': body.get('total_pages', 0),
            'total_images': body.get('total_images', 0),
            'text_folder': body.get('text_folder',0),
            'images_folder': body.get('images_folder',0),
            'extracted_text_by_page':body.get('extracted_text_by_page',''),
            'contains_images': body.get('contains_images', True),
            'text_stored_in_s3': True,
            'standardization_completed_at': datetime.now().isoformat(),
            'summary_s3_path': body.get('summary_s3_path', ''),
            'original_extraction_summary': body.get('summary_s3_path', ''),  # Reference to original extraction data
            'pages_processed': body.get('total_pages', 0)
        }

        
        logger.info("Text standardization completed successfully.")
        logger.info(f"Standardized text uploaded to: s3://{output_bucket}/{standardized_key}")
        return response_payload
        
    except KeyError as e:
        logger.error(f"Missing required field in event body: {str(e)}")
        return {
            'statusCode': 400,
            'error': f"Missing required field: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Unexpected error occurred: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }
        
def load_text_from_page_files(pages_summary):
    """
    Load and consolidate text from individual page files stored in S3
    """
    if not pages_summary:
        return ""
    
    consolidated_text = []
    
    # Sort pages by page number
    sorted_pages = sorted(pages_summary, key=lambda x: x.get('page', 0))
    
    for page_data in sorted_pages:
        page_num = page_data.get('page', 'Unknown')
        text_s3_path = page_data.get('text_s3_path', '')
        
        if not text_s3_path or not text_s3_path.startswith('s3://'):
            logger.warning(f"Invalid S3 path for page {page_num}: {text_s3_path}")
            continue
        
        try:
            # Parse S3 path: s3://bucket/key
            path_parts = text_s3_path[5:].split("/", 1)
            bucket = path_parts[0]
            key = path_parts[1]
            
            # Load text from S3
            response = s3_client.get_object(Bucket=bucket, Key=key)
            page_text = response["Body"].read().decode("utf-8").strip()
            
            if page_text:
                # Add page/sheet identifier
                sheet_name = page_data.get('sheet_name')
                slide_number = page_data.get('slide_number')
                
                if sheet_name:
                    consolidated_text.append(f"=== Sheet: {sheet_name} (Page {page_num}) ===")
                elif slide_number:
                    consolidated_text.append(f"=== Slide {slide_number} ===")
                else:
                    consolidated_text.append(f"=== Page {page_num} ===")
                
                consolidated_text.append(page_text)
                consolidated_text.append("")  # Add blank line between pages
            
        except Exception as e:
            logger.error(f"Failed to load text for page {page_num} from {text_s3_path}: {str(e)}")
            consolidated_text.append(f"=== Page {page_num} ===")
            consolidated_text.append(f"Error loading page content: {str(e)}")
            consolidated_text.append("")
    
    return '\n'.join(consolidated_text)

def build_text_from_page_previews(pages_summary):
    """
    Build text from page previews as a fallback when full text isn't available
    """
    if not pages_summary:
        return ""
    
    # Sort pages by page number
    sorted_pages = sorted(pages_summary, key=lambda x: x.get('page', 0))
    
    consolidated_text = []
    for page_data in sorted_pages:
        page_num = page_data.get('page', 'Unknown')
        text_preview = page_data.get('text_preview', '').strip()
        text_length = page_data.get('text_length', 0)
        
        if text_preview:
            # Add page/sheet identifier
            sheet_name = page_data.get('sheet_name')
            slide_number = page_data.get('slide_number')
            
            if sheet_name:
                consolidated_text.append(f"=== Sheet: {sheet_name} (Page {page_num}) ===")
            elif slide_number:
                consolidated_text.append(f"=== Slide {slide_number} ===")
            else:
                consolidated_text.append(f"=== Page {page_num} ===")
            
            consolidated_text.append(text_preview)
            
            # Add note if text was truncated
            if text_length > len(text_preview):
                consolidated_text.append(f"[Note: Text truncated - full length: {text_length} characters]")
            
            consolidated_text.append("")  # Add blank line between pages
    
    return '\n'.join(consolidated_text)


def build_text_from_pages(extracted_text_by_page):
    """
    Build consolidated text from page-based extraction data
    """
    if not extracted_text_by_page:
        return ""
    
    # Sort pages by page number to ensure correct order
    sorted_pages = sorted(extracted_text_by_page, key=lambda x: x.get('page', 0))
    
    consolidated_text = []
    for page_data in sorted_pages:
        page_num = page_data.get('page', 'Unknown')
        text = page_data.get('text', '').strip()
        
        if text:
            # Add page marker for presentation files
            consolidated_text.append(f"=== Slide {page_num} ===")
            consolidated_text.append(text)
            consolidated_text.append("")  # Add blank line between pages
    
    return '\n'.join(consolidated_text)

def standardize_text(text: str, file_type: str) -> str:
    """
    Standardize extracted text based on file type
    """
    try:
        logger.debug("Performing basic cleaning...")
        standardized = clean_text(text)
        
        if file_type.lower() == 'xlsx':
            standardized = standardize_spreadsheet_text(standardized)
        elif file_type.lower() in ['pptx', 'ppt']:
            standardized = standardize_presentation_text(standardized)
        else:
            standardized = standardize_document_text(standardized)
        
        logger.info(f"Text standardization completed. Original length: {len(text)}, Standardized length: {len(standardized)}")
        return standardized
    except Exception as e:
        logger.warning(f"Standardization failed, returning original text: {str(e)}")
        return text

def clean_text(text: str) -> str:
    """
    Perform basic text cleaning
    """
    # Replace multiple whitespaces with single space
    cleaned = re.sub(r'\s+', ' ', text)
    
    # Remove or replace problematic characters while preserving structure
    cleaned = re.sub(r'[^\w\s\.\,\:\;\!\?\-\(\)\[\]\/\=\|\n]', ' ', cleaned)
    
    # Clean up excessive spacing but preserve line breaks
    lines = cleaned.split('\n')
    cleaned_lines = []
    for line in lines:
        line = ' '.join(line.split()).strip()
        if line:  # Only add non-empty lines
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def standardize_spreadsheet_text(text: str) -> str:
    """
    Standardize text extracted from spreadsheet files (xlsx, csv)
    """
    lines = text.split('\n')
    standardized_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Handle tab-separated values
        if '\t' in line:
            cells = [cell.strip() for cell in line.split('\t') if cell.strip()]
            if cells:
                standardized_lines.append(' | '.join(cells))
        # Handle pipe-separated values (already processed)
        elif '|' in line:
            standardized_lines.append(line)
        # Handle regular text
        elif line:
            standardized_lines.append(line)
    
    return '\n'.join(standardized_lines)

def standardize_presentation_text(text: str) -> str:
    """
    Standardize text extracted from presentation files (pptx, ppt)
    """
    lines = text.split('\n')
    result = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Keep slide markers as-is
        if line.startswith('=== Slide'):
            result.append(f"\n{line}")
        # Keep table markers as-is
        elif line.startswith('=== Table'):
            result.append(f"\n{line}")
        elif line.startswith('=== End Table'):
            result.append(f"{line}\n")
        # Keep speaker notes markers as-is
        elif line.startswith('=== Speaker Notes'):
            result.append(f"\n{line}")
        elif line.startswith('--- Notes for Slide'):
            result.append(f"\n{line}")
        # Process section headers
        elif is_section_header(line):
            result.append(f"SECTION: {line}")
        # Process process steps
        elif is_process_step(line):
            result.append(f"STEP: {line}")
        # Keep everything else as-is
        else:
            result.append(line)
    
    return '\n'.join(result)

def standardize_document_text(text: str) -> str:
    """
    Standardize text extracted from document files (pdf, docx, txt)
    """
    lines = text.split('\n')
    result = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if is_section_header(line):
            result.append(f"SECTION: {line}")
        elif is_process_step(line):
            result.append(f"STEP: {line}")
        else:
            result.append(line)
    
    return '\n'.join(result)

def is_section_header(text: str) -> bool:
    """
    Determine if a line of text is likely a section header
    """
    patterns = [
        r'^\d+\.\s+[A-Z]',  # "1. SECTION NAME"
        r'^[A-Z\s]{3,}:?$',  # "SECTION NAME" or "SECTION NAME:"
        r'^\w+\s+\d+:',  # "Chapter 1:" or "Section 2:"
        r'^(chapter|section|appendix)\s+\w+',  # "Chapter One", "Section A"
        r'^[IVXLCDM]+\.',  # Roman numerals "I.", "II.", etc.
        r'^[A-Z]\.',  # Single letter "A.", "B.", etc.
        r'^(INTRODUCTION|OVERVIEW|CONCLUSION|SUMMARY|BACKGROUND)$',  # Common headers
    ]
    
    return any(re.match(p, text.strip(), re.IGNORECASE) for p in patterns)

def is_process_step(text: str) -> bool:
    """
    Determine if a line of text is likely a process step
    """
    patterns = [
        r'^\d+\)',  # "1)", "2)", etc.
        r'^\d+\.',  # "1.", "2.", etc.
        r'^Step\s+\d+[:\.]?',  # "Step 1:", "Step 2."
        r'^\w+:\s',  # "Action:", "Note:"
        r'^\-\s',  # "- item"
        r'^\*\s',  # "* item"
        r'^(first|next|then|finally),?\s',  # Sequence words
        r'^(log in to|navigate to|click on|select|enter|verify|ensure|complete)\s',  # Action verbs
        r'^(to\s+\w+|in\s+order\s+to)',  # "To do something", "In order to"
    ]
    
    return any(re.match(p, text.strip(), re.IGNORECASE) for p in patterns)