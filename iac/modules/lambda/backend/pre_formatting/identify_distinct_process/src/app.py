import json
import boto3
import re
import logging
from datetime import datetime
import uuid
import os

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

bedrock_client = boto3.client('bedrock-runtime')
s3_client = boto3.client('s3')

# Cache for prompt templates to avoid repeated S3 calls
PROMPT_CACHE = {}
DISTINCT_PROCESS_BUCKET = os.environ.get('DISTINCT_PROCESS_BUCKET', 'default-extracted-text-bucket')

def load_prompt_template_from_s3(bucket_name, template_key):
    """Load prompt template from S3 with caching."""
    cache_key = f"{bucket_name}/{template_key}"
    if cache_key in PROMPT_CACHE:
        logger.info(f"Using cached prompt template: {cache_key}")
        return PROMPT_CACHE[cache_key]
    
    try:
        logger.info(f"Loading prompt template from S3: s3://{bucket_name}/{template_key}")
        response = s3_client.get_object(Bucket=bucket_name, Key=template_key)
        template = response['Body'].read().decode('utf-8')
        if not template.strip():
            raise ValueError(f"Empty template found in {template_key}")
        
        PROMPT_CACHE[cache_key] = template
        logger.info(f"Successfully loaded and cached prompt template: {template_key}")
        return template
    except Exception as e:
        logger.error(f"Failed to load prompt template from S3: {str(e)}")
        raise Exception(f"Failed to load prompt template: {str(e)}")

def get_prompt_template_key(file_type):
    """Get the S3 key for the prompt template based on file type (only for distinct processes)."""
    template_mapping = {
        'pdf': 'prompts/pdf_process_prompts.txt',
        'docx': 'prompts/docx_process_prompts.txt',
        'pptx': 'prompts/pptx_process_prompts.txt',
        'xlsx': 'prompts/xlsx_process_prompts.txt'
    }
    return template_mapping.get(file_type.lower())

def generate_mermaid_flowchart(process_name, steps):
    """Generate Mermaid flowchart syntax from process steps."""
    try:
        clean_process_name = re.sub(r'[^\w\s]', '', process_name).replace(' ', '_')
        
        mermaid_lines = [
            "flowchart TD",
            f"    Start([Start: {process_name}])"
        ]
        
        previous_node = "Start"
        step_nodes = []
        
        for i, step in enumerate(steps):
            step_text = step.strip()
            
            step_match = re.match(r'^(\d+(?:\.\d+)?)\s*[.:]?\s*(.+)', step_text)
            if step_match:
                step_num = step_match.group(1)
                step_content = step_match.group(2)
            else:
                step_num = str(i + 1)
                step_content = step_text
            
            if len(step_content) > 80:
                step_content = step_content[:77] + "..."
            
            step_content = re.sub(r'["\n\r]', ' ', step_content)
            step_content = re.sub(r'\s+', ' ', step_content).strip()
            
            node_id = f"Step{step_num.replace('.', '_')}"
            step_nodes.append(node_id)
            
            mermaid_lines.append(f'    {node_id}["{step_num}: {step_content}"]')
            mermaid_lines.append(f"    {previous_node} --> {node_id}")
            
            previous_node = node_id
        
        mermaid_lines.append('    End([Process Complete])')
        mermaid_lines.append(f"    {previous_node} --> End")
        
        mermaid_lines.extend([
            "",
            "    classDef startEnd fill:#e1f5fe,stroke:#01579b,stroke-width:2px",
            "    classDef processStep fill:#f3e5f5,stroke:#4a148c,stroke-width:2px",
            "    class Start,End startEnd"
        ])
        
        if step_nodes:
            step_node_list = ",".join(step_nodes)
            mermaid_lines.append(f"    class {step_node_list} processStep")
        
        return "\n".join(mermaid_lines)
        
    except Exception as e:
        logger.error(f"Error generating Mermaid flowchart: {str(e)}")
        return f"""flowchart TD
    Start([Start: {process_name}])
    Process["{len(steps)} steps in this process"]
    End([Process Complete])
    Start --> Process
    Process --> End
    
    classDef startEnd fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef processStep fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    class Start,End startEnd
    class Process processStep"""

