import json
import boto3
import os
import logging
from datetime import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
rds = boto3.client("rds-data")

def lambda_handler(event, context):
    """
    Add LLM tags to existing processed documents and store enhanced version in tagged_processes folder
    """
    try:
        logger.info(f"Event: {event}")
        
        # Skip processing if document is duplicate or tagged duplicate
        if (event.get('is_duplicate', False) or
            event.get('is_tagged_duplicate', False) or
            event.get('tagging_skipped', False)):
            skip_reason = 'duplicate' if event.get('is_duplicate') else \
                        'tagged_duplicate' if event.get('is_tagged_duplicate') else \
                        'tagging_skipped'
            logger.info(f"Skipping document tagging due to: {skip_reason} for {event['object_key']}")
            return {
                **event,
                'tagged_document_stored': False,
                'skip_reason': skip_reason,
                'statusCode': 200
            }

        bucket_name = event['bucket_name']
        original_object_key = event['object_key']
        llm_tags = event.get('llm_tags', [])
        
        # Read the existing JSON file from S3
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=original_object_key)
            existing_content = response['Body'].read().decode('utf-8')
            existing_json = json.loads(existing_content)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.error(f"Original file not found: {original_object_key}")
                return {
                    **event,
                    'tagged_document_stored': False,
                    'statusCode': 404,
                    'error': {
                        'Error': 'FileNotFound',
                        'Cause': f'Original file {original_object_key} not found'
                    }
                }
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in original file: {original_object_key}")
            return {
                **event,
                'tagged_document_stored': False,
                'statusCode': 400,
                'error': {
                    'Error': 'InvalidJSON',
                    'Cause': f'Cannot parse JSON from {original_object_key}'
                }
            }
        
        # Create enhanced JSON with tags
        enhanced_json = {
            **existing_json,  # Keep all existing content
            'llm_tags': llm_tags,
            'tag_categories': categorize_tags(llm_tags),
            'tagging_info': {
                'llm_model_used': 'anthropic.claude-3-sonnet-20240229-v1:0',
                'tagging_timestamp': datetime.utcnow().isoformat(),
                'tags_count': len(llm_tags),
                'tagging_status': 'completed',
                'original_object_key': original_object_key
            }
        }

        print(f"enhanced json: {enhanced_json}")
        
        # Generate new object key for tagged_processes folder
        # Convert: processes/Client1e/2025/08/29/brand_voice_guidelines_5e0c8cbb.json
        # To: tagged_processes/Client1e/2025/08/29/brand_voice_guidelines_5e0c8cbb.json
        if original_object_key.startswith('processes/'):
            relative_path = original_object_key[10:]  # Remove 'processes/' prefix
            tagged_object_key = f"tagged_processes/{relative_path}"
        else:
            # If it doesn't start with 'processes/', just add tagged_processes prefix
            tagged_object_key = f"tagged_processes/{original_object_key}"
        
        # Prepare metadata for S3 object
        original_metadata = response.get('Metadata', {})
        s3_metadata = {
            **original_metadata,  # Keep existing metadata
            'original-key': original_object_key.replace('/', '-').replace(' ', '-')[:255],
            'tags-count': str(len(llm_tags)),
            'tagging-date': datetime.utcnow().strftime('%Y-%m-%d'),
            'tagged': 'true'
        }
        
        # Add primary tags to metadata (limit to avoid metadata size limits)
        primary_tags = llm_tags[:5]  # Take first 5 tags to avoid metadata limits
        for i, tag in enumerate(primary_tags):
            # Clean tag for metadata (remove special characters and limit length)
            clean_tag = ''.join(c for c in tag if c.isalnum() or c in ['-', '_'])[:20]
            if clean_tag:  # Only add if there's content after cleaning
                s3_metadata[f'tag-{i+1}'] = clean_tag
        
        # Get original content type
        content_type = response.get('ContentType', 'application/json')
        
        # Store the enhanced document in tagged_processes folder
        s3_client.put_object(
            Bucket=bucket_name,
            Key=tagged_object_key,
            Body=json.dumps(enhanced_json, indent=2, ensure_ascii=False),
            ContentType=content_type,
            Metadata=s3_metadata,
            ServerSideEncryption='AES256'
        )
        
        # Write record to database
        insert_process_record(enhanced_json, event)
        insert_process_record(enhanced_json, event)

        # Create a searchable index entry
        index_entry = {
            'object_key': tagged_object_key,
            'original_key': original_object_key,
            'tags': llm_tags,
            'categories': categorize_tags(llm_tags),
            'tagging_date': datetime.utcnow().isoformat(),
            'process_name': enhanced_json.get('metadata', {}).get('process_name', ''),
            'process_id': enhanced_json.get('metadata', {}).get('process_id', ''),
            'process_uuid': enhanced_json.get('metadata', {}).get('process_uuid', ''),
            'content_preview': str(enhanced_json.get('process_details', {}).get('description', ''))[:500]
        }
        
        # Generate index key
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        safe_filename = original_object_key.replace('/', '_').replace(' ', '_')
        index_key = f"tagged_processes/_index/{timestamp}_{safe_filename}_index.json"
                
        s3_client.put_object(
            Bucket=bucket_name,
            Key=index_key,
            Body=json.dumps(index_entry, indent=2, ensure_ascii=False),
            ContentType='application/json',
            Metadata={'type': 'search-index', 'original-key': original_object_key.replace('/', '-')[:255]},
            ServerSideEncryption='AES256'
        )
        
        logger.info(f"Successfully created enhanced document: {tagged_object_key}")
        logger.info(f"Successfully created index entry: {index_key}")
        logger.info(f"Added {len(llm_tags)} tags: {', '.join(llm_tags[:10])}")
        
        result = {
            **event,
            'tagged_document_stored': True,
            'tagged_object_key': tagged_object_key,
            'original_object_key': original_object_key,
            'index_object_key': index_key,
            'final_tags': llm_tags,
            'tag_categories': categorize_tags(llm_tags),
            'storage_timestamp': datetime.utcnow().isoformat(),
            'statusCode': 200
        }
        
        return result
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"S3 error creating enhanced document: {error_code} - {error_message}")
        return {
            **event,
            'tagged_document_stored': False,
            'statusCode': 500,
            'error': {
                'Error': f'S3Error.{error_code}',
                'Cause': error_message
            }
        }
    
    except Exception as e:
        error_message = str(e)
        logger.error(f"Unexpected error creating enhanced document: {error_message}")
        return {
            **event,
            'tagged_document_stored': False,
            'statusCode': 500,
            'error': {
                'Error': 'UnexpectedError',
                'Cause': error_message
            }
        }

