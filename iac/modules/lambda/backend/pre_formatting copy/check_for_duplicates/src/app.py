import json
import boto3
import os
import logging
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

rds = boto3.client("rds-data")

def check_duplicate_content(content_hash, client_id):
    """
    Check if content with this hash already exists for the client using RDS Data API
    """
    dbname = os.environ["PGDATABASE"]
    secret = os.environ["DB_SECRET_NAME"]
    cluster = os.environ["DB_CLUSTER_ARN"]
    
    try:
        # SQL query to check for existing content with same hash for this client
        sql = """
        SELECT process_id, title, source_sop_url, created_at, file_hash
        FROM processes 
        WHERE file_hash = :content_hash AND client_id = :client_id
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        parameters = [
            {"name": "content_hash", "value": {"stringValue": content_hash}},
            {"name": "client_id", "value": {"stringValue": client_id}}
        ]
        
        logger.info(f"Executing duplicate check query for hash: {content_hash}, client: {client_id}")
        
        response = rds.execute_statement(
            resourceArn=cluster,
            secretArn=secret,
            database=dbname,
            sql=sql,
            parameters=parameters
        )
        
        records = response.get("records", [])
        
        if records and len(records) > 0:
            # Extract values from the first record
            record = records[0]
            
            # RDS Data API returns values in a specific format
            duplicate_info = {
                'process_id': record[0].get('stringValue', '') if record[0] else '',
                'title': record[1].get('stringValue', '') if record[1] else '',
                'source_sop_url': record[2].get('stringValue', '') if record[2] else '',
                'created_at': record[3].get('stringValue', '') if record[3] else '',
                'file_hash': record[4].get('stringValue', '') if record[4] else ''
            }
            
            logger.info(f"Found duplicate content: {duplicate_info}")
            return True, duplicate_info
        else:
            logger.info("No duplicate content found")
            return False, None
            
    except Exception as e:
        logger.error(f"Error checking duplicate content: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Check for duplicate content using file hash
    """
    try:
        logger.info(f"Event: {event}")
        
        # Handle nested body structure
        if 'body' in event:
            event_data = event['body'] if isinstance(event['body'], dict) else event
        else:
            event_data = event
        
        # Extract required data
        content_hash = event_data.get('content_hash')
        client_name = event_data.get('client_name')
        txn_id = event_data.get('txn_id')
        
        if not content_hash:
            raise ValueError("Missing required parameter: content_hash")
            
        if not client_name:
            raise ValueError("Missing required parameter: client_name")
        
        logger.info(f"Checking duplicate for content_hash: {content_hash}, client: {client_name}")
        
        # Check for duplicate content
        is_duplicate, duplicate_info = check_duplicate_content(content_hash, client_name)
        
        # Prepare response with duplicate detection results
        duplicate_detection_result = {
            'is_duplicate': is_duplicate,
            'content_hash': content_hash,
            'duplicate_check_timestamp': datetime.utcnow().isoformat(),
            'duplicate_info': duplicate_info if is_duplicate else None,
            'client_name': client_name
        }
        
        # Add duplicate detection metadata to the event data
        response_body = {
            **event_data,  # Pass through all original data
            'duplicate_detection': duplicate_detection_result
        }
        
        logger.info(f"Duplicate detection result: is_duplicate={is_duplicate}")
        if is_duplicate:
            logger.info(f"Found duplicate: {duplicate_info}")
        
        return {
            'statusCode': 200,
            'body': response_body
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS error in duplicate detection: {error_code} - {error_message}")
        
        return {
            'statusCode': 500,
            'body': {
                'status': 'ERROR',
                'error': f'AWS Error: {error_code} - {error_message}',
                'duplicate_detection': {
                    'is_duplicate': False,
                    'error': 'Failed to check duplicates due to AWS error'
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error in duplicate detection: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': {
                'status': 'ERROR',
                'error': str(e),
                'duplicate_detection': {
                    'is_duplicate': False,
                    'error': 'Failed to check duplicates'
                }
            }
        }