def add_mermaid_to_processes(processes_data):
    """Add Mermaid flowchart syntax to each process in the data structure."""
    try:
        if 'processes' in processes_data:
            for process in processes_data['processes']:
                process_name = process.get('process_name', 'Unknown Process')
                steps = process.get('steps', [])
                
                mermaid_syntax = generate_mermaid_flowchart(process_name, steps)
                process['mermaid_syntax'] = mermaid_syntax
                
                logger.info(f"Generated Mermaid flowchart for process: {process_name}")
        
        elif 'sheets' in processes_data:
            for sheet_name, categories in processes_data['sheets'].items():
                for category_name, category_data in categories.items():
                    if isinstance(category_data, dict) and 'steps' in category_data:
                        process_name = f"{sheet_name} - {category_name}"
                        steps = category_data.get('steps', [])
                        
                        mermaid_syntax = generate_mermaid_flowchart(process_name, steps)
                        category_data['mermaid_syntax'] = mermaid_syntax
                        
                        logger.info(f"Generated Mermaid flowchart for XLSX process: {process_name}")
        
        return processes_data
        
    except Exception as e:
        logger.error(f"Error adding Mermaid to processes: {str(e)}")
        return processes_data

def create_prompt(file_type, text, extracted_text_by_page, chunks_data, event):
    """Generates the appropriate LLM prompt using S3-stored templates (only for distinct processes)."""
    page_context = create_page_context(extracted_text_by_page)
    prompt_bucket = event.get('prompt_bucket', 'intouchx-prompts')
    
    template_key = get_prompt_template_key(file_type)
    if not template_key:
        raise ValueError(f"No prompt template found for file type: {file_type}")
    
    prompt_template = load_prompt_template_from_s3(prompt_bucket, template_key)
    
    if file_type.lower() == 'xlsx':
        formatted_prompt = prompt_template.format(
            text=text,
            page_context=page_context
        )
    else:
        chunk_ids = ",".join(map(str, [c['chunk_id'] for c in chunks_data]))
        formatted_prompt = prompt_template.format(
            text=text,
            page_context=page_context,
            chunk_ids=chunk_ids
        )
    
    logger.info(f"Created distinct prompt using template: s3://{prompt_bucket}/{template_key}")
    return formatted_prompt

def get_processes_input(event):
    """Retrieves semantic chunks from the event payload or S3."""
    if 'semantic_chunks' in event:
        logger.info("Using semantic_chunks from event payload.")
        return event['semantic_chunks']
    elif 'chunks_s3_bucket' in event and 'chunks_s3_key' in event:
        chunks_s3_bucket = event['chunks_s3_bucket']
        chunks_s3_key = event['chunks_s3_key']
        logger.info(f"Reading semantic chunks from S3: s3://{chunks_s3_bucket}/{chunks_s3_key}")
        try:
            response = s3_client.get_object(Bucket=chunks_s3_bucket, Key=chunks_s3_key)
            chunks_data = json.loads(response['Body'].read().decode('utf-8'))
            return chunks_data.get('chunks', chunks_data)
        except Exception as s3_error:
            raise Exception(f"Failed to read semantic chunks from S3: {str(s3_error)}")
    else:
        raise KeyError("'semantic_chunks' or ('chunks_s3_bucket' and 'chunks_s3_key')")

#old-code logic
"""
def call_bedrock_and_parse(prompt, file_type):
    #Invokes the Bedrock model and parses the response for distinct processes.
    try:
        model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        bedrock_payload = json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 4000,
            'messages': [{'role': 'user', 'content': prompt}]
        })
        
        logger.info(f"Calling Bedrock model: {model_id} for distinct processes")
        response = bedrock_client.invoke_model(modelId=model_id, body=bedrock_payload)
        response_body = json.loads(response['body'].read())
        process_result = response_body['content'][0]['text']
        logger.info("Successfully received distinct response from Bedrock")
        
        json_match = re.search(r'\{.*\}', process_result, re.DOTALL)
        if json_match:
            parsed_response = json.loads(json_match.group())
            if 'sheets' in parsed_response and file_type == 'xlsx':
                return convert_xlsx_to_standard_format(parsed_response)
            return parsed_response
        else:
            logger.warning("No JSON found in Bedrock distinct response. Returning empty result.")
            return {'processes': [], 'total_processes_found': 0, 'document_type': 'no_json_response_distinct'}
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse Bedrock distinct JSON response: {str(e)}. Returning empty result.")
        return {'processes': [], 'total_processes_found': 0, 'document_type': 'json_decode_error_distinct'}
    except Exception as e:
        logger.exception(f"Error calling Bedrock for distinct processes: {str(e)}. Returning empty result.")
        return {'processes': [], 'total_processes_found': 0, 'document_type': 'bedrock_error_distinct'}
"""