def categorize_tags(tags):
    """
    Categorize tags into predefined categories for better organization
    """
    categories = {
        'department': [],
        'process_type': [],
        'subject_matter': [],
        'priority': [],
        'stakeholders': [],
        'other': []
    }
    
    # Define category keywords
    department_keywords = ['hr', 'finance', 'operations', 'it', 'legal', 'marketing',
                          'sales', 'procurement', 'compliance', 'human resources']
    process_type_keywords = ['policy', 'procedure', 'workflow', 'guideline', 'standard',
                             'protocol', 'manual', 'checklist', 'sop', 'operational']
    priority_keywords = ['critical', 'important', 'standard', 'low', 'high', 'urgent', 'routine']
    stakeholder_keywords = ['manager', 'employee', 'contractor', 'external', 'customer',
                            'vendor', 'executive', 'admin', 'staff']
    
    for tag in tags:
        tag_lower = tag.lower()
        categorized = False
        
        # Check department
        if any(keyword in tag_lower for keyword in department_keywords):
            categories['department'].append(tag)
            categorized = True
        
        # Check process type
        if any(keyword in tag_lower for keyword in process_type_keywords):
            categories['process_type'].append(tag)
            categorized = True
        
        # Check priority
        if any(keyword in tag_lower for keyword in priority_keywords):
            categories['priority'].append(tag)
            categorized = True
        
        # Check stakeholders
        if any(keyword in tag_lower for keyword in stakeholder_keywords):
            categories['stakeholders'].append(tag)
            categorized = True
        
        # If not categorized, add to subject_matter or other
        if not categorized:
            if len(tag) > 15:  # Longer tags likely to be subject matter
                categories['subject_matter'].append(tag)
            else:
                categories['other'].append(tag)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}

