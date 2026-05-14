import json
import boto3
import os
from botocore.exceptions import ClientError

bedrock_agent = boto3.client('bedrock-agent')

def lambda_handler(event, context):
    """
    Lambda function to start Bedrock Knowledge Base ingestion job
    """
    try:
        knowledge_base_id = os.environ.get('KNOWLEDGE_BASE_ID')
        data_source_id = os.environ.get('DATA_SOURCE_ID')
        
        if not knowledge_base_id or not data_source_id:
            raise ValueError("KNOWLEDGE_BASE_ID and DATA_SOURCE_ID environment variables must be set")
        
        # Start ingestion job
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id
        )
        
        ingestion_job = response.get('ingestionJob', {})
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Ingestion job started successfully',
                'ingestionJobId': ingestion_job.get('ingestionJobId'),
                'status': ingestion_job.get('status'),
                'knowledgeBaseId': knowledge_base_id,
                'dataSourceId': data_source_id
            })
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"AWS Client Error: {error_code} - {error_message}")
        
        return {
            'statusCode': 500,
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
