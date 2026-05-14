import boto3
import os
import logging
import json
import io
from typing import Dict, Any, Optional

# Initialize AWS clients
s3 = boto3.client('s3')

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def sanitize_bucket_name(bucket_or_arn: str) -> str:
    """
    Extract bucket name from ARN or return bucket name as-is.
    
    Args:
        bucket_or_arn: S3 bucket name or ARN
        
    Returns:
        Clean bucket name
    """
    if bucket_or_arn and bucket_or_arn.startswith("arn:aws:s3:::"):
        bucket_name = bucket_or_arn.split(":::")[-1]
        logger.debug(f"Extracted bucket name '{bucket_name}' from ARN: {bucket_or_arn}")
        return bucket_name
    return bucket_or_arn

def validate_json_content(content: str) -> Dict[str, Any]:
    """
    Validate and parse JSON content.
    
    Args:
        content: Raw JSON string content
        
    Returns:
        Parsed JSON object
        
    Raises:
        ValueError: If JSON is invalid
    """
    try:
        parsed_json = json.loads(content)
        logger.info(f"Successfully parsed JSON with {len(str(parsed_json))} characters")
        return parsed_json
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {e}")
        raise ValueError(f"Invalid JSON format: {e}")

def read_json_content(byte_stream: io.BytesIO) -> Dict[str, Any]:
    """
    Read and parse JSON content from byte stream.
    
    Args:
        byte_stream: BytesIO stream containing JSON data
        
    Returns:
        Parsed JSON object
    """
    try:
        # Read bytes and decode to string
        content_bytes = byte_stream.read()
        logger.debug(f"Read {len(content_bytes)} bytes from stream")
        
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1']
        content_str = None
        
        for encoding in encodings:
            try:
                content_str = content_bytes.decode(encoding)
                logger.debug(f"Successfully decoded content using {encoding}")
                break
            except UnicodeDecodeError:
                logger.debug(f"Failed to decode with {encoding}, trying next encoding")
                continue
        
        if content_str is None:
            raise ValueError("Unable to decode file content with any supported encoding")
        
        # Validate and parse JSON
        return validate_json_content(content_str)
        
    except Exception as e:
        logger.error(f"Error reading JSON content: {e}")
        raise

def extract_event_details(event: Dict[str, Any]) -> tuple[str, str]:
    """
    Extract S3 bucket and key from various event formats.
    
    Args:
        event: Lambda event data
        
    Returns:
        Tuple of (bucket, key)
    """
    bucket = None
    key = None
    
    # Check if it's an SQS event from EventBridge
    if 'Records' in event:
        logger.info("Processing SQS event")
        for record in event['Records']:
            if 'body' in record:
                try:
                    # Parse SQS message body
                    sqs_body = json.loads(record['body'])
                    logger.debug(f"SQS message body: {sqs_body}")
                    
                    # Extract S3 details from EventBridge message
                    if 'detail' in sqs_body:
                        detail = sqs_body['detail']
                        bucket = detail.get('bucket', {}).get('name')
                        key = detail.get('object', {}).get('key')
                        logger.info(f"Extracted from EventBridge detail - Bucket: {bucket}, Key: {key}")
                        break
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse SQS message body: {e}")
                    continue
    
    # Fallback to direct event parameters
    if not bucket or not key:
        bucket = event.get('bucket') or event.get('s3_bucket')
        key = event.get('s3_key') or event.get('key')
        logger.info(f"Using direct event parameters - Bucket: {bucket}, Key: {key}")
    
    # Fallback to environment variable for bucket
    if not bucket:
        bucket = os.environ.get('S3_BUCKET')
        logger.info(f"Using S3_BUCKET environment variable: {bucket}")
    
    return bucket, key

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Reads a .json SOP file from S3 and returns its parsed content.
    
    Supports multiple event formats:
    1. SQS events from EventBridge (S3 notifications)
    2. Direct invocation with s3_key and bucket parameters
    
    Args:
        event: Lambda event data
        context: Lambda context
        
    Returns:
        Dict containing parsed JSON content and metadata
    """
    
    # Log the incoming event (be careful with sensitive data)
    logger.info(f"Lambda invocation started. Request ID: {context.aws_request_id}")
    logger.debug(f"Event keys: {list(event.keys())}")
    
    try:
        # Extract bucket and key from event
        bucket, key = extract_event_details(event)
        bucket = sanitize_bucket_name(bucket) if bucket else None
        
        # Validate required parameters
        if not bucket or not key:
            error_msg = f"Missing required parameters. bucket: {bucket}, s3_key: {key}"
            logger.error(error_msg)
            raise ValueError("Missing required parameters: bucket and s3_key are required.")
        
        # Validate file extension
        if not key.lower().endswith('.json'):
            error_msg = f"File is not a JSON file: {key}"
            logger.error(error_msg)
            raise ValueError(f"Expected JSON file, got: {key}")
        
        # Validate file is in non_distinct_processes folder
        if not key.startswith('non_distinct_processes/'):
            error_msg = f"File is not in the non_distinct_processes folder: {key}"
            logger.error(error_msg)
            raise ValueError(f"File must be in non_distinct_processes/ folder: {key}")
        
        logger.info(f"Processing JSON file from S3: s3://{bucket}/{key}")
        
        # Get object from S3
        response = s3.get_object(Bucket=bucket, Key=key)
        #print(response)
        logger.info(f"Successfully retrieved S3 object. Size: {response['ContentLength']} bytes")
        
        # Read and parse JSON content
        file_stream = io.BytesIO(response['Body'].read())
        parsed_content = read_json_content(file_stream)
        
        # Add better logging for the actual content
        logger.info(f"Parsed JSON structure - Top level keys: {list(parsed_content.keys())}")
        if 'metadata' in parsed_content:
            logger.info(f"Process ID: {parsed_content['metadata'].get('process_id')}")
            logger.info(f"Process Name: {parsed_content['metadata'].get('process_name')}")
            logger.info(f"Process Details: {parsed_content.get('process_details', {})}")
            logger.info(f"content: {parsed_content.get('content', {})}")
            logger.info(f"analytics: {parsed_content.get('analytics', {})}")
            # Use .get() for potentially missing keys
            logger.info(f"llm_tags: {parsed_content.get('llm_tags', 'Not present')}")
            logger.info(f"tag_categories: {parsed_content.get('tag_categories', 'Not present')}")
            logger.info(f"tagging_info: {parsed_content.get('tagging_info', 'Not present')}")
            # Safely access nested mermaid_syntax
            mermaid_syntax = parsed_content.get('process_details', {}).get('mermaid_syntax', 'Not present')
            logger.info(f"mermaid_syntax: {mermaid_syntax}")
        
        # Prepare response
        result = {
            "success": True,
            "content": parsed_content,
            "metadata": {
                "s3_key": key,
                "bucket": bucket,
                "size": response['ContentLength'],
                "last_modified": response['LastModified'].isoformat() if 'LastModified' in response else None,
                "content_type": response.get('ContentType', 'application/json'),
                "etag": response.get('ETag', '').strip('"'),
                "request_id": context.aws_request_id
            }
        }
        logger.info(f"Successfully processed JSON file. Content: {(parsed_content)}")
        logger.info(f"Successfully processed JSON file. Content keys: {list(parsed_content.keys()) if isinstance(parsed_content, dict) else 'Not a dict'}")
        return result
        
    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        return {
            "success": False,
            "error": str(ve),
            "error_type": "ValidationError",
            "request_id": context.aws_request_id
        }
        
    except Exception as e:
        logger.error(f"Unexpected error processing S3 file: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "request_id": context.aws_request_id
        }
