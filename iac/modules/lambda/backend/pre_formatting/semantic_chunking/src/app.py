import json
import boto3
import re
import logging
from datetime import datetime
import uuid
import os

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("Logger initialized with StreamHandler and custom formatter.")

bedrock_client = boto3.client('bedrock-runtime')
s3_client = boto3.client('s3')
SEMANTIC_CHUNKING_BUCKET = os.environ.get('SEMANTIC_CHUNKING_BUCKET', 'default-extracted-text-bucket')

def lambda_handler(event, context):
    """
    Lambda handler function to perform semantic chunking on standardized text
    using AWS Bedrock and store results in S3.
    """
    logger.info("Lambda handler 'semantic_chunker' invoked.")
    logger.debug("Received event: %s", json.dumps(event))

    try:
        # Check if standardized_text is directly provided
        client_name = event.get('client_name')
        if 'standardized_text' in event:
            standardized_text = event['standardized_text']
            logger.info("Using standardized_text from event payload")
        # Check if we have valid S3 bucket and key (not empty strings)
        elif 'text_s3_bucket' in event and 'text_s3_key' in event:
            text_s3_bucket = event['text_s3_bucket']
            text_s3_key = event['text_s3_key']
            logger.info(f"Reading standardized text from S3: {text_s3_bucket}/{text_s3_key}")
            # # Extract bucket name from S3 URI if needed
            # if text_s3_bucket.startswith('s3://'):
            #     text_s3_bucket = text_s3_bucket.replace('s3://', '').split('/')[0]

            try:
                response = s3_client.get_object(Bucket=text_s3_bucket, Key=text_s3_key)
                standardized_text = response['Body'].read().decode('utf-8')
                logger.info(f"Successfully read {len(standardized_text)} characters from S3")
            except Exception as s3_error:
                logger.error(f"Failed to read from S3: {str(s3_error)}")
                return {
                    'statusCode': 500,
                    'error': f"Failed to read standardized text from S3: {str(s3_error)}"
                }
        file_type = event['file_type']
        s3_bucket = event.get('s3_bucket', 'N/A')
        s3_key = event.get('s3_key', 'N/A')
        txn_id = event.get('txn_id')
        content_hash = event.get('content_hash')
        is_duplicate = event.get('is_duplicate')

        # Extract additional metadata for logging and return
        original_filename = event.get('original_file', 'N/A')
        timestamp_text_standardization_processed_at = event.get('timestamp_text_standardization_processed_at')

        logger.info(f"Starting semantic chunking for file type: '{file_type}' from s3://{s3_bucket}/{s3_key}")
        logger.debug(f"Standardized text length: {len(standardized_text)} characters. First 200 chars: '{standardized_text[:200]}...'")

        # Perform semantic chunking using Bedrock
        chunks = perform_semantic_chunking(standardized_text, file_type)

        logger.info(f"Semantic chunking completed successfully. Generated {len(chunks)} chunks.")

        # Store chunks in S3 instead of returning them directly
        chunks_s3_key, chunks_s3_bucket = store_chunks_to_s3(chunks, event)

        # Return only metadata and S3 reference
        return {
            'statusCode': 200,
            'chunks_count': len(chunks),
            'chunks_s3_bucket': chunks_s3_bucket,
            'chunks_s3_key': chunks_s3_key,
            'file_type': file_type,
            'original_file': original_filename,
            'text_s3_bucket': event.get('text_s3_bucket'),
            'text_s3_key': event.get('text_s3_key'),
            'txn_id' : txn_id,
            'content_hash':content_hash,
            'is_duplicate':is_duplicate,
            'client_name' : event.get('client_name'),
            'timestamp_text_standardization':event.get('timestamp_text_standardization',''),
            'timestamp_semantic_chunking': datetime.utcnow().isoformat(),
            'timestamp_text_extraction':event.get('timestamp_text_extraction', ''),
            'standardized_text_length': event.get('standardized_text_length'),
            'total_pages': event.get('total_pages'),
            'contains_images': event.get('contains_images'),
            'extracted_text_by_page':event.get('extracted_text_by_page','')
        }

    except KeyError as ke:
        logger.error(f"Missing expected key in event: {str(ke)}. Event: {json.dumps(event)}")
        return {
            'statusCode': 400,
            'error': f"Missing required event key: {str(ke)}"
        }
    except Exception as e:
        logger.exception(f"An unexpected error occurred in semantic chunking lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }

def store_chunks_to_s3(chunks, event):
    """
    Store the semantic chunks to S3 and return the S3 location.
    """
    try:
        c_name = event.get('client_name')
        # Use the same bucket as text extraction but different folder
        text_s3_bucket = event.get('text_s3_bucket', '')
        if text_s3_bucket.startswith('s3://'):
            chunks_bucket = text_s3_bucket.replace('s3://', '').split('/')[0]
        else:
            chunks_bucket = text_s3_bucket

        # Fallback to environment variable if no bucket found
        if not chunks_bucket:
            chunks_bucket = SEMANTIC_CHUNKING_BUCKET  # Use existing bucket

        logger.info(f"Using bucket for semantic chunks: {chunks_bucket}")

        # Generate a unique key for the chunks file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]

        # Extract filename from original file for better naming
        original_file = event.get('original_file', '')
        print("original-file :", original_file)
        if original_file:
            filename = original_file.split('/')[-1].split('.')[0]
        else:
            filename = 'unknown_file'

        # Store in semantic_chunks folder to separate from text extraction
        chunks_s3_key = f"{c_name}/semantic_chunks/{timestamp}_{unique_id}_{filename}_chunks.json"

        # Prepare chunks data with metadata
        chunks_data = {
            'metadata': {
                'original_file': event.get('original_file'),
                'file_type': event.get('file_type'),
                'processed_at': datetime.now().isoformat(),
                'chunks_count': len(chunks),
                'total_pages': event.get('total_pages'),
                'source_text_folder': event.get('text_folder')
            },
            'chunks': chunks
        }

        # Store to S3
        s3_client.put_object(
            Bucket=chunks_bucket,
            Key=chunks_s3_key,
            Body=json.dumps(chunks_data, indent=2),
            ContentType='application/json'
        )

        logger.info(f"Successfully stored {len(chunks)} chunks to s3://{chunks_bucket}/{chunks_s3_key}")

        return chunks_s3_key, chunks_bucket

    except Exception as e:
        logger.error(f"Failed to store chunks to S3: {str(e)}")
        raise Exception(f"Failed to store chunks to S3: {str(e)}")


def perform_semantic_chunking(text: str, file_type: str) -> list:
    logger.info(f"Initiating semantic chunking with Bedrock for file type: '{file_type}'.")
    try:
        prompt = create_chunking_prompt(text, file_type)
        logger.debug(f"Generated Bedrock prompt (first 500 chars): '{prompt[:500]}...'")

        # Call Bedrock Claude model
        model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        bedrock_payload = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "temperature": 0,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        })

        logger.info(f"Invoking Bedrock model '{model_id}' for semantic chunking.")
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=bedrock_payload
        )
        logger.info("Received response from Bedrock.")

        response_body = json.loads(response['body'].read())
        logger.debug(f"Raw Bedrock response body: {json.dumps(response_body)}")

        if 'content' not in response_body or not response_body['content']:
            logger.warning("Bedrock response did not contain expected 'content' field or it was empty. Falling back to simple chunking.")
            return simple_chunking(text)

        chunked_result = response_body['content'][0]['text']
        logger.debug(f"Extracted chunked result text from Bedrock (first 500 chars): '{chunked_result[:500]}...'")

        # Parse the response to extract chunks
        chunks = parse_chunking_response(chunked_result)
        logger.info(f"Successfully parsed Bedrock response. Number of chunks: {len(chunks)}")

        return chunks

    except Exception as e:
        logger.exception(f"An unexpected error occurred during Bedrock semantic chunking: {str(e)}")
        logger.warning("Falling back to simple chunking.")
        return simple_chunking(text)