def call_bedrock_and_parse(prompt, file_type):
    """Invokes the Bedrock model and parses the response for distinct processes."""
    try:
        print(f" DEBUG: Starting call_bedrock_and_parse for file_type: {file_type}")
        logger.info(f"Starting call_bedrock_and_parse for file_type: {file_type}")
        model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        bedrock_payload = json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 4000,
            'messages': [{'role': 'user', 'content': prompt}]
        })
        
        logger.info(f"Calling Bedrock model: {model_id} for distinct processes")
        response = bedrock_client.invoke_model(modelId=model_id, body=bedrock_payload)
        response_body = json.loads(response['body'].read())
        process_result = response_body['content'][0]['text']
        logger.info("Successfully received distinct response from Bedrock")
        
        # More robust JSON extraction
        # First, try to find complete JSON object
        json_match = re.search(r'\{.*\}', process_result, re.DOTALL)
        
        if json_match:
            print(f"✅ DEBUG: Found complete JSON match for {file_type}")
            logger.info(f"✅ DEBUG: Using SIMPLE JSON extraction for {file_type}")
            json_text = json_match.group()
        else:
            # If no complete JSON found, try to reconstruct it
            print(f"⚠️ DEBUG: No complete JSON found for {file_type}, attempting reconstruction...")
            logger.warning("No complete JSON found, attempting to reconstruct...")
            
            # Look for content that starts with a JSON property
            partial_match = re.search(r'"providers".*', process_result, re.DOTALL)
            if partial_match:
                print(f"🔧 DEBUG: Using COMPLEX reconstruction logic for {file_type}")
                logger.info(f"🔧 DEBUG: Using COMPLEX reconstruction logic for {file_type}")
                # Add missing opening brace
                json_text = '{' + partial_match.group()
                print(f"🔧 DEBUG: Added missing closing brace for {file_type}")
                # Ensure it ends with closing brace if missing
                if not json_text.rstrip().endswith('}'):
                    json_text += '}'
                    print(f"🔧 DEBUG: Added missing closing brace for {file_type}")

            else:
                print(f"❌ DEBUG: No recognizable JSON structure found for {file_type}")
                logger.error(f"❌ DEBUG: No recognizable JSON structure found for {file_type}")
                logger.error("No recognizable JSON structure found in response")
                return {'processes': [], 'total_processes_found': 0, 'document_type': 'no_json_found'}
        
        # Clean up the JSON text
        json_text = json_text.strip()
        
        print(f"🔍 DEBUG: Final JSON length for {file_type}: {len(json_text)} characters")
        print(f"🔍 DEBUG: First 200 chars of JSON for {file_type}: {json_text[:200]}...")
        # Log the JSON text for debugging
        logger.info(f"Attempting to parse JSON: {json_text[:200]}...")
        
        try:
            parsed_response = json.loads(json_text)
            print(f"✅ DEBUG: Successfully parsed JSON for {file_type}")

            # Check for related_pages in the response
            if 'processes' in parsed_response:
                for i, process in enumerate(parsed_response['processes']):
                    related_pages = process.get('related_pages', [])
                    print(f"🔍 DEBUG: Process {i+1} for {file_type} has related_pages: {related_pages}")
            
            if 'sheets' in parsed_response and file_type == 'xlsx':
                return convert_xlsx_to_standard_format(parsed_response)
            
            print(f"✅ DEBUG: Returning parsed response for {file_type}")
            return parsed_response

        except json.JSONDecodeError as json_err:
            print(f"❌ DEBUG: JSON decode error for {file_type}: {str(json_err)}")
            logger.error(f"JSON decode error for {file_type}: {str(json_err)}")
            logger.error(f"Problematic JSON for {file_type}: {json_text}")
            return {'processes': [], 'total_processes_found': 0, 'document_type': 'json_decode_error_distinct'}
            
    except (KeyError) as e:
        print(f"❌ DEBUG: KeyError for {file_type}: {str(e)}")
        logger.error(f"Failed to parse Bedrock distinct response structure for {file_type}: {str(e)}. Returning empty result.")
        return {'processes': [], 'total_processes_found': 0, 'document_type': 'response_structure_error_distinct'}
    except Exception as e:
        print(f"❌ DEBUG: Exception for {file_type}: {str(e)}")
        logger.exception(f"Error calling Bedrock for distinct processes {file_type}: {str(e)}. Returning empty result.")
        return {'processes': [], 'total_processes_found': 0, 'document_type': 'bedrock_error_distinct'}

