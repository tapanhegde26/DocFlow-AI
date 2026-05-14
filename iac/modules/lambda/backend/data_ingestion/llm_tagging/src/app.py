import json
import boto3
import logging
import base64
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_client = boto3.client('bedrock-runtime')

def decode_document_content(event):
    """
    Extract and decode document content from various sources
    """
    # First try document_content
    if event.get('document_content'):
        return event['document_content']
        
    # Try document_binary (hex encoded)
    if event.get('document_binary'):
        try:
            # Decode hex to bytes, then to string
            hex_data = event['document_binary']
            byte_data = bytes.fromhex(hex_data)
            return byte_data.decode('utf-8')
        except Exception as e:
            logger.warning(f"Failed to decode document_binary: {e}")
    
    return None

def decode_hex_content(hex_string):
    """
    Decode hexadecimal string to readable text
    """
    try:
        byte_data = bytes.fromhex(hex_string)
        return byte_data.decode('utf-8')
    except Exception as e:
        logger.warning(f"Failed to decode hex content: {e}")
        return hex_string  # Return original if decoding fails

def extract_process_details(decoded_content):
    """
    Extract relevant information from the JSON document for tagging
    """
    try:
        doc_data = json.loads(decoded_content)
        
        # Extract key information for tagging
        process_details = doc_data.get('process_details', {})
        metadata = doc_data.get('metadata', {})
        
        # Build a text summary for LLM analysis
        summary_parts = []
        
        if process_details.get('name'):
            summary_parts.append(f"Process Name: {process_details['name']}")
        
        if process_details.get('description'):
            summary_parts.append(f"Description: {process_details['description']}")
        
        if process_details.get('category'):
            summary_parts.append(f"Category: {process_details['category']}")
        
        if process_details.get('steps'):
            summary_parts.append(f"Steps: {'; '.join(process_details['steps'])}")
        
        if process_details.get('location_info', {}).get('section_location'):
            summary_parts.append(f"Section: {process_details['location_info']['section_location']}")
        
        return '\n'.join(summary_parts)
    
    except json.JSONDecodeError:
        # If it's not JSON, return the raw content
        return decoded_content

def lambda_handler(event, context):
    """
    Tag process documents using LLM model
    """
    try:
        # Skip processing if document is duplicate
        if event.get('is_duplicate', False):
            logger.info(f"Skipping LLM tagging for duplicate document: {event['object_key']}")
            return {
                **event,
                'llm_tags': [],
                'tagging_skipped': True,
                'skip_reason': 'duplicate_document'
            }
        
        object_key = event['object_key']
        
        # Try to get document content from multiple sources
        document_content = decode_document_content(event)
        
        if not document_content:
            logger.warning(f"No document content available for tagging: {object_key}")
            return {
                **event,
                'llm_tags': [],
                'tagging_skipped': True,
                'skip_reason': 'no_content'
            }
        
        # Extract process details for better tagging
        processed_content = extract_process_details(document_content)
        
        if not processed_content:
            logger.warning(f"Could not extract meaningful content for tagging: {object_key}")
            return {
                **event,
                'llm_tags': [],
                'tagging_skipped': True,
                'skip_reason': 'no_meaningful_content'
            }
        
        # Prepare prompt for LLM
        prompt = f"""Analyze the following process document and generate exactly 5 relevant tags.

FOCUS AREAS:
1. Affected Users
   - Who is impacted: Employees, Customers, Managers, Contractors, External Partners, Leadership

2. Content Classification  
   - Content type: Policy, Procedure, Guidelines, Training, Reference, Compliance, Security, Workflow

3. Process Category
   - Business function: HR, Finance, IT, Operations, Marketing, Legal, Customer Service

4. Subject Matter
   - Specific topic: Onboarding, Payroll, Communication, Branding, Returns, Data Management, Quality Control

5. Implementation Level
   - Operational scope: Department-wide, Company-wide, Role-specific, Project-based, Self-Service

DOCUMENT CONTENT:
{document_content}

OUTPUT FORMAT:
Provide response as JSON array of exactly 5 tags, prioritizing most specific categories.

EXAMPLE:
["Customers", "Returns", "Customer Service", "Workflow", "Self-Service"]


Response:"""
        
        # Call Bedrock (using Claude)
        model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        llm_response = response_body['content'][0]['text']
        
        # Parse LLM response to extract tags
        try:
            # Try to extract JSON array from response
            import re
            json_match = re.search(r'\[.*?\]', llm_response, re.DOTALL)
            if json_match:
                tags = json.loads(json_match.group())
            else:
                # Fallback: split by common delimiters
                tags = [tag.strip() for tag in llm_response.replace('\n', ',').split(',') if tag.strip()]
        except json.JSONDecodeError:
            # Fallback parsing
            tags = [tag.strip() for tag in llm_response.replace('\n', ',').split(',') if tag.strip()]
        
        # Clean and validate tags
        cleaned_tags = []
        for tag in tags:
            clean_tag = tag.strip().strip('"').strip("'").strip('[]')
            if clean_tag and len(clean_tag) <= 50:  # Reasonable tag length limit
                cleaned_tags.append(clean_tag)
        
        logger.info(f"Generated {len(cleaned_tags)} tags for document: {object_key}")
        
        # Decode content if it's in hex format for the response
        readable_content = document_content
        if event.get('content') and isinstance(event['content'], str):
            # Check if the content looks like hex (all chars are valid hex)
            try:
                if all(c in '0123456789abcdefABCDEF' for c in event['content']):
                    readable_content = decode_hex_content(event['content'])
            except:
                pass
        
        result = {
            **event,
            'llm_tags': cleaned_tags,
            'tagging_skipped': False,
            'statusCode': 200,
            # Include decoded content in response
            'content': readable_content if 'content' in event else document_content
        }
        
        return result
    
    except ClientError as e:
        logger.error(f"Bedrock error: {e}")
        return {
            **event,
            'llm_tags': [],
            'tagging_skipped': True,
            'skip_reason': 'bedrock_error',
            'statusCode': 500,
            'error': f'LLM tagging failed: {str(e)}'
        }
    
    except Exception as e:
        logger.error(f"Error in LLM tagging: {str(e)}")
        return {
            **event,
            'llm_tags': [],
            'tagging_skipped': True,
            'skip_reason': 'processing_error',
            'statusCode': 500,
            'error': f'Unexpected error in LLM tagging: {str(e)}'
        }