def create_chunking_prompt(text: str, file_type: str) -> str:
    logger.debug(f"Creating chunking prompt for file type: '{file_type}'.")
    if file_type == 'xlsx':
        prompt = f"""You are analyzing spreadsheet text extracted from an XLSX file.
Identify each logical step/section as a separate chunk.
Do not merge unrelated sections.

Return only valid JSON in this format:
{{
  "chunks": [
    {{
      "chunk_id": 1,
      "content": "chunk content here",
      "semantic_type": "process",
      "summary": "brief summary"
    }}
  ]
}}"""
        logger.debug("Generated XLSX chunking prompt.")
    else:
        prompt = f"""Please analyze the following document content and break it down into semantically meaningful chunks. Each chunk should represent a complete thought, process step, or logical section.

Content to chunk:
{text}

Please return the chunks in the following JSON format:
{{
    "chunks": [
        {{
            "chunk_id": 1,
            "content": "chunk content here",
            "semantic_type": "process|procedure|section|step",
            "summary": "brief summary of this chunk"
        }}
    ]
}}"""
        logger.debug("Generated general document chunking prompt.")

    return prompt

def parse_chunking_response(response_text: str) -> list:
    logger.info("Attempting to parse Bedrock chunking response.")
    try:
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            logger.debug("Extracted potential JSON string from response.")
            parsed_response = json.loads(json_str)
            chunks = parsed_response.get('chunks', [])
            logger.info(f"Successfully parsed JSON response. Found {len(chunks)} chunks.")
            return chunks
        else:
            logger.warning("No JSON object found in Bedrock response. Falling back to simple chunking.")
            return simple_chunking(response_text)

    except json.JSONDecodeError as jde:
        logger.error(f"Failed to parse JSON response from Bedrock: {str(jde)}. Response text (first 200 chars): '{response_text[:200]}...'")
        logger.warning("Falling back to simple chunking due to JSON decode error.")
        return simple_chunking(response_text)
    except Exception as e:
        logger.exception(f"An unexpected error occurred during parsing chunking response: {str(e)}")
        logger.warning("Falling back to simple chunking due to unexpected parsing error.")
        return simple_chunking(response_text)

def simple_chunking(text: str) -> list:
    logger.warning("Executing fallback simple_chunking method.")
    chunks = []
    paragraphs = text.split('\n\n')

    for i, paragraph in enumerate(paragraphs):
        if paragraph.strip():
            chunk_content = paragraph.strip()
            chunks.append({
                'chunk_id': i + 1,
                'content': chunk_content,
                'semantic_type': 'general_fallback',
                'summary': chunk_content[:100] + '...' if len(chunk_content) > 100 else chunk_content
            })

    logger.info(f"Simple chunking completed. Generated {len(chunks)} chunks.")
    return chunks