def create_page_context(extracted_text_by_page):
    """Creates a context string with page information and image references."""
    if not extracted_text_by_page:
        return "No page or image information available."
    
    page_context = "PAGE INFORMATION WITH IMAGE REFERENCES:\n"
    for page_info in extracted_text_by_page:
        page_num = page_info.get('page', 'Unknown')
        image_details = page_info.get('image_details', [])
        page_context += f"\nPage {page_num}:\n"
        if image_details:
            page_context += "Images on this page:\n"
            for idx, img in enumerate(image_details):
                page_context += f"  - Image {idx+1}: {img.get('s3_path', 'No path')}\n"
        else:
            page_context += "No images on this page.\n"
    return page_context

def convert_xlsx_to_standard_format(xlsx_response):
    """Converts the specific XLSX JSON format from Bedrock into a standard format."""
    processes = []
    process_counter = 1
    sheets = xlsx_response.get('sheets', {})
    
    for sheet_name, categories in sheets.items():
        for category_name, category_data in categories.items():
            if isinstance(category_data, dict):
                steps = category_data.get('steps', [])
                related_pages = category_data.get('related_pages', [])
                if steps:
                    processes.append({
                        'process_id': f'process_{process_counter}',
                        'process_name': f'{sheet_name} - {category_name}',
                        'process_category': 'xlsx_process',
                        'steps': steps,
                        'related_pages': related_pages,
                        'image_references': []
                    })
                    process_counter += 1
    
    return {
        'processes': processes,
        'total_processes_found': len(processes),
        'document_type': 'xlsx_process_manual',
        'sheets': sheets
    }

def map_images_to_processes(processes_data, extracted_text_by_page):
    """Programmatically maps images to processes based on page numbers."""
    if not extracted_text_by_page:
        return processes_data
    
    images_by_page = {}
    for page_info in extracted_text_by_page:
        page_num = page_info.get('page')
        images_by_page[page_num] = page_info.get('image_details', [])
    
    if 'processes' in processes_data:
        for process in processes_data['processes']:
            relevant_images = []
            related_pages = process.get('related_pages', [])
            for page in related_pages:
                if page in images_by_page:
                    for img in images_by_page[page]:
                        if (img.get('width', 0) > 100 and img.get('height', 0) > 100) or img.get('size_bytes', 0) > 1000:
                            relevant_images.append({
                                's3_path': img.get('s3_path'),
                                'page': page,
                                'description': f"Image from page {page}"
                            })
            process['image_references'] = relevant_images
    
    elif 'sheets' in processes_data:
        for sheet_name, categories in processes_data['sheets'].items():
            for category_name, category_data in categories.items():
                if isinstance(category_data, dict):
                    relevant_images = []
                    related_pages = category_data.get('related_pages', [])
                    for page in related_pages:
                        if page in images_by_page:
                            for img in images_by_page[page]:
                                if (img.get('width', 0) > 100 and img.get('height', 0) > 100) or img.get('size_bytes', 0) > 1000:
                                    relevant_images.append({
                                        's3_path': img.get('s3_path'),
                                        'page': page,
                                        'description': f"Image from page {page}"
                                    })
                    category_data['image_references'] = relevant_images
    
    return processes_data

def extract_used_chunks_from_distinct_processes(distinct_processes_data):
    """Extract chunk IDs that were used in distinct processes."""
    used_chunk_ids = set()
    
    if 'processes' in distinct_processes_data:
        for process in distinct_processes_data['processes']:
            related_chunks = process.get('related_chunks', [])
            for chunk_id in related_chunks:
                used_chunk_ids.add(chunk_id)
    
    logger.info(f"Found {len(used_chunk_ids)} chunk IDs used in distinct processes: {used_chunk_ids}")
    return used_chunk_ids

def identify_non_distinct_chunks(semantic_chunks, used_chunk_ids):
    """Identify chunks that were not used in distinct processes."""
    non_distinct_chunks = []
    
    for chunk in semantic_chunks:
        chunk_id = chunk.get('chunk_id')
        if chunk_id not in used_chunk_ids:
            non_distinct_chunks.append(chunk)
    
    logger.info(f"Identified {len(non_distinct_chunks)} non-distinct chunks out of {len(semantic_chunks)} total chunks")
    return non_distinct_chunks

