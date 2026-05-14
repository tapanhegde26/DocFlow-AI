import json
import boto3
import os
from urllib.parse import unquote_plus
from typing import Dict, Any
import logging
import uuid

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO) # Set the default logging level to INFO

# Configure handler and formatter if not already configured (important for Lambda execution context reuse)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("Logger initialized with StreamHandler and custom formatter.")

s3_client = boto3.client('s3')

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler function to process S3 object creation events,
    determine file type, and check for support.
    """
    logger.info("Lambda handler 'file_type_detector' invoked.")
    logger.debug("Received event: %s", json.dumps(event)) # Log full event at DEBUG level
    
    try:
        # Extract S3 details from the event
        # Using .get() for robustness in case keys are missing, though 'bucket' and 's3_key' are expected.
        transaction_uuid = str(uuid.uuid4())
        bucket_name: str = event.get('bucket')
        object_key_raw: str = event.get('s3_key')
        client_name = event.get('client_name')
        
        if not bucket_name:
            logger.error("Missing 'bucket' key in the event. Cannot proceed.")
            return {
                'statusCode': 400,
                'body': {
                    'status': 'ERROR',
                    'error_message': "Missing 'bucket' key in event.",
                    'event_data': event # Include event data for debugging
                }
            }

        if not object_key_raw:
            logger.error("Missing 's3_key' in the event. Cannot proceed.")
            return {
                'statusCode': 400,
                'body': {
                    'status': 'ERROR',
                    'error_message': "Missing 's3_key' in event.",
                    'bucket_name': bucket_name,
                    'event_data': event
                }
            }

        object_key: str = unquote_plus(object_key_raw)
        logger.info("Processing object: bucket='%s', raw_key='%s', unquoted_key='%s'", bucket_name, object_key_raw, object_key)

        # Validate object key prefix for security and expected workflow
        expected_prefix = "raw_files/"
        if not object_key.startswith(expected_prefix):
            error_message = f"Unauthorized access or invalid path: This Lambda only processes files under '{expected_prefix}', but received key: {object_key}"
            logger.warning(error_message) # Use warning as it might be a misconfiguration, not an error in the code itself
            return {
                'statusCode': 400,
                'body': {
                    'status': 'ERROR',
                    'error_message': error_message,
                    'bucket_name': bucket_name,
                    'object_key': object_key
                }
            }
                
        logger.info("Object key '%s' is under the expected prefix '%s'.", object_key, expected_prefix)
                
        # Get file extension
        file_extension: str = os.path.splitext(object_key)[1].lower()
        if not file_extension:
            logger.warning("Object key '%s' does not have a file extension.", object_key)
        logger.info("Extracted file extension: '%s'", file_extension)
                
        # Get object metadata using head_object
        try:
            response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
            content_type: str = response.get('ContentType', 'application/octet-stream') # Default if not found
            file_size: int = response.get('ContentLength', 0) # Default to 0 if not found
            logger.info("S3 object metadata retrieved: Content-Type='%s', File size=%d bytes", content_type, file_size)
            
            # Convert datetime objects to strings for JSON serialization
            response_for_logging = {}
            for key, value in response.items():
                if hasattr(value, 'isoformat'):  # Check if it's a datetime object
                    response_for_logging[key] = value.isoformat()
                else:
                    response_for_logging[key] = value
            
            logger.debug("Full S3 head_object response: %s", json.dumps(response_for_logging, default=str))
            
        except s3_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.error("S3 object '%s/%s' not found. Error: %s", bucket_name, object_key, str(e))
                return {
                    'statusCode': 404,
                    'body': {
                        'status': 'ERROR',
                        'error_message': f"S3 object not found: {object_key}",
                        'bucket_name': bucket_name,
                        'object_key': object_key
                    }
                }
            else:
                logger.error("S3 ClientError when calling head_object for '%s/%s': %s", bucket_name, object_key, str(e), exc_info=True)
                raise # Re-raise other S3 client errors
        
        # Updated file type mapping - now includes 5 supported types
        file_type_mapping: dict[str, str] = {
            '.pdf': 'PDF',
            '.docx': 'DOCX', 
            '.xlsx': 'XLSX',
            '.pptx': 'PPTX',
            '.txt': 'TXT'
        }
                
        detected_file_type: str = file_type_mapping.get(file_extension, 'UNKNOWN')
        logger.info("Mapped file extension '%s' to detected file type: '%s'", file_extension, detected_file_type)
                
        # Validate if file type is supported - now 5 types
        supported_types: list[str] = ['PDF', 'DOCX', 'XLSX', 'PPTX', 'TXT']
        is_supported: bool = detected_file_type in supported_types
                
        logger.info("Is file type '%s' supported? %s", detected_file_type, is_supported)
                
        result: dict[str, Any] = {
            'txn_id':transaction_uuid,
            'bucket_name': bucket_name,
            'client_name' : client_name,
            'object_key': object_key,
            'file_type': detected_file_type,
            'file_extension': file_extension,
            'content_type': content_type,
            'file_size': file_size,
            'is_supported': is_supported,
            'status': 'SUCCESS' if is_supported else 'UNSUPPORTED_FILE_TYPE',
            'requires_image_detection': detected_file_type in ['DOCX', 'XLSX', 'PPTX'] # TXT and PDF typically handled differently for image extraction
        }
                
        logger.info("File processing completed. Result: %s", json.dumps(result))
                
        return {
            'statusCode': 200,
            'body': result
        }
            
    except Exception as e:
        # Catch any unexpected errors during the process
        logger.exception("An unexpected error occurred during file processing: %s", str(e)) # exc_info=True is implied by exception()
        return {
            'statusCode': 500,
            'body': {
                'status': 'ERROR',
                'error_message': f"An unexpected error occurred: {str(e)}",
                'bucket_name': event.get('bucket', 'N/A'), # Use .get() for robustness
                'object_key': event.get('s3_key', 'N/A')
            }
        }
