import json
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Read process documents from S3 under /processes path
    """
    try:
        # Extract S3 details from the event
        bucket_name = event['bucket']
        object_key = event['s3_key']
        
        # Validate that the object is under /processes path
        if not object_key.startswith('processes/'):
            return {
                'statusCode': 400,
                'error': f'Object {object_key} is not under /processes path'
            }
        
        # Read the document from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        document_content = response['Body'].read()
        
        # Get content type and size
        content_type = response.get('ContentType', 'application/octet-stream')
        content_length = response.get('ContentLength', 0)
        
        # Always try to decode content as text
        document_text = None
        try:
            # First try UTF-8 decoding
            document_text = document_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                # Fallback to latin-1 which can decode any byte sequence
                document_text = document_content.decode('latin-1')
                logger.warning(f"Used latin-1 encoding for {object_key}")
            except UnicodeDecodeError:
                logger.warning(f"Could not decode content as text for {object_key}")
                document_text = None
        
        result = {
            'statusCode': 200,
            'bucket_name': bucket_name,
            'object_key': object_key,
            'content_type': content_type,
            'content_length': content_length,
            'document_content': document_text,
            'metadata': response.get('Metadata', {}),
            'last_modified': response['LastModified'].isoformat(),
            'etag': response['ETag']
        }
        
        logger.info(f"Successfully read document: {object_key}")
        return result
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"S3 error reading {object_key}: {error_code} - {error_message}")
        
        return {
            'statusCode': 404 if error_code == 'NoSuchKey' else 500,
            'error': f'Failed to read document: {error_message}'
        }
        
    except Exception as e:
        logger.error(f"Unexpected error reading document: {str(e)}")
        return {
            'statusCode': 500,
            'error': f'Unexpected error: {str(e)}'
        }