def create_non_distinct_processes_data(non_distinct_chunks, extracted_text_by_page):
    """Create a structured format for non-distinct processes from leftover chunks with page-wise organization."""
    try:
        # Parse content to extract page/slide information
        all_content = []
        for chunk in non_distinct_chunks:
            content = chunk.get('content', '').strip()
            if content:
                all_content.append(content)
        
        combined_content = ' '.join(all_content)
        
        # Extract page/slide sections using regex
        slide_pattern = r'=== Slide (\d+) ===(.*?)(?==== Slide \d+ ===|$)'
        slide_matches = re.findall(slide_pattern, combined_content, re.DOTALL)
        
        if slide_matches:
            # Create page-wise structure
            pages_data = {}
            for slide_num, slide_content in slide_matches:
                page_num = int(slide_num)
                pages_data[page_num] = {
                    'page_number': page_num,
                    'text_content': slide_content.strip(),
                    'image_references': []
                }
            
            # Map images to respective pages
            images_by_page = {}
            for page_info in extracted_text_by_page:
                page_num = page_info.get('page')
                if page_num:
                    images_by_page[page_num] = page_info.get('image_details', [])
            
            # Add images to each page
            for page_num in pages_data:
                if page_num in images_by_page:
                    for img in images_by_page[page_num]:
                        if (img.get('width', 0) > 100 and img.get('height', 0) > 100) or img.get('size_bytes', 0) > 1000:
                            pages_data[page_num]['image_references'].append({
                                's3_path': img.get('s3_path'),
                                'page': page_num,
                                'description': f"Image from page {page_num}"
                            })
            
            # Create the final structure
            non_distinct_processes = [{
                'process_id': 'non_distinct_process_1',
                'process_name': 'Non-distinct Process 1',
                'process_category': 'non_distinct',
                'pages': pages_data,
                'related_pages': list(pages_data.keys()),
                'total_pages': len(pages_data)
            }]
            
            return {
                'processes': non_distinct_processes,
                'total_processes_found': 1,
                'document_type': 'non_distinct_processes_leftover'
            }
        
        # Fallback to original logic if no slide markers found
        # [Keep existing logic here as fallback]
        
    except Exception as e:
        logger.error(f"Error creating non-distinct processes data: {str(e)}")
        return {
            'processes': [],
            'total_processes_found': 0,
            'document_type': 'non_distinct_processes_error',
            'error': str(e)
        }

