import json
import boto3
import os
import time
import time
from botocore.exceptions import ClientError

bedrock_agent = boto3.client('bedrock-agent')

def lambda_handler(event, context):
    """
    Lambda function to start Bedrock Knowledge Base ingestion job with retry logic
    Lambda function to start Bedrock Knowledge Base ingestion job with retry logic
    """
    try:
        knowledge_base_id = os.environ.get('KNOWLEDGE_BASE_ID')
        data_source_id = os.environ.get('DATA_SOURCE_ID')
        max_retries = int(os.environ.get('MAX_RETRIES', '3'))
        retry_delay = int(os.environ.get('RETRY_DELAY_SECONDS', '30'))
        max_retries = int(os.environ.get('MAX_RETRIES', '3'))
        retry_delay = int(os.environ.get('RETRY_DELAY_SECONDS', '30'))
        
        if not knowledge_base_id or not data_source_id:
            raise ValueError("KNOWLEDGE_BASE_ID and DATA_SOURCE_ID environment variables must be set")
        
        for attempt in range(max_retries + 1):
            try:
                # Start ingestion job
                response = bedrock_agent.start_ingestion_job(
                    knowledgeBaseId=knowledge_base_id,
                    dataSourceId=data_source_id
                )
                
                ingestion_job = response.get('ingestionJob', {})
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': f'Ingestion job started successfully on attempt {attempt + 1}',
                        'ingestionJobId': ingestion_job.get('ingestionJobId'),
                        'status': ingestion_job.get('status'),
                        'knowledgeBaseId': knowledge_base_id,
                        'dataSourceId': data_source_id,
                        'attempts': attempt + 1
                    })
                }
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                
                if error_code == 'ConflictException' and attempt < max_retries:
                    print(f"Attempt {attempt + 1} failed with ConflictException. Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    continue
                else:
                    # If it's not a conflict or we've exhausted retries, raise the error
                    raise e
        
        # If we get here, we've exhausted all retries
        return {
            'statusCode': 409,
            'body': json.dumps({
                'error': 'ConflictException',
                'message': f'Knowledge Base still in use after {max_retries} retries',
                'attempts': max_retries + 1
            })
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"AWS Client Error: {error_code} - {error_message}")
        
        return {
            'statusCode': 409 if error_code == 'ConflictException' else 500,
            'statusCode': 409 if error_code == 'ConflictException' else 500,
            'body': json.dumps({
                'error': error_code,
                'message': error_message
            })
        }
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'InternalError',
                'message': str(e)
            })
        }