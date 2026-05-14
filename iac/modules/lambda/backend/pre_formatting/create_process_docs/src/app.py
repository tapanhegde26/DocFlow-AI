import json
import boto3
from datetime import datetime
import uuid
import os
import logging
import re

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

s3_client = boto3.client('s3')
rds = boto3.client("rds-data")

def lambda_handler(event, context):
    logger.info("Lambda function 'process_json_creator' started with event: %s", json.dumps(event))
    try:
        # Initialize variables for both distinct and non-distinct processes
        distinct_processes = None
        non_distinct_processes = None
        semantic_chunks = None
        
        # Handle distinct_processes
        if 'distinct_processes' in event and isinstance(event['distinct_processes'], dict):
            distinct_processes_meta = event['distinct_processes']
            
            # Check if it's metadata pointing to S3 or actual process data
            if 'processes_s3_bucket' in distinct_processes_meta and 'processes_s3_key' in distinct_processes_meta and distinct_processes_meta.get('processes_count', 0) > 0:
                # It's metadata pointing to S3 location
                processes_s3_bucket = distinct_processes_meta['processes_s3_bucket']
                processes_s3_key = distinct_processes_meta['processes_s3_key']
                logger.info(f"Reading distinct processes from S3: s3://{processes_s3_bucket}/{processes_s3_key}")
                
                try:
                    # Read processes data from S3
                    response = s3_client.get_object(Bucket=processes_s3_bucket, Key=processes_s3_key)
                    processes_data = json.loads(response['Body'].read().decode('utf-8'))
                    
                    # Extract distinct_processes from the stored format
                    if 'distinct_processes' in processes_data:
                        distinct_processes = processes_data['distinct_processes']
                    else:
                        # If it's stored in the root level
                        distinct_processes = processes_data
                    
                    logger.info(f"Successfully loaded distinct processes from S3")
                    
                except Exception as s3_error:
                    logger.error(f"Failed to read distinct processes from S3: {str(s3_error)}")
                    return {
                        'statusCode': 500,
                        'error': f"Failed to read distinct processes from S3: {str(s3_error)}"
                    }
            else:
                # It's actual process data (backward compatibility)
                distinct_processes = distinct_processes_meta
                logger.info("Using distinct_processes from event payload (backward compatibility)")
        
        # Handle non_distinct_processes
        if 'non_distinct_processes' in event and isinstance(event['non_distinct_processes'], dict):
            non_distinct_processes_meta = event['non_distinct_processes']
            
            # Check if it's metadata pointing to S3 or actual process data
            if 'processes_s3_bucket' in non_distinct_processes_meta and 'processes_s3_key' in non_distinct_processes_meta and non_distinct_processes_meta.get('processes_count', 0) > 0:
                # It's metadata pointing to S3 location
                non_distinct_processes_s3_bucket = non_distinct_processes_meta['processes_s3_bucket']
                non_distinct_processes_s3_key = non_distinct_processes_meta['processes_s3_key']
                logger.info(f"Reading non-distinct processes from S3: s3://{non_distinct_processes_s3_bucket}/{non_distinct_processes_s3_key}")
                
                try:
                    # Read non-distinct processes data from S3
                    response = s3_client.get_object(Bucket=non_distinct_processes_s3_bucket, Key=non_distinct_processes_s3_key)
                    non_distinct_processes_data = json.loads(response['Body'].read().decode('utf-8'))
                    
                    # Extract non_distinct_processes from the stored format
                    if 'non_distinct_processes' in non_distinct_processes_data:
                        non_distinct_processes = non_distinct_processes_data['non_distinct_processes']
                    elif 'processes' in non_distinct_processes_data:
                        non_distinct_processes = {'processes': non_distinct_processes_data['processes']}
                    else:
                        # If it's stored in the root level
                        non_distinct_processes = non_distinct_processes_data
                    
                    logger.info(f"Successfully loaded non-distinct processes from S3")
                    
                except Exception as s3_error:
                    logger.error(f"Failed to read non-distinct processes from S3: {str(s3_error)}")
                    return {
                        'statusCode': 500,
                        'error': f"Failed to read non-distinct processes from S3: {str(s3_error)}"
                    }
            else:
                # It's actual process data (backward compatibility)
                non_distinct_processes = non_distinct_processes_meta
                logger.info("Using non_distinct_processes from event payload (backward compatibility)")
        
        # Handle semantic chunks (required for both types of processes)
        if 'chunks_s3_bucket' in event and 'chunks_s3_key' in event:
            chunks_s3_bucket = event['chunks_s3_bucket']
            chunks_s3_key = event['chunks_s3_key']
            logger.info(f"Reading semantic chunks from S3: s3://{chunks_s3_bucket}/{chunks_s3_key}")
            
            try:
                chunks_response = s3_client.get_object(Bucket=chunks_s3_bucket, Key=chunks_s3_key)
                chunks_data = json.loads(chunks_response['Body'].read().decode('utf-8'))
                
                if 'chunks' in chunks_data:
                    semantic_chunks = chunks_data['chunks']
                else:
                    semantic_chunks = chunks_data
                
                logger.info(f"Successfully loaded {len(semantic_chunks)} chunks from S3")
            except Exception as s3_error:
                logger.error(f"Failed to read chunks from S3: {str(s3_error)}")
                return {
                    'statusCode': 500,
                    'error': f"Failed to read chunks from S3: {str(s3_error)}"
                }
        else:
            raise KeyError("'chunks_s3_bucket' and 'chunks_s3_key'")
        
        # Legacy path: processes_s3_bucket directly in event (for backward compatibility)
        if not distinct_processes and 'processes_s3_bucket' in event and 'processes_s3_key' in event:
            processes_s3_bucket = event['processes_s3_bucket']
            processes_s3_key = event['processes_s3_key']
            logger.info(f"Reading distinct processes from S3 (legacy path): s3://{processes_s3_bucket}/{processes_s3_key}")
            
            try:
                # Read processes data from S3
                response = s3_client.get_object(Bucket=processes_s3_bucket, Key=processes_s3_key)
                processes_data = json.loads(response['Body'].read().decode('utf-8'))
                
                # Extract distinct_processes from the stored format
                if 'distinct_processes' in processes_data:
                    distinct_processes = processes_data['distinct_processes']
                else:
                    distinct_processes = processes_data
                
                logger.info(f"Successfully loaded processes from S3")
                    
            except Exception as s3_error:
                logger.error(f"Failed to read data from S3: {str(s3_error)}")
                return {
                    'statusCode': 500,
                    'error': f"Failed to read data from S3: {str(s3_error)}"
                }
        
        # Validate that we have at least one type of processes and semantic chunks
        if not distinct_processes and not non_distinct_processes:
            raise KeyError("Either 'distinct_processes' or 'non_distinct_processes' must be provided")
        
        if not semantic_chunks:
            raise KeyError("'semantic_chunks' data is required")

        # Validate required fields
        if 'file_type' not in event:
            raise KeyError("'file_type'")

        file_type = event['file_type']
        original_filename = event.get('original_file', '')
        # The above code is defining a variable `client_name` in Python.
        client_name = event.get('client_name')
        provider_name = event.get('client_name')
        txn_id = event.get('txn_id')
        content_hash = event.get('content_hash')
        is_duplicate = event.get('is_duplicate')
        timestamp_text_extraction = event.get('timestamp_text_extraction', '')
        timestamp_text_standardization = event.get('timestamp_text_standardization', '')
        timestamp_semantic_chunking = event.get('timestamp_semantic_chunking','')
        timestamp_identify_processes = event.get('timestamp_identify_processes','')
        timestamp_create_process_docs = datetime.now().isoformat()
        
        logger.info(f"Extracted event parameters: file_type={file_type}, original_filename={original_filename}")

        # Get target S3 bucket from environment variable
        output_bucket = os.environ.get('OUTPUT_BUCKET')
        if not output_bucket:
            logger.error("OUTPUT_BUCKET environment variable is not set.")
            raise ValueError("OUTPUT_BUCKET environment variable is not configured.")
        processes_bucket = None
        if non_distinct_processes and 'non_distinct_processes' in event:
            processes_bucket = event['non_distinct_processes'].get('processes_s3_bucket')
            # Fallback to main processes bucket if not specified in non_distinct_processes
        if not processes_bucket:
            processes_bucket = event.get('processes_s3_bucket')
            
        logger.info(f"Target buckets - Distinct processes: {output_bucket}, Non-distinct processes: {processes_bucket}")
        
        created_files = []
        total_distinct_processes = 0
        total_non_distinct_processes = 0
        
        # Process distinct_processes(use output_bucket)
        if distinct_processes and distinct_processes_meta.get('processes_count', 0) > 0:
            logger.info("Processing distinct processes")
            
            # Determine source S3 info for distinct processes
            if 'distinct_processes' in event and 'processes_s3_bucket' in event['distinct_processes']:
                source_s3_bucket = event['distinct_processes']['processes_s3_bucket']
                source_s3_key = event['distinct_processes']['processes_s3_key']
            else:
                source_s3_bucket = event.get('processes_s3_bucket', '')
                source_s3_key = event.get('processes_s3_key', '')
            
            # Handle different file types differently for distinct processes
            if file_type == 'xlsx' and 'sheets' in distinct_processes:
                logger.info("Processing XLSX file with sheets structure for distinct processes")
                distinct_created_files = process_xlsx_sheets(
                    distinct_processes, 
                    semantic_chunks, 
                    file_type, 
                    original_filename, 
                    source_s3_bucket, 
                    source_s3_key, 
                    output_bucket,
                    client_name,
                    content_hash,
                    is_duplicate,
                    provider_name,
                    timestamp_text_extraction,
                    timestamp_text_standardization,
                    timestamp_semantic_chunking,
                    timestamp_identify_processes,
                    timestamp_create_process_docs,
                    process_type="distinct"
                )
            else:
                logger.info("Processing standard document with distinct processes structure")
                distinct_created_files = process_standard_documents(
                    distinct_processes, 
                    semantic_chunks, 
                    file_type, 
                    original_filename, 
                    source_s3_bucket, 
                    source_s3_key, 
                    output_bucket,
                    client_name,
                    content_hash,
                    is_duplicate,
                    provider_name,
                    timestamp_text_extraction,
                    timestamp_text_standardization,
                    timestamp_semantic_chunking,
                    timestamp_identify_processes,
                    timestamp_create_process_docs,
                    process_type="distinct"
                )
            
            created_files.extend(distinct_created_files)
            total_distinct_processes = len(distinct_created_files)
            logger.info(f"Created {total_distinct_processes} distinct process files in {output_bucket}")
        
        # Process non_distinct_processes (use processes_bucket)
        if non_distinct_processes and non_distinct_processes_meta.get('processes_count', 0) > 0:
            if not processes_bucket:
                logger.error("No processes bucket specified for non-distinct processes")
                raise ValueError("processes_s3_bucket is required for non-distinct processes")
                
            logger.info(f"Processing non-distinct processes in bucket: {processes_bucket}")
            
            # Determine source S3 info for non-distinct processes
            if 'non_distinct_processes' in event and 'processes_s3_bucket' in event['non_distinct_processes']:
                source_s3_bucket = event['non_distinct_processes']['processes_s3_bucket']
                source_s3_key = event['non_distinct_processes']['processes_s3_key']
            else:
                # Fallback to main event S3 info if not specified
                source_s3_bucket = event.get('processes_s3_bucket', '')
                source_s3_key = event.get('processes_s3_key', '')
            
            # Handle different file types differently for non-distinct processes
            if file_type == 'xlsx' and 'sheets' in non_distinct_processes:
                logger.info("Processing XLSX file with sheets structure for non-distinct processes")
                non_distinct_created_files = process_xlsx_sheets(
                    non_distinct_processes, 
                    semantic_chunks, 
                    file_type, 
                    original_filename, 
                    source_s3_bucket, 
                    source_s3_key, 
                    processes_bucket,
                    client_name,
                    content_hash,
                    is_duplicate,
                    provider_name,
                    timestamp_text_extraction,
                    timestamp_text_standardization,
                    timestamp_semantic_chunking,
                    timestamp_identify_processes,
                    timestamp_create_process_docs,
                    process_type="non_distinct"
                )
            else:
                logger.info("Processing standard document with non-distinct processes structure")
                non_distinct_created_files = process_standard_documents(
                    non_distinct_processes, 
                    semantic_chunks, 
                    file_type, 
                    original_filename, 
                    source_s3_bucket, 
                    source_s3_key, 
                    processes_bucket,
                    client_name,
                    content_hash,
                    is_duplicate,
                    provider_name,
                    timestamp_text_extraction,
                    timestamp_text_standardization,
                    timestamp_semantic_chunking,
                    timestamp_identify_processes,
                    timestamp_create_process_docs,
                    process_type="non_distinct"
                )
            
            created_files.extend(non_distinct_created_files)
            total_non_distinct_processes = len(non_distinct_created_files)
            logger.info(f"Created {total_non_distinct_processes} non-distinct process files in {processes_bucket}")
        
        total_processes = total_distinct_processes + total_non_distinct_processes
        logger.info(f"Finished processing. Total files created: {len(created_files)} (Distinct: {total_distinct_processes}, Non-distinct: {total_non_distinct_processes})")
        
        return {
            'statusCode': 200,
            'client_name': client_name,
            'document_status': 'draft',
            'provider_name':provider_name,
            'txn_id': txn_id,
            'content_hash' : content_hash,
            'is_duplicate' : str(is_duplicate),
            'created_files': created_files,
            'file_type': file_type,
            'original_file': original_filename,
            'total_processes': total_processes,
            'total_distinct_processes': total_distinct_processes,
            'total_non_distinct_processes': total_non_distinct_processes,
            'target_buckets': {
                'distinct_processes': output_bucket,
                'non_distinct_processes': processes_bucket
            },
            'timestamp_text_extraction': event.get('timestamp_text_extraction', ''),
            'timestamp_text_standardization': event.get('timestamp_text_standardization', ''),
            'timestamp_semantic_chunking': event.get('timestamp_semantic_chunking',''),
            'timestamp_identify_processes': event.get('timestamp_identify_processes',''),
            'timestamp_create_process_docs': datetime.now().isoformat(),
            'source_file': {
                'bucket': source_s3_bucket if 'source_s3_bucket' in locals() else '',
                'key': source_s3_key if 'source_s3_key' in locals() else '',
                'filename': original_filename
            },
            'input_references': {
                'processes_s3_bucket': event.get('processes_s3_bucket'),
                'processes_s3_key': event.get('processes_s3_key'),
                'chunks_s3_bucket': event.get('chunks_s3_bucket'),
                'chunks_s3_key': event.get('chunks_s3_key'),
                'distinct_processes_s3_bucket': event.get('distinct_processes', {}).get('processes_s3_bucket'),
                'distinct_processes_s3_key': event.get('distinct_processes', {}).get('processes_s3_key'),
                'non_distinct_processes_s3_bucket': event.get('non_distinct_processes', {}).get('processes_s3_bucket'),
                'non_distinct_processes_s3_key': event.get('non_distinct_processes', {}).get('processes_s3_key')
            },
            'processing_summary': {
                'distinct_processes_success': total_distinct_processes > 0 if distinct_processes else None,
                'non_distinct_processes_success': total_non_distinct_processes > 0 if non_distinct_processes else None,
                'overall_success': len(created_files) > 0
            },
            'file_type': file_type,
            'txn_id': txn_id,
            'document_type': (distinct_processes or non_distinct_processes or {}).get('document_type', 'general')
        }
        
    except KeyError as ke:
        logger.error(f"Missing expected key in event: {str(ke)}")
        return {
            'statusCode': 400,
            'error': f"Missing required event key: {str(ke)}"
        }
    except ValueError as ve:
        logger.error(f"Configuration error: {str(ve)}")
        return {
            'statusCode': 500,
            'error': str(ve)
        }
    except Exception as e:
        logger.exception(f"Error in lambda_handler while creating process JSON files: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }
        
def process_xlsx_sheets(distinct_processes, semantic_chunks, file_type, original_filename, source_bucket, source_key, target_bucket, client_name,content_hash,is_duplicate,provider_name,timestamp_text_extraction,
                timestamp_text_standardization,
                timestamp_semantic_chunking,
                timestamp_identify_processes,
                timestamp_create_process_docs,
                process_type="distinct"):
    """Process XLSX files with one document per sheet"""
    logger.info(f"Processing XLSX sheets structure - one document per sheet ({process_type} processes)")
    created_files = []
    
    try:
        sheets = distinct_processes.get('sheets', {})
        
        for sheet_name, categories in sheets.items():
            logger.info(f"Creating single document for sheet: {sheet_name} ({process_type})")
            
            # Combine all categories and steps for this sheet with hierarchy
            all_steps = []
            all_categories = []
            
            for category_name, category_data in categories.items():
                # Handle both old format (direct list) and new format (object with steps)
                steps = []
                if isinstance(category_data, list):
                    # Old format: direct list of steps
                    steps = category_data
                elif isinstance(category_data, dict):
                    # New format: object with 'steps' property
                    steps = category_data.get('steps', [])
                else:
                    logger.warning(f"Unexpected category data format for {sheet_name}.{category_name}: {type(category_data)}")
                    continue
                
                # Only process if we have valid steps
                if steps and isinstance(steps, list) and len(steps) > 0:
                    all_categories.append(category_name)
                    # Add category as header
                    all_steps.append(f"<{category_name}>")
                    # Add steps with indentation
                    for step in steps:
                        if step and step.strip():  # Ensure step is not empty
                            all_steps.append(f"     - {step}")
                else:
                    logger.info(f"No valid steps found for category '{category_name}' in sheet '{sheet_name}'")
            
            if not all_steps:
                logger.warning(f"Skipping sheet '{sheet_name}' - no valid steps found ({process_type})")
                continue
            
            # Get additional metadata from the first category (if available)
            first_category_data = next(iter(categories.values()))
            related_pages = []
            image_references = []
            
            if isinstance(first_category_data, dict):
                related_pages = first_category_data.get('related_pages', [])
                image_references = first_category_data.get('image_references', [])
            
            # Create single process object for entire sheet
            process = {
                'process_id': f"{sanitize_filename(sheet_name)}_complete_{process_type}",
                'process_name': f"{sheet_name} - Complete Process ({process_type.title()})",
                'process_category': f'xlsx_sheet_process_{process_type}',
                'process_type': process_type,
                'client_name': client_name,
                'document_status': 'draft',
                'content_hash' : content_hash,
                'is_duplicate' : str(is_duplicate),
                'provider_name': provider_name,
                'timestamp_text_extraction': timestamp_text_extraction,
                'timestamp_text_standardization': timestamp_text_standardization,
                'timestamp_semantic_chunking': timestamp_semantic_chunking,
                'timestamp_identify_processes': timestamp_identify_processes,
                'timestamp_create_process_docs': timestamp_create_process_docs,
                'steps': all_steps,
                'related_chunks': related_pages,  # Use related_pages as related_chunks
                'related_pages': related_pages,
                'image_references': image_references,
                'description': f"Complete {process_type} process for {sheet_name} sheet with categories: {', '.join(all_categories)}",
                'section_location': f"Sheet: {sheet_name}",
                'sheet_name': sheet_name,
                'categories': all_categories
            }
            
            try:
                json_file_info = create_xlsx_process_json_file(
                    process,
                    semantic_chunks,
                    file_type,
                    original_filename,
                    source_bucket,
                    source_key,
                    target_bucket,
                    client_name,
                    content_hash,
                    is_duplicate,
                    provider_name,
                    timestamp_text_extraction,
                    timestamp_text_standardization,
                    timestamp_semantic_chunking,
                    timestamp_identify_processes,
                    timestamp_create_process_docs,
                    process_type
                )
                created_files.append(json_file_info)
                logger.info(f"Successfully created single JSON file for sheet: {sheet_name} ({process_type})")

                # Only insert process record for non-distinct documents. 
                # distinct documents will be inserted after LLM tagging
                if (process_type != 'distinct'):
                    records_inserted = insert_process_record(original_filename, client_name, source_bucket, source_key, is_duplicate, process)


                
            except Exception as inner_e:
                logger.error(f"Failed to create JSON file for sheet {sheet_name} ({process_type}): {str(inner_e)}")
                continue
        
    except Exception as e:
        logger.error(f"Error processing XLSX sheets ({process_type}): {str(e)}")
        raise
    
    return created_files

def process_standard_documents(distinct_processes, semantic_chunks, file_type, original_filename, 
                source_bucket, source_key, target_bucket,client_name,content_hash,is_duplicate,provider_name,timestamp_text_extraction,
                timestamp_text_standardization,
                timestamp_semantic_chunking,
                timestamp_identify_processes,
                timestamp_create_process_docs,
                process_type="distinct"):
    """Process standard documents with processes structure"""
    logger.info(f"Processing standard document structure ({process_type} processes)")
    created_files = []
    
    processes_list = distinct_processes.get('processes', [])
    total_processes_to_create = len(processes_list)
    logger.info(f"Starting to create JSON files for {total_processes_to_create} {process_type} processes.")

    # Create separate JSON file for each process
    for i, process in enumerate(processes_list):
        process_name = process.get('process_name', 'Unnamed Process')
        logger.info(f"Processing {process_type} process {i+1}/{total_processes_to_create}: '{process_name}'")
        
        # Add process type to the process data
        process['process_type'] = process_type
        
        try:
            json_file_info = create_process_json_file(
                process, 
                semantic_chunks,
                file_type,
                original_filename,
                source_bucket,
                source_key,
                target_bucket,
                client_name,
                content_hash,
                is_duplicate,
                provider_name,
                timestamp_text_extraction,
                timestamp_text_standardization,
                timestamp_semantic_chunking,
                timestamp_identify_processes,
                timestamp_create_process_docs,
                process_type
            )
            created_files.append(json_file_info)
            logger.info(f"Successfully created JSON file for {process_type} process '{process_name}'. S3 Key: {json_file_info.get('s3_key')}")

            # Only insert process record for non-distinct documents. 
            # distinct documents will be inserted after LLM tagging
            if (process_type != 'distinct'):
                records_inserted = insert_process_record(original_filename, client_name, source_bucket, source_key, is_duplicate, process)

        except Exception as inner_e:
            logger.error(f"Failed to create JSON file for {process_type} process '{process_name}': {str(inner_e)}")
            continue

    return created_files

def create_xlsx_process_json_file(process, semantic_chunks, file_type, original_filename, 
                source_bucket, source_key, target_bucket,client_name,content_hash,is_duplicate,provider_name,timestamp_text_extraction,
                timestamp_text_standardization,
                timestamp_semantic_chunking,
                timestamp_identify_processes,
                timestamp_create_process_docs,
                process_type="distinct"):
    """Create individual JSON file for each XLSX process category"""
    process_name = process.get('process_name', 'Unnamed Process')
    sheet_name = process.get('sheet_name', 'Unknown Sheet')
    category_name = process.get('category_name', 'Unknown Category')
    
    logger.debug(f"Starting creation of XLSX JSON file for {process_type} process: '{process_name}'")
    
    try:
        # Generate unique process ID
        process_uuid = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Get related chunks content (for XLSX, we typically use all chunks)
        related_chunks_content = []
        for chunk in semantic_chunks:
            if chunk.get('content'):
                related_chunks_content.append({
                    'chunk_id': chunk.get('chunk_id', 1),
                    'content': chunk['content'],
                    'semantic_type': chunk.get('semantic_type', 'xlsx_content'),
                    'summary': chunk.get('summary', '')
                })
        
        logger.info(f"Found {len(related_chunks_content)} chunks for XLSX {process_type} process '{process_name}'")
        
        # Create comprehensive XLSX process JSON
        process_json = {
            'metadata': {
                'process_uuid': process_uuid,
                'process_id': process.get('process_id', f'xlsx_{process_type}_{process_uuid[:8]}'),
                'process_name': process_name,
                'process_type': process_type,
                'created_timestamp': timestamp,
                'client_name': client_name,
                'document_status': 'draft',
                'content_hash' : content_hash,
                'is_duplicate' : str(is_duplicate),
                'provider_name':provider_name,
                'timestamp_text_extraction' : timestamp_text_extraction,
                'timestamp_text_standardization' : timestamp_text_standardization,
                'timestamp_semantic_chunking' : timestamp_semantic_chunking,
                'timestamp_identify_processes' : timestamp_identify_processes,
                'timestamp_create_process_docs' : timestamp_create_process_docs,
                'source_file': {
                    'original_filename': original_filename,
                    'file_type': file_type,
                    's3_bucket': source_bucket,
                    's3_key': source_key
                },
                'processing_info': {
                    'extraction_method': f'xlsx_automated_{process_type}',
                    'chunking_method': 'xlsx_semantic',
                    'identification_method': f'bedrock_claude_xlsx_{process_type}'
                },
                'xlsx_specific': {
                    'sheet_name': sheet_name,
                    'category_name': category_name,
                    'provider': sheet_name
                }
            },
            'process_details': {
                'name': process_name,
                'description': process.get('description', ''),
                'category': process.get('process_category', f'xlsx_process_{process_type}'),
                'process_type': process_type,
                'steps': process.get('steps', []),
                'client_name':client_name,
                'content_hash' : content_hash,
                'is_duplicate' : str(is_duplicate),
                'provider_name':provider_name,
                'timestamp_text_extraction' : timestamp_text_extraction,
                'timestamp_text_standardization' : timestamp_text_standardization,
                'timestamp_semantic_chunking' : timestamp_semantic_chunking,
                'timestamp_identify_processes' : timestamp_identify_processes,
                'timestamp_create_process_docs' : timestamp_create_process_docs,
                'location_info': {
                    'section_location': process.get('section_location', ''),
                    'sheet_name': sheet_name,
                    'category_name': category_name,
                    'organization_pattern': 'xlsx_hierarchical'
                }
            },
            'content': {
                'related_chunks': related_chunks_content,
                'total_chunks': len(related_chunks_content),
                'step_details': process.get('steps', []),
                'full_content': '\n\n'.join([chunk['content'] for chunk in related_chunks_content])
            },
            'analytics': {
                'word_count': sum(len(step.split()) for step in process.get('steps', [])),
                'character_count': sum(len(step) for step in process.get('steps', [])),
                'step_count': len(process.get('steps', [])),
                'complexity_score': calculate_xlsx_complexity_score(process)
            }
        }
        
        # Generate S3 key for the XLSX JSON file
        safe_sheet_name = sanitize_filename(sheet_name)
        safe_category_name = sanitize_filename(category_name)
        #json_filename = f"processes/xlsx/{client_name}/{datetime.now().strftime('%Y/%m/%d')}/{safe_sheet_name}_{safe_category_name}_{process_uuid[:8]}.json"
        # Generate S3 key for the XLSX JSON file based on process type
        if process_type == "distinct":
            json_filename = f"processes/{client_name}/xlsx/{datetime.now().strftime('%Y/%m/%d')}/{safe_sheet_name}_{safe_category_name}_{process_uuid[:8]}.json"
        else:  # non_distinct
            json_filename = f"non_distinct_processes/{client_name}/xlsx/{datetime.now().strftime('%Y/%m/%d')}/{safe_sheet_name}_{safe_category_name}_{process_uuid[:8]}.json"

        
        logger.info(f"Generated S3 key for XLSX {process_type} process '{process_name}': {json_filename}")
        
        json_body = json.dumps(process_json, indent=2, ensure_ascii=False)
        file_size_bytes = len(json_body.encode('utf-8'))
        
        # Upload to S3
        s3_client.put_object(
            Bucket=target_bucket,
            Key=json_filename,
            Body=json_body,
            ContentType='application/json',
            Metadata={
                'process-id': process.get('process_id', ''),
                'process-name': process_name,
                'process-type': process_type,
                'sheet-name': sheet_name,
                'client_name':client_name,
                'content_hash' : content_hash,
                'is_duplicate' : str(is_duplicate),
                'provider_name':provider_name,
                'category-name': category_name,
                'source-file': original_filename,
                'file-type': file_type,
                'provider': sheet_name
            }
        )
        logger.info(f"Successfully uploaded XLSX {process_type} process JSON file to s3://{target_bucket}/{json_filename}")
        

        return {
            'process_id': process.get('process_id'),
            'process_name': process_name,
            'process_uuid': process_uuid,
            'process_type': process_type,
            'client_name':client_name,
            'document_status': 'draft',
            'content_hash' : content_hash,
            'is_duplicate' : str(is_duplicate),
            'provider_name':provider_name,
            'sheet_name': sheet_name,
            'category_name': category_name,
            's3_bucket': target_bucket,
            's3_key': json_filename,
            'file_size_bytes': file_size_bytes,
            'chunk_count': len(related_chunks_content),
            'step_count': len(process.get('steps', []))
        }
        
    except Exception as e:
        logger.exception(f"Error creating XLSX JSON file for {process_type} process '{process_name}': {str(e)}")
        raise

def create_xlsx_summary_file(distinct_processes, semantic_chunks, file_type, 
    original_filename, source_bucket, source_key, 
    target_bucket,client_name,content_hash,is_duplicate,provider_name):
    """Create a summary file for the entire XLSX document"""
    logger.info("Creating XLSX summary file")
    
    try:
        summary_uuid = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        sheets = distinct_processes.get('sheets', {})
        total_categories = sum(len(categories) for categories in sheets.values())
        total_steps = sum(
            len(steps) for categories in sheets.values() 
            for steps in categories.values() 
            if isinstance(steps, list)
        )
        
        # Create summary structure
        summary_json = {
            'metadata': {
                'summary_uuid': summary_uuid,
                'document_type': 'xlsx_process_manual_summary',
                'created_timestamp': timestamp,
                'client_name':client_name,
                'document_status': 'draft',
                'content_hash' : content_hash,
                'is_duplicate' : str(is_duplicate),
                'provider_name':provider_name,
                'source_file': {
                    'original_filename': original_filename,
                    'file_type': file_type,
                    's3_bucket': source_bucket,
                    's3_key': source_key
                }
            },
            'summary': {
                'total_sheets': len(sheets),
                'total_categories': total_categories,
                'total_steps': total_steps,
                'providers': list(sheets.keys())
            },
            'sheets_overview': {},
            'complete_structure': sheets
        }
        
        # Add overview for each sheet
        for sheet_name, categories in sheets.items():
            summary_json['sheets_overview'][sheet_name] = {
                'total_categories': len(categories),
                'categories': list(categories.keys()),
                'total_steps': sum(len(steps) for steps in categories.values() if isinstance(steps, list))
            }
        
        # Generate S3 key for summary
        safe_filename = sanitize_filename(original_filename.split('.')[0] if original_filename else 'xlsx_summary')
        summary_filename = f"summaries/xlsx/{datetime.now().strftime('%Y/%m/%d')}/{safe_filename}_summary_{summary_uuid[:8]}.json"
        
        json_body = json.dumps(summary_json, indent=2, ensure_ascii=False)
        file_size_bytes = len(json_body.encode('utf-8'))
        
        # Upload to S3
        s3_client.put_object(
            Bucket=target_bucket,
            Key=summary_filename,
            Body=json_body,
            ContentType='application/json',
            Metadata={
                'document-type': 'xlsx_summary',
                'source-file': original_filename,
                'client_name':client_name,
                'document_status': 'draft',
                'content_hash' : content_hash,
                'is_duplicate' : str(is_duplicate),
                'provider_name':provider_name,
                'file-type': file_type,
                'total-sheets': str(len(sheets)),
                'total-categories': str(total_categories)
            }
        )
        
        logger.info(f"Successfully uploaded XLSX summary file to s3://{target_bucket}/{summary_filename}")
        
        return {
            'process_id': f'summary_{summary_uuid[:8]}',
            'process_name': f'XLSX Summary - {original_filename}',
            'process_uuid': summary_uuid,
            'document_type': 'xlsx_summary',
            'client_name':client_name,
            'document_status': 'draft',
            'content_hash' : content_hash,
            'is_duplicate' : str(is_duplicate),
            'provider_name':provider_name,
            's3_bucket': target_bucket,
            's3_key': summary_filename,
            'file_size_bytes': file_size_bytes,
            'total_sheets': len(sheets),
            'total_categories': total_categories,
            'total_steps': total_steps
        }
        
    except Exception as e:
        logger.exception(f"Error creating XLSX summary file: {str(e)}")
        raise

def sanitize_header_value(value):
    """Sanitize string to be safe for HTTP headers by removing newlines and control characters"""
    if not isinstance(value, str):
        value = str(value)
    # Replace newlines and other control characters with spaces
    sanitized = re.sub(r'[\r\n\t\x00-\x1f\x7f-\x9f]', ' ', value)
    # Replace multiple spaces with single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    # Trim and limit length for header values
    return sanitized.strip()[:100]  # AWS metadata values have limits

def create_process_json_file(process, semantic_chunks, file_type, original_filename, source_bucket, 
        source_key, target_bucket, client_name,content_hash,is_duplicate,provider_name,timestamp_text_extraction,
                timestamp_text_standardization,
                timestamp_semantic_chunking,
                timestamp_identify_processes,
                timestamp_create_process_docs,
                process_type="distinct"):
    """Create individual JSON file for each process and upload to S3"""
    process_name = process.get('process_name', 'Unnamed Process')
    logger.debug(f"Starting creation of JSON file for {process_type} process: '{process_name}'")
    try:
        # Generate unique process ID
        process_uuid = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        logger.debug(f"Generated process_uuid: {process_uuid}, timestamp: {timestamp}")
        
        # Get related chunks content
        related_chunks_content = []
        related_chunk_ids = process.get('related_chunks', [])
        related_pages = process.get('related_pages', [])
        image_references = []
        mermaid_syntax = None
        pages = process.get('pages', {})
        if pages:
            # Extract from nested pages structure
            for page_num, page_data in pages.items():
                if isinstance(page_data, dict) and 'image_references' in page_data:
                    image_references.extend(page_data['image_references'])
        else:
            # Fallback to direct image_references if pages structure doesn't exist
            image_references = process.get('image_references', [])
        if process_type == "distinct":
            mermaid_syntax = process.get('mermaid_syntax')
        else:
            mermaid_syntax
        description = process.get('description')
        logger.debug(f"Looking for {len(related_chunk_ids)} related chunk IDs for {process_type} process '{process_name}'.")
        logger.info(f"Found {len(image_references)} image references for {process_type} process '{process_name}': {image_references}")
        logger.info(f"Found mermaid syntax for {process_type} process '{process_name}': {bool(mermaid_syntax)}")
        
        for chunk in semantic_chunks:
            if chunk.get('chunk_id') in related_chunk_ids:
                related_chunks_content.append({
                    'chunk_id': chunk['chunk_id'],
                    'content': chunk['content'],
                    'semantic_type': chunk.get('semantic_type', 'general'),
                    'summary': chunk.get('summary', '')
                })
        logger.info(f"Found {len(related_chunks_content)} matching semantic chunks for {process_type} process '{process_name}'.")
        
        # Create comprehensive process JSON
        process_json = {
            'metadata': {
                'process_uuid': process_uuid,
                'process_id': process.get('process_id', f'proc_{process_type}_{process_uuid[:8]}'),
                'process_name': process_name,
                'process_type': process_type,
                'created_timestamp': timestamp,
                'client_name': client_name,
                'document_status': 'draft',
                'content_hash' : content_hash,
                'is_duplicate' : str(is_duplicate),
                'provider_name':provider_name,
                'timestamp_text_extraction':timestamp_text_extraction,
                'timestamp_text_standardization': timestamp_text_standardization,
                'timestamp_semantic_chunking': timestamp_semantic_chunking,
                'timestamp_identify_processes': timestamp_identify_processes,
                'timestamp_create_process_docs': timestamp_create_process_docs,
                'source_file': {
                    'original_filename': original_filename,
                    'file_type': file_type,
                    's3_bucket': source_bucket,
                    's3_key': source_key
                },
                'processing_info': {
                    'extraction_method': f'automated_{process_type}',
                    'chunking_method': 'semantic',
                    'identification_method': f'bedrock_claude_{process_type}'
                }
            },
            'process_details': {
                'name': process_name,
                'description': process.get('description', ''),
                'category': process.get('process_category', process.get('process_type', f'general_{process_type}')),
                'process_type': process_type,
                'steps': process.get('steps', []),
                'client_name': client_name,
                'document_status': 'draft',
                'content_hash' : content_hash,
                'is_duplicate' : str(is_duplicate),
                'provider_name':provider_name,
                'timestamp_text_extraction':timestamp_text_extraction,
                'timestamp_text_standardization': timestamp_text_standardization,
                'timestamp_semantic_chunking': timestamp_semantic_chunking,
                'timestamp_identify_processes': timestamp_identify_processes,
                'timestamp_create_process_docs': timestamp_create_process_docs,
                'location_info': {
                    'section_location': process.get('section_location', ''),
                    'location': process.get('location', ''),
                    'organization_pattern': process.get('organization_pattern', 'sequential')
                },
                'related_pages': related_pages,
                'image_references': image_references,
                'mermaid_syntax': process.get('mermaid_syntax')
            },
            'content': {
                'related_chunks': related_chunks_content,
                'total_chunks': len(related_chunks_content),
                'full_content': '\n\n'.join([chunk['content'] for chunk in related_chunks_content])
            },
            'analytics': {
                'word_count': sum(len(chunk['content'].split()) for chunk in related_chunks_content),
                'character_count': sum(len(chunk['content']) for chunk in related_chunks_content),
                'step_count': len(process.get('steps', [])),
                'complexity_score': calculate_complexity_score(process, related_chunks_content),
                'image_count': len(image_references),
                'has_mermaid_syntax': bool(mermaid_syntax)
            }
        }
        logger.debug(f"Constructed process JSON for {process_type} process '{process_name}' with {len(image_references)} image references.")
        
        # Generate S3 key for the JSON file
        safe_process_name = sanitize_filename(process_name)
        #json_filename = f"processes/{client_name}/{datetime.now().strftime('%Y/%m/%d')}/{safe_process_name}_{process_uuid[:8]}.json"
        if process_type == "distinct":
            json_filename = f"processes/{client_name}/{datetime.now().strftime('%Y/%m/%d')}/{safe_process_name}_{process_uuid[:8]}.json"
        else:  # non_distinct
            json_filename = f"non_distinct_processes/{client_name}/{datetime.now().strftime('%Y/%m/%d')}/{safe_process_name}_{process_uuid[:8]}.json"
        logger.info(f"Generated S3 key for {process_type} process '{process_name}': {json_filename}")
        
        json_body = json.dumps(process_json, indent=2, ensure_ascii=False)
        file_size_bytes = len(json_body.encode('utf-8'))
        logger.debug(f"JSON body size for {process_type} process '{process_name}': {file_size_bytes} bytes.")
        
        # Prepare metadata with sanitized values
        metadata = {
            'process-id': process.get('process_id', ''),
            'process-name': sanitize_header_value(process_name),
            'process-type': process_type,
            'source-file': sanitize_header_value(original_filename),
            'file-type': file_type,
            'client_name': client_name,
            'document_status': 'draft',
            'content_hash' : content_hash,
            'is_duplicate' : str(is_duplicate),
            'provider_name':provider_name,
            'image-count': str(len(image_references)),
            'has-mermaid': str(bool(mermaid_syntax))
        }
        
        # Upload to S3
        s3_client.put_object(
            Bucket=target_bucket,
            Key=json_filename,
            Body=json_body,
            ContentType='application/json',
            Metadata=metadata
        )
        logger.info(f"Successfully uploaded {process_type} process JSON file to s3://{target_bucket}/{json_filename}")
        
        return {
            'process_id': process.get('process_id'),
            'process_name': process_name,
            'process_uuid': process_uuid,
            'process_type': process_type,
            's3_bucket': target_bucket,
            's3_key': json_filename,
            'client_name': client_name,
            'document_status': 'draft',
            'content_hash' : content_hash,
            'is_duplicate' : str(is_duplicate),
            'provider_name':provider_name,
            'file_size_bytes': file_size_bytes,
            'chunk_count': len(related_chunks_content),
            'image_count': len(image_references),
            'has_mermaid_syntax': bool(mermaid_syntax),
            'timestamp_text_extraction':timestamp_text_extraction,
            'timestamp_text_standardization': timestamp_text_standardization,
            'timestamp_semantic_chunking': timestamp_semantic_chunking,
            'timestamp_identify_processes': timestamp_identify_processes,
            'timestamp_create_process_docs': timestamp_create_process_docs,
        }
        
    except Exception as e:
        logger.exception(f"Error creating JSON file for {process_type} process '{process_name}': {str(e)}")
        raise

def calculate_xlsx_complexity_score(process):
    """Calculate complexity score specifically for XLSX processes"""
    try:
        steps = process.get('steps', [])
        step_count = len(steps)
        
        # Calculate based on step count and content complexity
        total_words = sum(len(step.split()) for step in steps)
        avg_words_per_step = total_words / step_count if step_count > 0 else 0
        
        # Simple complexity calculation for XLSX
        complexity = (step_count * 0.4) + (avg_words_per_step * 0.1) + (total_words / 50 * 0.5)
        
        return round(min(complexity, 10), 2)  # Cap at 10
        
    except Exception as e:
        logger.error(f"Error calculating XLSX complexity score: {str(e)}")
        return 1.0

def calculate_complexity_score(process, chunks):
    """Calculate a simple complexity score for the process"""
    process_name = process.get('process_name', 'Unnamed Process')
    process_type = process.get('process_type', 'unknown')
    logger.debug(f"Calculating complexity score for {process_type} process: '{process_name}'")
    try:
        step_count = len(process.get('steps', []))
        chunk_count = len(chunks)
        total_words = sum(len(chunk.get('content', '').split()) for chunk in chunks)
        
        logger.debug(f"Complexity inputs for {process_type} process '{process_name}': steps={step_count}, chunks={chunk_count}, words={total_words}")
        
        # Simple complexity calculation
        complexity = (step_count * 0.3) + (chunk_count * 0.2) + (total_words / 100 * 0.5)
        
        final_complexity = round(min(complexity, 10), 2)  # Cap at 10
        logger.debug(f"Calculated complexity score for {process_type} process '{process_name}': {final_complexity}")
        return final_complexity
        
    except Exception as e:
        logger.error(f"Error calculating complexity score for {process_type} process '{process_name}': {str(e)}. Returning default score 1.0.")
        return 1.0

def sanitize_filename(filename):
    """Sanitize filename for S3 key"""
    logger.debug(f"Sanitizing filename: '{filename}'")
    # Remove or replace invalid characters
    sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Trim and lowercase
    final_sanitized = sanitized.strip('_').lower()[:50]  # Limit length
    logger.debug(f"Sanitized filename result: '{final_sanitized}'")
    return final_sanitized

def insert_process_record(original_filename, client_name, source_bucket, source_key, is_duplicate,process: dict):
    """
        Connects to PostgreSQL and inserts a record into the 'processes' table using RDS Data API

        Environment variables required:
            - PGDATABASE
            - DB_SECRET_NAME
            - DB_CLUSTER_ARN
    """

    logger.info(f"Inserting process record......, received process info: {is_duplicate}")
    dbname = os.environ["PGDATABASE"]
    secret = os.environ["DB_SECRET_NAME"]
    cluster = os.environ["DB_CLUSTER_ARN"]

    try:
        flags_value = {}        
        if str(is_duplicate).lower() == "true":
            flags_value["conflict"] = True

        sql = """
        INSERT INTO processes ( client_id, process_url, source_sop_url, title, domain, document_type, s3_key, flags) 
        VALUES ( :client_id, :process_url, :source_sop_url, :title, :domain, :document_type, :s3_key, :flags::jsonb)
        """

        logger.info(f"SQL statement: {sql}")

        parameters = [
            {"name": "client_id", "value": {"stringValue": client_name}},
            {"name": "process_url", "value": {"stringValue": source_bucket + "/" + source_key }},
            {"name": "source_sop_url", "value": {"stringValue": original_filename}},
            {"name": "title", "value": {"stringValue": process["process_name"]}},
            {"name": "domain", "value": {"stringValue": process["process_category"]}},
            {"name": "document_type", "value": {"stringValue": "document"}},
            {"name": "s3_key", "value": {"stringValue": source_bucket + "/" + source_key}},
            {"name": "flags","value": {"stringValue": json.dumps(flags_value)}}
        ]

        logger.info(f"Parameters: {parameters}")

        logger.info("Executing SQL via RDS Data API...")
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
            logger.info(f"Inserted {rows_inserted} process row(s) for client: {client_name}")
        else:
            logger.warning("No rows inserted into DB.")
        return rows_inserted

    except Exception as e:
        logger.exception(f"Failed to insert process record into DB. Parameters:\n{json.dumps(parameters, indent=2)}")
        return 0