def store_processes_to_s3(processes_data, event, process_type='distinct'):
    """Stores the identified processes to S3 with process type-specific folder structure."""
    try:
        c_name = event.get('client_name')
        output_bucket = DISTINCT_PROCESS_BUCKET
        
        if not output_bucket:
            raise ValueError("No valid S3 bucket name found in event payload.")
        
        original_s3_key = event.get('s3_key', 'unknown_file')
        filename = original_s3_key.split('/')[-1].split('.')[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        
        # Create folder structure based on process type
        if process_type == 'distinct':
            # Keep existing structure for distinct processes: <client-name>/distinct-process-folder/
            folder_name = "distinct_processes"
            processes_s3_key = f"{c_name}/{folder_name}/{timestamp}_{unique_id}_{filename}_{process_type}_processes.json"
        else:
            # New structure for non-distinct processes: non-distinct-process-folder/<client-name>/
            folder_name = "non_distinct_processes"
            processes_s3_key = f"{folder_name}/{c_name}/{timestamp}_{unique_id}_{filename}_{process_type}_processes.json"
        
        # Store with appropriate data structure
        data_key = f"{process_type}_processes"
        storage_data = {data_key: processes_data}
        
        s3_client.put_object(
            Bucket=output_bucket,
            Key=processes_s3_key,
            Body=json.dumps(storage_data, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Successfully stored {process_type} processes data to s3://{output_bucket}/{processes_s3_key}")
        return processes_s3_key, output_bucket
        
    except Exception as e:
        logger.error(f"Failed to store {process_type} processes to S3: {str(e)}")
        raise

def process_distinct_documents(semantic_chunks, file_type, extracted_text_by_page, event):
    """Process documents for distinct processes using LLM."""
    try:
        # Combine all text content
        combined_text = "\n\n".join([chunk['content'] for chunk in semantic_chunks])
        
        # Create prompt using S3 template for distinct processes
        prompt = create_prompt(file_type, combined_text, extracted_text_by_page, semantic_chunks, event)
        
        # Call Bedrock and parse response
        processes = call_bedrock_and_parse(prompt, file_type)
        
        # Map images to processes
        processes_with_images = map_images_to_processes(processes, extracted_text_by_page)
        
        # Add Mermaid flowchart syntax to each process
        final_processes = add_mermaid_to_processes(processes_with_images)
        logger.info("Successfully added Mermaid flowcharts to all distinct processes")
        
        # Store results to S3
        processes_s3_key, processes_s3_bucket = store_processes_to_s3(final_processes, event, 'distinct')
        
        return {
            'success': True,
            'processes_count': final_processes.get('total_processes_found', 0),
            'processes_s3_bucket': processes_s3_bucket,
            'processes_s3_key': processes_s3_key,
            'template_used': get_prompt_template_key(file_type),
            'mermaid_flowcharts_generated': True,
            'processes_data': final_processes  # Return the actual data for chunk analysis
        }
        
    except Exception as e:
        logger.error(f"Error processing distinct processes: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'processes_count': 0,
            'processes_data': {'processes': [], 'total_processes_found': 0}
        }

def process_non_distinct_documents(semantic_chunks, distinct_processes_data, extracted_text_by_page, event):
    """Process non-distinct documents by identifying leftover chunks."""
    try:
        # Extract chunk IDs used in distinct processes
        used_chunk_ids = extract_used_chunks_from_distinct_processes(distinct_processes_data)
        
        # Identify chunks not used in distinct processes
        non_distinct_chunks = identify_non_distinct_chunks(semantic_chunks, used_chunk_ids)
        
        if not non_distinct_chunks:
            logger.info("No non-distinct chunks found - all content was captured in distinct processes")
            return {
                'success': True,
                'processes_count': 0,
                'processes_s3_bucket': None,
                'processes_s3_key': None,
                'mermaid_flowcharts_generated': False,
                'message': 'All content was captured in distinct processes'
            }
        
        # Create non-distinct processes data from leftover chunks
        non_distinct_processes_data = create_non_distinct_processes_data(non_distinct_chunks, extracted_text_by_page)
        
        # Store results to S3
        processes_s3_key, processes_s3_bucket = store_processes_to_s3(non_distinct_processes_data, event, 'non_distinct')
        
        return {
            'success': True,
            'processes_count': non_distinct_processes_data.get('total_processes_found', 0),
            'processes_s3_bucket': processes_s3_bucket,
            'processes_s3_key': processes_s3_key,
            'mermaid_flowcharts_generated': True,
            'leftover_chunks_count': len(non_distinct_chunks),
            'original_chunks_count': len(semantic_chunks)
        }
        
    except Exception as e:
        logger.error(f"Error processing non-distinct processes: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'processes_count': 0
        }

def lambda_handler(event, context):
    """Main Lambda handler function - processes distinct processes via LLM and non-distinct via leftover analysis."""
    logger.info("Lambda function started with event: %s", json.dumps(event))
    
    try:
        # Get input data
        semantic_chunks = get_processes_input(event)
        file_type = event['file_type']
        extracted_text_by_page = event.get('extracted_text_by_page', [])
        client_name = event.get('client_name')
        txn_id = event.get('txn_id')
        content_hash = event.get('content_hash')
        is_duplicate = event.get('is_duplicate')
        
        # Process distinct processes using LLM
        logger.info("Starting distinct processes extraction using LLM...")
        distinct_results = process_distinct_documents(
            semantic_chunks, file_type, extracted_text_by_page, event
        )
        
        # Process non-distinct processes by analyzing leftover chunks
        logger.info("Starting non-distinct processes identification from leftover chunks...")
        non_distinct_results = process_non_distinct_documents(
            semantic_chunks, 
            distinct_results.get('processes_data', {}), 
            extracted_text_by_page, 
            event
        )
        
        # Prepare response with both results
        response = {
            'statusCode': 200,
            'client_name': client_name,
            'txn_id': txn_id,
            'content_hash' : content_hash,
            'is_duplicate' : is_duplicate,
            'file_type': file_type,
            'original_file': event.get('original_file'),
            'chunks_s3_bucket': event.get('chunks_s3_bucket'),
            'chunks_s3_key': event.get('chunks_s3_key'),
            'prompt_bucket': event.get('prompt_bucket', 'intouchx-prompts'),
            'timestamp_text_extraction':event.get('timestamp_text_extraction', ''),
            'timestamp_text_standardization':event.get('timestamp_text_standardization', ''),
            'timestamp_semantic_chunking': event.get('timestamp_semantic_chunking',''),
            'timestamp_identify_processes_processes': datetime.utcnow().isoformat(),
            # Distinct processes results (LLM-based)
            'distinct_processes': {
                'success': distinct_results['success'],
                'client_name': client_name,
                'content_hash' : content_hash,
                'is_duplicate' : is_duplicate,
                'processes_count': distinct_results['processes_count'],
                'processes_s3_bucket': distinct_results.get('processes_s3_bucket'),
                'processes_s3_key': distinct_results.get('processes_s3_key'),
                'template_used': distinct_results.get('template_used'),
                'mermaid_flowcharts_generated': distinct_results.get('mermaid_flowcharts_generated', False),
                'error': distinct_results.get('error'),
                'extraction_method': 'llm_based',
                'timestamp_text_extraction':event.get('timestamp_text_extraction', ''),
                'timestamp_text_standardization':event.get('timestamp_text_standardization', ''),
                'timestamp_semantic_chunking': event.get('timestamp_semantic_chunking',''),
                'timestamp_identify_processes_processes': datetime.utcnow().isoformat()
            },
            
            # Non-distinct processes results (leftover analysis)
            'non_distinct_processes': {
                'success': non_distinct_results['success'],
                'client_name': client_name,
                'content_hash' : content_hash,
                'is_duplicate' : is_duplicate,
                'processes_count': non_distinct_results['processes_count'],
                'processes_s3_bucket': non_distinct_results.get('processes_s3_bucket'),
                'processes_s3_key': non_distinct_results.get('processes_s3_key'),
                'mermaid_flowcharts_generated': non_distinct_results.get('mermaid_flowcharts_generated', False),
                'leftover_chunks_count': non_distinct_results.get('leftover_chunks_count', 0),
                'original_chunks_count': non_distinct_results.get('original_chunks_count', len(semantic_chunks)),
                'error': non_distinct_results.get('error'),
                'message': non_distinct_results.get('message'),
                'extraction_method': 'leftover_analysis',
                'timestamp_text_extraction':event.get('timestamp_text_extraction', ''),
                'timestamp_text_standardization':event.get('timestamp_text_standardization', ''),
                'timestamp_semantic_chunking': event.get('timestamp_semantic_chunking',''),
                'timestamp_identify_processes_processes': datetime.utcnow().isoformat()
            },
            
            # Summary
            'total_distinct_processes': distinct_results['processes_count'],
            'total_non_distinct_processes': non_distinct_results['processes_count'],
            'total_processes': distinct_results['processes_count'] + non_distinct_results['processes_count'],
            'total_chunks_analyzed': len(semantic_chunks),
            'chunks_coverage': {
                'distinct_processes_used_chunks': len(semantic_chunks) - non_distinct_results.get('leftover_chunks_count', 0),
                'non_distinct_leftover_chunks': non_distinct_results.get('leftover_chunks_count', 0),
                'coverage_percentage': round(((len(semantic_chunks) - non_distinct_results.get('leftover_chunks_count', 0)) / len(semantic_chunks)) * 100, 2) if semantic_chunks else 0
            },
            'processing_summary': {
                'distinct_success': distinct_results['success'],
                'non_distinct_success': non_distinct_results['success'],
                'overall_success': distinct_results['success'] and non_distinct_results['success']
            }
        }
        
        logger.info(f"Processing completed successfully. Total processes: {response['total_processes']} "
                   f"(Distinct: {response['total_distinct_processes']}, "
                   f"Non-distinct: {response['total_non_distinct_processes']}) "
                   f"Coverage: {response['chunks_coverage']['coverage_percentage']}%")
        
        return response
        
    except Exception as e:
        logger.exception("Error in lambda_handler: %s", str(e))
        return {
            'statusCode': 500,
            'error': str(e),
            'file_type': event.get('file_type', 'unknown'),
            'client_name': event.get('client_name'),
            'txn_id': event.get('txn_id'),
            'timestamp_error_occurred_at': datetime.utcnow().isoformat()
        }