def insert_process_record(data: dict, event: dict):
    """
    Connects to PostgreSQL and inserts a record into the 'processes' table using RDS Data API
    Environment variables required:
        - PGDATABASE
        - DB_SECRET_NAME
        - DB_CLUSTER_ARN
    """

    logger.info(f"Inserting process record...... received data: {data} and event: {event}")
    dbname = os.environ["PGDATABASE"]
    secret = os.environ["DB_SECRET_NAME"]
    cluster = os.environ["DB_CLUSTER_ARN"]

    try:
        # Extract content_hash from event metadata (most reliable source)
        content_hash = event.get('metadata', {}).get('content_hash', '')

        # Fallback to extracting from document content if not in event metadata
        if not content_hash:
            content_hash = data.get("metadata", {}).get("content_hash", "")

        flags_value = {}        
        is_duplicate = data["metadata"]["is_duplicate"]
        logger.info(f"is_duplicate: {is_duplicate}")
        if str(is_duplicate).lower() == "true":
            flags_value["conflict"] = True


        # the tagged_processes are stored in OpenSearch, in the project_s3_key
        process_url = event.get("bucket_name") + "/tagged_" + event.get("object_key")
        logger.info(f"process_url: {process_url}")


        sql = """
        INSERT INTO processes (client_id, process_url, source_sop_url, title, domain, llm_tags, document_type, s3_key, mermaid, file_hash, flags) 
        VALUES (:client_id, :process_url, :source_sop_url, :title, :domain, string_to_array(:llm_tags, ','),:document_type, :s3_key, :mermaid, :file_hash, :flags::jsonb)
        """

        parameters = [
            {"name": "client_id", "value": {"stringValue": data["metadata"]["client_name"]}},
            {"name": "process_url", "value": {"stringValue": process_url}},
            {"name": "source_sop_url", "value": {"stringValue": data["metadata"]["source_file"]["original_filename"]}},
            {"name": "title", "value": {"stringValue": data["metadata"]["process_name"]}},
            {"name": "domain", "value": {"stringValue": data["process_details"]["category"]}},
            {"name": "llm_tags", "value": {"stringValue": ",".join(data["llm_tags"])}},
            {"name": "document_type", "value": {"stringValue": "process"}},
            {"name": "s3_key", "value": {"stringValue": process_url}},
            {"name": "mermaid", "value": {"stringValue": data["process_details"]["mermaid_syntax"]}},
            {"name": "file_hash", "value": {"stringValue": content_hash}},
            {"name": "flags","value": {"stringValue": json.dumps(flags_value)}}
        ]

        logger.info("Executing SQL via RDS Data API...")
        logger.info(f"Inserting record with content_hash: {content_hash}")
        
        response = rds.execute_statement(
            resourceArn=cluster,
            secretArn=secret,
            database=dbname,
            sql=sql,
            parameters=parameters
        )
        
        logger.info("Insert response:\n%s", json.dumps(response, indent=2))
        rows_inserted = response.get("numberOfRecordsUpdated", 0)
        if rows_inserted:
            logger.info(f"Inserted {rows_inserted} process row(s) for client: {data['metadata']['client_name']} with hash: {content_hash}")
        else:
            logger.warning("No rows inserted into DB.")
        
        return rows_inserted
    except Exception as e:
        logger.exception(f"Failed to insert process record into DB. Parameters:\n{json.dumps(parameters, indent=2)}")
        return 0
