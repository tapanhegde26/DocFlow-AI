import os
import logging
import json
from typing import List, Dict, Any, Union

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Optional environment variables for flexibility
DEFAULT_CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 300))
DEFAULT_CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 50))
INCLUDE_IMAGE_REFS = os.environ.get("INCLUDE_IMAGE_REFS", "true").lower() == "true"
SEPARATE_IMAGE_CHUNKS = os.environ.get("SEPARATE_IMAGE_CHUNKS", "false").lower() == "true"
INCLUDE_TAGGING_INFO = os.environ.get("INCLUDE_TAGGING_INFO", "true").lower() == "true"

def extract_text_content(content_obj: Dict[str, Any]) -> str:
    """
    UPDATED: Extract meaningful text content including LLM tags and tagging information.
    """
    logger.info("=== STARTING TEXT EXTRACTION (UPDATED WITH TAGGING) ===")
    logger.info(f"INCLUDE_IMAGE_REFS setting: {INCLUDE_IMAGE_REFS}")
    logger.info(f"INCLUDE_TAGGING_INFO setting: {INCLUDE_TAGGING_INFO}")
    
    text_parts = []
    image_refs_processed = 0
    
    # Extract metadata
    if "metadata" in content_obj:
        metadata = content_obj["metadata"]
        logger.info("✅ Found metadata section")
        text_parts.append(f"Process: {metadata.get('process_name', '')}")
        text_parts.append(f"Process ID: {metadata.get('process_id', '')}")
        text_parts.append(f"Process UUID: {metadata.get('process_uuid', '')}")
        text_parts.append(f"Created: {metadata.get('created_timestamp', '')}")
        
        # Extract source file info
        if "source_file" in metadata:
            source = metadata["source_file"]
            text_parts.append(f"Source File Type: {source.get('file_type', '')}")
            text_parts.append(f"Original Filename: {source.get('original_filename', 'Unknown')}")
            text_parts.append(f"S3 Location: {source.get('s3_key', '')}")
        
        # Extract processing info
        if "processing_info" in metadata:
            proc_info = metadata["processing_info"]
            text_parts.append(f"Extraction Method: {proc_info.get('extraction_method', '')}")
            text_parts.append(f"Chunking Method: {proc_info.get('chunking_method', '')}")
            text_parts.append(f"Identification Method: {proc_info.get('identification_method', '')}")

    # Extract process details
    if "process_details" in content_obj:
        details = content_obj["process_details"]
        logger.info("✅ Found process_details section")
        
        text_parts.append(f"Process Name: {details.get('name', '')}")
        text_parts.append(f"Description: {details.get('description', '')}")
        text_parts.append(f"Category: {details.get('category', '')}")
        
        # Extract steps
        if "steps" in details and details["steps"]:
            logger.info(f"✅ Found {len(details['steps'])} process steps")
            text_parts.append("Process Steps:")
            for i, step in enumerate(details["steps"], 1):
                text_parts.append(f"Step {i}: {step}")
        
        # Extract location info
        if "location_info" in details:
            loc_info = details["location_info"]
            if loc_info.get("section_location"):
                text_parts.append(f"Section Location: {loc_info['section_location']}")
            if loc_info.get("location"):
                text_parts.append(f"Location: {loc_info['location']}")
            if loc_info.get("organization_pattern"):
                text_parts.append(f"Organization Pattern: {loc_info['organization_pattern']}")
        
        # Extract related pages
        if "related_pages" in details and details["related_pages"]:
            pages_text = ", ".join(map(str, details["related_pages"]))
            text_parts.append(f"Related Pages: {pages_text}")
        
        # *** FIXED: Force image references processing ***
        if "image_references" in details:
            image_refs = details["image_references"]
            logger.info(f"🖼️  FOUND {len(image_refs)} IMAGE REFERENCES")
            
            if INCLUDE_IMAGE_REFS and image_refs:
                logger.info("🖼️  FORCE PROCESSING IMAGE REFERENCES")
                
                # Add a clear separator
                text_parts.append("=" * 50)
                text_parts.append("IMAGE REFERENCES SECTION")
                text_parts.append("=" * 50)
                
                for idx, img_ref in enumerate(image_refs):
                    page = img_ref.get('page', 'Unknown')
                    description = img_ref.get('description', 'No description')
                    s3_path = img_ref.get('s3_path', 'No path')
                    
                    # Create very explicit image reference text
                    img_text = f"IMAGE_REF_{idx+1}: Page {page} - {description} - Location: {s3_path}"
                    text_parts.append(img_text)
                    image_refs_processed += 1
                    logger.info(f"📷 PROCESSED image ref {idx+1}: Page {page}")
                
                # Add closing separator
                text_parts.append("=" * 50)
                text_parts.append(f"END IMAGE REFERENCES ({image_refs_processed} total)")
                text_parts.append("=" * 50)
                
                logger.info(f"✅ SUCCESSFULLY PROCESSED {image_refs_processed} IMAGE REFERENCES")
            else:
                logger.warning("❌ IMAGE REFERENCES SKIPPED - INCLUDE_IMAGE_REFS is False or no refs")
        else:
            logger.warning("❌ NO 'image_references' KEY FOUND in process_details")
            
        # Extract mermaid syntax (ADD THIS SECTION)
        if "mermaid_syntax" in details and details["mermaid_syntax"]:
            logger.info("🔄 Found mermaid syntax diagram")
            text_parts.append("=" * 50)
            text_parts.append("PROCESS FLOW DIAGRAM (MERMAID)")
            text_parts.append("=" * 50)
            text_parts.append("Mermaid Flowchart Syntax:")
            text_parts.append(details["mermaid_syntax"])
            text_parts.append("=" * 50)
            text_parts.append("END PROCESS FLOW DIAGRAM")
            text_parts.append("=" * 50)
            logger.info("✅ Successfully processed mermaid syntax")
        else:
            logger.info("❌ No mermaid syntax found in process_details")


    # Extract main content 
    if "content" in content_obj:
        content_section = content_obj["content"]
        logger.info("✅ Found content section")
        
        # Check for full_content
        if "full_content" in content_section and content_section["full_content"]:
            logger.info(f"✅ Found full_content with {len(content_section['full_content'])} characters")
            text_parts.append("Full Content:")
            text_parts.append(content_section["full_content"])
        
        # Extract content from related_chunks if available
        if "related_chunks" in content_section and content_section["related_chunks"]:
            logger.info(f"✅ Found {len(content_section['related_chunks'])} related chunks")
            text_parts.append("Related Content:")
            for chunk in content_section["related_chunks"]:
                if "content" in chunk and chunk["content"]:
                    section_title = chunk.get('section_title', 'Untitled Section')
                    text_parts.append(f"Section: {section_title}")
                    text_parts.append(chunk["content"])

    # Extract analytics info
    if "analytics" in content_obj:
        analytics = content_obj["analytics"]
        analytics_text = (f"Document Analytics - "
                         f"Word Count: {analytics.get('word_count', 0)}, "
                         f"Character Count: {analytics.get('character_count', 0)}, "
                         f"Step Count: {analytics.get('step_count', 0)}, "
                         f"Complexity Score: {analytics.get('complexity_score', 0)}, "
                         f"Image Count: {analytics.get('image_count', 0)}")
        text_parts.append(analytics_text)

    # *** NEW: Extract LLM Tags and Tagging Information ***
    if INCLUDE_TAGGING_INFO:
        logger.info("🏷️  PROCESSING TAGGING INFORMATION")
        
        # Extract LLM Tags
        if "llm_tags" in content_obj and content_obj["llm_tags"]:
            llm_tags = content_obj["llm_tags"]
            logger.info(f"🏷️  Found {len(llm_tags)} LLM tags")
            
            text_parts.append("=" * 50)
            text_parts.append("LLM TAGS SECTION")
            text_parts.append("=" * 50)
            text_parts.append(f"LLM Generated Tags ({len(llm_tags)} total):")
            text_parts.append(", ".join(llm_tags))
            
            # Add individual tag entries for better searchability
            for idx, tag in enumerate(llm_tags, 1):
                text_parts.append(f"Tag_{idx}: {tag}")
        
        # Extract Tag Categories
        if "tag_categories" in content_obj and content_obj["tag_categories"]:
            tag_categories = content_obj["tag_categories"]
            logger.info(f"🏷️  Found {len(tag_categories)} tag categories")
            
            text_parts.append("TAG CATEGORIES:")
            for category, tags in tag_categories.items():
                if tags:  # Only include categories that have tags
                    text_parts.append(f"{category.upper()}: {', '.join(tags)}")
                    # Add individual category-tag entries for better searchability
                    for tag in tags:
                        text_parts.append(f"Category_{category}: {tag}")
        
        # Extract Tagging Info
        if "tagging_info" in content_obj and content_obj["tagging_info"]:
            tagging_info = content_obj["tagging_info"]
            logger.info("🏷️  Found tagging_info section")
            
            text_parts.append("TAGGING METADATA:")
            text_parts.append(f"LLM Model Used: {tagging_info.get('llm_model_used', 'Unknown')}")
            text_parts.append(f"Tagging Timestamp: {tagging_info.get('tagging_timestamp', 'Unknown')}")
            text_parts.append(f"Tags Count: {tagging_info.get('tags_count', 0)}")
            text_parts.append(f"Tagging Status: {tagging_info.get('tagging_status', 'Unknown')}")
            text_parts.append(f"Original Object Key: {tagging_info.get('original_object_key', 'Unknown')}")
            
            text_parts.append("=" * 50)
            text_parts.append("END TAGGING INFORMATION")
            text_parts.append("=" * 50)
        
        logger.info("✅ SUCCESSFULLY PROCESSED TAGGING INFORMATION")
    else:
        logger.info("🏷️  TAGGING INFORMATION PROCESSING DISABLED")

    # Combine all text parts
    combined_text = "\n\n".join(filter(None, text_parts))
    
    # CRITICAL: Verify image references are in final text
    image_refs_in_final_text = combined_text.count("IMAGE_REF_")
    tagging_sections_in_final_text = combined_text.count("LLM TAGS SECTION") + combined_text.count("TAG CATEGORIES:")
    
    logger.info("=== TEXT EXTRACTION COMPLETE ===")
    logger.info(f"📊 Total text parts collected: {len(text_parts)}")
    logger.info(f"📊 Final combined text length: {len(combined_text)} characters")
    logger.info(f"🖼️  Image references processed: {image_refs_processed}")
    logger.info(f"🖼️  Image references in final text: {image_refs_in_final_text}")
    logger.info(f"🏷️  Tagging sections in final text: {tagging_sections_in_final_text}")
    
    # Log the portion containing tagging information
    if "LLM TAGS SECTION" in combined_text:
        start_idx = combined_text.find("LLM TAGS SECTION")
        end_idx = combined_text.find("END TAGGING INFORMATION")
        if start_idx != -1 and end_idx != -1:
            tagging_section = combined_text[start_idx:end_idx + 100]
            logger.info(f"🏷️  TAGGING SECTION PREVIEW: {tagging_section[:200]}...")
    else:
        logger.warning("❌ 'LLM TAGS SECTION' NOT FOUND in final text!")
    
    # Final verification
    if image_refs_processed > 0 and image_refs_in_final_text == 0:
        logger.error("🚨 CRITICAL: Image references processed but missing from final text!")
    elif image_refs_processed > 0 and image_refs_in_final_text > 0:
        logger.info("✅ SUCCESS: Image references confirmed in final text!")
    
    # Tagging verification
    if INCLUDE_TAGGING_INFO and "llm_tags" in content_obj and content_obj["llm_tags"]:
        if tagging_sections_in_final_text == 0:
            logger.error("🚨 CRITICAL: LLM tags found in input but missing from final text!")
        else:
            logger.info("✅ SUCCESS: LLM tags confirmed in final text!")
    
    return combined_text

def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[Dict[str, Any]]:
    """
    UPDATED: Splits text with guaranteed image reference and tagging detection.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected string input, got {type(text)}")
    
    logger.info("=== STARTING TEXT CHUNKING (UPDATED VERSION) ===")
    logger.info(f"📏 Input text length: {len(text)} characters")
    logger.info(f"📏 Chunk size: {chunk_size}, Overlap: {overlap}")
    
    # Pre-check for image references and tagging info in input text
    image_refs_in_input = text.count("IMAGE_REF_")
    tagging_sections_in_input = text.count("LLM TAGS SECTION") + text.count("TAG CATEGORIES:")
    llm_tags_in_input = text.count("Tag_")
    
    logger.info(f"🖼️  Image references detected in input text: {image_refs_in_input}")
    logger.info(f"🏷️  Tagging sections detected in input text: {tagging_sections_in_input}")
    logger.info(f"🏷️  Individual LLM tags detected in input text: {llm_tags_in_input}")
    
    chunks = []
    start = 0
    text_length = len(text)
    chunk_index = 0
    total_image_refs_in_chunks = 0
    total_tag_refs_in_chunks = 0
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk_content = text[start:end].strip()
        
        if chunk_content:
            # Count image references and tagging info in this chunk
            image_refs_in_chunk = chunk_content.count("IMAGE_REF_")
            tag_refs_in_chunk = chunk_content.count("Tag_")
            category_refs_in_chunk = chunk_content.count("Category_")
            tagging_sections_in_chunk = chunk_content.count("LLM TAGS SECTION") + chunk_content.count("TAG CATEGORIES:")
            
            total_image_refs_in_chunks += image_refs_in_chunk
            total_tag_refs_in_chunks += tag_refs_in_chunk
            
            chunk_obj = {
                "chunk_id": f"text_chunk_{chunk_index}",
                "content": chunk_content,
                "metadata": {
                    "chunk_index": chunk_index,
                    "chunk_type": "text_content",
                    "start_position": start,
                    "end_position": end,
                    "chunk_size": len(chunk_content),
                    "total_text_length": text_length,
                    "is_image_reference": False,
                    "contains_image_refs": image_refs_in_chunk > 0,
                    "image_ref_count": image_refs_in_chunk,
                    "contains_llm_tags": tag_refs_in_chunk > 0,
                    "llm_tag_count": tag_refs_in_chunk,
                    "category_ref_count": category_refs_in_chunk,
                    "contains_tagging_sections": tagging_sections_in_chunk > 0
                }
            }
            chunks.append(chunk_obj)
            
            # Detailed logging for each chunk
            logger.info(f"📝 Created chunk {chunk_index}: positions {start}-{end}, size {len(chunk_content)}")
            
            if image_refs_in_chunk > 0:
                logger.info(f"🖼️  ✅ CHUNK {chunk_index} CONTAINS {image_refs_in_chunk} IMAGE REFERENCES!")
                # Log a snippet of the image references
                if "IMAGE_REF_" in chunk_content:
                    image_lines = [line for line in chunk_content.split('\n') if 'IMAGE_REF_' in line]
                    for line in image_lines[:3]:  # Show first 3 image references
                        logger.info(f"🖼️     {line[:100]}...")
            
            if tag_refs_in_chunk > 0:
                logger.info(f"🏷️  ✅ CHUNK {chunk_index} CONTAINS {tag_refs_in_chunk} LLM TAG REFERENCES!")
                # Log a snippet of the tag references
                if "Tag_" in chunk_content:
                    tag_lines = [line for line in chunk_content.split('\n') if 'Tag_' in line]
                    for line in tag_lines[:3]:  # Show first 3 tag references
                        logger.info(f"🏷️     {line[:100]}...")
            
            if category_refs_in_chunk > 0:
                logger.info(f"🏷️  ✅ CHUNK {chunk_index} CONTAINS {category_refs_in_chunk} CATEGORY REFERENCES!")
            
            if tagging_sections_in_chunk > 0:
                logger.info(f"🏷️  ✅ CHUNK {chunk_index} CONTAINS TAGGING SECTIONS!")
            
            chunk_index += 1
        
        # Move start position (creates overlap)
        start += chunk_size - overlap
        
        # Prevent infinite loop for very small texts
        if chunk_size - overlap <= 0:
            break

    logger.info("=== TEXT CHUNKING COMPLETE ===")
    logger.info(f"📊 Generated {len(chunks)} text chunks")
    logger.info(f"🖼️  Total image references found across all chunks: {total_image_refs_in_chunks}")
    logger.info(f"🖼️  Expected image references: {image_refs_in_input}")
    logger.info(f"🏷️  Total LLM tag references found across all chunks: {total_tag_refs_in_chunks}")
    logger.info(f"🏷️  Expected LLM tag references: {llm_tags_in_input}")
    
    # Verification
    if image_refs_in_input > 0 and total_image_refs_in_chunks == 0:
        logger.error("🚨 CRITICAL: Image references in input but NONE found in chunks!")
    elif total_image_refs_in_chunks >= image_refs_in_input:
        logger.info("✅ SUCCESS: All image references captured in chunks!")
    
    # Tagging verification
    if llm_tags_in_input > 0 and total_tag_refs_in_chunks == 0:
        logger.error("🚨 CRITICAL: LLM tag references in input but NONE found in chunks!")
    elif total_tag_refs_in_chunks >= llm_tags_in_input:
        logger.info("✅ SUCCESS: All LLM tag references captured in chunks!")
    
    return chunks

def extract_image_references_as_chunks(content_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract image references as separate specialized chunks.
    """
    logger.info("=== EXTRACTING SEPARATE IMAGE CHUNKS ===")
    image_chunks = []
    
    if "process_details" in content_obj and "image_references" in content_obj["process_details"]:
        image_refs = content_obj["process_details"]["image_references"]
        logger.info(f"🖼️  Creating {len(image_refs)} separate image reference chunks")
        
        for idx, img_ref in enumerate(image_refs):
            content_text = (f"Image Reference for Page {img_ref.get('page', 'Unknown')}: "
                           f"{img_ref.get('description', 'No description available')}. "
                           f"This image supports the process documentation and can be found at: "
                           f"{img_ref.get('s3_path', 'Path not available')}")
            
            chunk = {
                "chunk_id": f"image_ref_{idx}",
                "content": content_text,
                "metadata": {
                    "chunk_index": idx,
                    "chunk_type": "image_reference",
                    "s3_path": img_ref.get('s3_path'),
                    "page": img_ref.get('page'),
                    "description": img_ref.get('description'),
                    "start_position": 0,
                    "end_position": len(content_text),
                    "chunk_size": len(content_text),
                    "is_image_reference": True
                }
            }
            image_chunks.append(chunk)
            logger.info(f"📷 Created image chunk {idx}: Page {img_ref.get('page')}")
    else:
        logger.warning("❌ No image references found for separate chunk creation")
    
    logger.info(f"✅ Created {len(image_chunks)} separate image chunks")
    return image_chunks

def extract_tagging_as_chunks(content_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    NEW: Extract tagging information as separate specialized chunks.
    """
    logger.info("=== EXTRACTING SEPARATE TAGGING CHUNKS ===")
    tagging_chunks = []
    
    # Create LLM Tags chunk
    if "llm_tags" in content_obj and content_obj["llm_tags"]:
        llm_tags = content_obj["llm_tags"]
        logger.info(f"🏷️  Creating LLM tags chunk with {len(llm_tags)} tags")
        
        content_text = (f"LLM Generated Tags for this process: {', '.join(llm_tags)}. "
                       f"These tags were automatically generated to help categorize and search for this process. "
                       f"Total tags: {len(llm_tags)}")
        
        chunk = {
            "chunk_id": "llm_tags_chunk",
            "content": content_text,
            "metadata": {
                "chunk_index": 0,
                "chunk_type": "llm_tags",
                "tags": llm_tags,
                "tags_count": len(llm_tags),
                "start_position": 0,
                "end_position": len(content_text),
                "chunk_size": len(content_text),
                "is_tagging_reference": True
            }
        }
        tagging_chunks.append(chunk)
        logger.info(f"🏷️  Created LLM tags chunk with {len(llm_tags)} tags")
    
    # Create Tag Categories chunk
    if "tag_categories" in content_obj and content_obj["tag_categories"]:
        tag_categories = content_obj["tag_categories"]
        logger.info(f"🏷️  Creating tag categories chunk with {len(tag_categories)} categories")
        
        category_descriptions = []
        for category, tags in tag_categories.items():
            if tags:
                category_descriptions.append(f"{category.title()}: {', '.join(tags)}")
        
        content_text = (f"Tag Categories for this process: {'; '.join(category_descriptions)}. "
                       f"These categorized tags help organize and filter processes by type, department, and subject matter.")
        
        chunk = {
            "chunk_id": "tag_categories_chunk",
            "content": content_text,
            "metadata": {
                "chunk_index": 1,
                "chunk_type": "tag_categories",
                "categories": tag_categories,
                "categories_count": len(tag_categories),
                "start_position": 0,
                "end_position": len(content_text),
                "chunk_size": len(content_text),
                "is_tagging_reference": True
            }
        }
        tagging_chunks.append(chunk)
        logger.info(f"🏷️  Created tag categories chunk with {len(tag_categories)} categories")
    
    # Create Tagging Info chunk
    if "tagging_info" in content_obj and content_obj["tagging_info"]:
        tagging_info = content_obj["tagging_info"]
        logger.info("🏷️  Creating tagging info chunk")
        
        content_text = (f"Tagging Information: This process was tagged using {tagging_info.get('llm_model_used', 'Unknown model')} "
                       f"on {tagging_info.get('tagging_timestamp', 'Unknown date')}. "
                       f"Tagging status: {tagging_info.get('tagging_status', 'Unknown')}. "
                       f"Total tags generated: {tagging_info.get('tags_count', 0)}. "
                       f"Original location: {tagging_info.get('original_object_key', 'Unknown')}")
        
        chunk = {
            "chunk_id": "tagging_info_chunk",
            "content": content_text,
            "metadata": {
                "chunk_index": 2,
                "chunk_type": "tagging_info",
                "tagging_info": tagging_info,
                "start_position": 0,
                "end_position": len(content_text),
                "chunk_size": len(content_text),
                "is_tagging_reference": True
            }
        }
        tagging_chunks.append(chunk)
        logger.info("🏷️  Created tagging info chunk")
    
    logger.info(f"✅ Created {len(tagging_chunks)} separate tagging chunks")
    return tagging_chunks

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    UPDATED: Main Lambda handler with guaranteed image reference and tagging processing.
    """
    logger.info("=== LAMBDA HANDLER STARTED (UPDATED WITH TAGGING) ===")
    logger.info(f"🔧 Environment Variables:")
    logger.info(f"   INCLUDE_IMAGE_REFS: {INCLUDE_IMAGE_REFS}")
    logger.info(f"   SEPARATE_IMAGE_CHUNKS: {SEPARATE_IMAGE_CHUNKS}")
    logger.info(f"   INCLUDE_TAGGING_INFO: {INCLUDE_TAGGING_INFO}")
    logger.info(f"   DEFAULT_CHUNK_SIZE: {DEFAULT_CHUNK_SIZE}")
    logger.info(f"   DEFAULT_CHUNK_OVERLAP: {DEFAULT_CHUNK_OVERLAP}")
    logger.info(f"📋 Request ID: {context.aws_request_id}")
    
    logger.info(f"🔍 DEBUG: Full event keys: {list(event.keys())}")
    logger.info(f"🔍 DEBUG: Event metadata: {event.get('metadata', 'NOT FOUND')}")

    try:
        # Extract content from event
        content = event.get("content")
        if not content:
            logger.error("❌ Missing 'content' in input event")
            raise ValueError("Missing required field: content")
        
        # Handle different content types
        all_chunks = []
        text_to_chunk = ""
        input_image_count = 0
        input_tags_count = 0
        input_categories_count = 0
        
        if isinstance(content, str):
            logger.info("📄 Processing simple string content")
            text_to_chunk = content
        elif isinstance(content, dict):
            logger.info("📊 Processing complex SOP JSON content structure")
            logger.info(f"📊 Content object top-level keys: {list(content.keys())}")
            
            # Count input image references for verification
            if "process_details" in content and "image_references" in content["process_details"]:
                input_image_count = len(content["process_details"]["image_references"])
                logger.info(f"🖼️  INPUT CONTAINS {input_image_count} IMAGE REFERENCES")
            
            # Count input tagging information for verification
            if "llm_tags" in content:
                input_tags_count = len(content["llm_tags"])
                logger.info(f"🏷️  INPUT CONTAINS {input_tags_count} LLM TAGS")
            
            if "tag_categories" in content:
                input_categories_count = len(content["tag_categories"])
                logger.info(f"🏷️  INPUT CONTAINS {input_categories_count} TAG CATEGORIES")
            
            # Extract text content with detailed logging
            text_to_chunk = extract_text_content(content)
            
            # If configured to create separate image chunks, add them
            if SEPARATE_IMAGE_CHUNKS:
                logger.info("🖼️  SEPARATE_IMAGE_CHUNKS enabled - creating dedicated image chunks")
                image_chunks = extract_image_references_as_chunks(content)
                all_chunks.extend(image_chunks)
                logger.info(f"✅ Added {len(image_chunks)} separate image reference chunks")
            else:
                logger.info("🖼️  SEPARATE_IMAGE_CHUNKS disabled - no separate image chunks will be created")
            
            # NEW: If configured to create separate tagging chunks, add them
            separate_tagging_chunks = os.environ.get("SEPARATE_TAGGING_CHUNKS", "false").lower() == "true"
            if separate_tagging_chunks:
                logger.info("🏷️  SEPARATE_TAGGING_CHUNKS enabled - creating dedicated tagging chunks")
                tagging_chunks = extract_tagging_as_chunks(content)
                all_chunks.extend(tagging_chunks)
                logger.info(f"✅ Added {len(tagging_chunks)} separate tagging chunks")
            else:
                logger.info("🏷️  SEPARATE_TAGGING_CHUNKS disabled - no separate tagging chunks will be created")
                
        else:
            logger.error(f"❌ Unsupported content type: {type(content)}")
            raise ValueError(f"Content must be string or dict, got {type(content)}")
        
        # Verify text extraction results
        image_refs_in_extracted_text = text_to_chunk.count("IMAGE_REF_") if text_to_chunk else 0
        tag_refs_in_extracted_text = text_to_chunk.count("Tag_") if text_to_chunk else 0
        tagging_sections_in_extracted_text = text_to_chunk.count("LLM TAGS SECTION") if text_to_chunk else 0
        
        logger.info(f"🖼️  Text extraction results: {image_refs_in_extracted_text} image refs in {len(text_to_chunk)} chars")
        logger.info(f"🏷️  Text extraction results: {tag_refs_in_extracted_text} tag refs, {tagging_sections_in_extracted_text} tagging sections")
        
        # Check if we have meaningful text to chunk
        if not text_to_chunk or not text_to_chunk.strip():
            logger.warning("⚠️  No meaningful text content found to chunk")
            logger.info(f"📊 Returning {len(all_chunks)} special chunks only")
            return {
                "success": True,
                "chunks": all_chunks,
                "metadata": {
                    "total_chunks": len(all_chunks),
                    "text_chunks": 0,
                    "image_chunks": len([c for c in all_chunks if c.get("metadata", {}).get("chunk_type") == "image_reference"]),
                    "tagging_chunks": len([c for c in all_chunks if c.get("metadata", {}).get("is_tagging_reference", False)]),
                    "original_content_type": type(content).__name__,
                    "image_references_included": INCLUDE_IMAGE_REFS,
                    "tagging_info_included": INCLUDE_TAGGING_INFO,
                    "separate_image_chunks": SEPARATE_IMAGE_CHUNKS,
                    "separate_tagging_chunks": separate_tagging_chunks,
                    "request_id": context.aws_request_id,
                    "text_extraction_length": 0,
                    "input_image_count": input_image_count,
                    "input_tags_count": input_tags_count,
                    "input_categories_count": input_categories_count,
                    "extracted_image_refs": 0,
                    "extracted_tag_refs": 0
                }
            }
        
        # Get chunking parameters
        chunk_size = int(event.get("chunk_size", DEFAULT_CHUNK_SIZE))
        overlap = int(event.get("chunk_overlap", DEFAULT_CHUNK_OVERLAP))
        
        logger.info(f"📏 Using chunk_size: {chunk_size}, overlap: {overlap}")
        
        # Validate parameters
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk_size}")
        if overlap < 0:
            raise ValueError(f"chunk_overlap cannot be negative, got {overlap}")
        if overlap >= chunk_size:
            logger.warning(f"⚠️  Overlap ({overlap}) >= chunk_size ({chunk_size}), reducing overlap")
            overlap = max(0, chunk_size - 1)
        
        # Perform text chunking
        logger.info("🔄 Starting text chunking process...")
        text_chunks = chunk_text(text_to_chunk, chunk_size=chunk_size, overlap=overlap)
        
        # Analyze chunking results for image references and tagging
        text_chunks_with_images = 0
        text_chunks_with_tags = 0
        total_image_refs_in_text_chunks = 0
        total_tag_refs_in_text_chunks = 0
        
        for i, chunk in enumerate(text_chunks):
            chunk_content = chunk["content"]
            image_count = chunk_content.count("IMAGE_REF_")
            tag_count = chunk_content.count("Tag_")
            
            if image_count > 0:
                text_chunks_with_images += 1
                total_image_refs_in_text_chunks += image_count
                logger.info(f"🖼️  ✅ Chunk {i} contains {image_count} image references")
            
            if tag_count > 0:
                text_chunks_with_tags += 1
                total_tag_refs_in_text_chunks += tag_count
                logger.info(f"🏷️  ✅ Chunk {i} contains {tag_count} tag references")
        
        # Combine text chunks with any special chunks
        all_chunks.extend(text_chunks)
        
        # Calculate final statistics
        total_chunks = len(all_chunks)
        text_chunk_count = len(text_chunks)
        image_chunk_count = len([c for c in all_chunks if c.get("metadata", {}).get("chunk_type") == "image_reference"])
        tagging_chunk_count = len([c for c in all_chunks if c.get("metadata", {}).get("is_tagging_reference", False)])
        
        # Prepare comprehensive response
        response = {
            "success": True,
            "chunks": all_chunks,
            "metadata": {
                "total_chunks": total_chunks,
                "text_chunks": text_chunk_count,
                "image_chunks": image_chunk_count,
                "tagging_chunks": tagging_chunk_count,
                "text_chunks_with_image_refs": text_chunks_with_images,
                "text_chunks_with_tag_refs": text_chunks_with_tags,
                "total_image_refs_in_text_chunks": total_image_refs_in_text_chunks,
                "total_tag_refs_in_text_chunks": total_tag_refs_in_text_chunks,
                "original_content_type": type(content).__name__,
                "chunk_size": chunk_size,
                "chunk_overlap": overlap,
                "original_text_length": len(text_to_chunk),
                "image_references_included": INCLUDE_IMAGE_REFS,
                "tagging_info_included": INCLUDE_TAGGING_INFO,
                "separate_image_chunks": SEPARATE_IMAGE_CHUNKS,
                "separate_tagging_chunks": separate_tagging_chunks,
                "request_id": context.aws_request_id,
                "processing_summary": {
                    "environment_settings": {
                        "include_image_refs": INCLUDE_IMAGE_REFS,
                        "include_tagging_info": INCLUDE_TAGGING_INFO,
                        "separate_image_chunks": SEPARATE_IMAGE_CHUNKS,
                        "separate_tagging_chunks": separate_tagging_chunks
                    },
                    "image_processing_results": {
                        "input_image_count": input_image_count,
                        "extracted_image_refs": image_refs_in_extracted_text,
                        "final_image_refs_in_chunks": total_image_refs_in_text_chunks + image_chunk_count,
                        "processing_successful": (input_image_count > 0 and 
                                                 (total_image_refs_in_text_chunks > 0 or image_chunk_count > 0))
                    },
                    "tagging_processing_results": {
                        "input_tags_count": input_tags_count,
                        "input_categories_count": input_categories_count,
                        "extracted_tag_refs": tag_refs_in_extracted_text,
                        "extracted_tagging_sections": tagging_sections_in_extracted_text,
                        "final_tag_refs_in_chunks": total_tag_refs_in_text_chunks + tagging_chunk_count,
                        "processing_successful": (input_tags_count > 0 and 
                                                 (total_tag_refs_in_text_chunks > 0 or tagging_chunk_count > 0))
                    },
                    "content_analysis": {
                        "has_process_details": "process_details" in content if isinstance(content, dict) else False,
                        "has_image_references": input_image_count > 0,
                        "has_llm_tags": input_tags_count > 0,
                        "has_tag_categories": input_categories_count > 0,
                        "has_tagging_info": "tagging_info" in content if isinstance(content, dict) else False
                    }
                }
            }
        }
        logger.info(f"📊 Returning {total_chunks} total chunks - before metadata check")

        # Add original metadata if present
        if isinstance(content, dict) and "metadata" in content:
            response["original_metadata"] = content["metadata"]
        
        # Add tagging metadata if present
        if isinstance(content, dict):
            if "llm_tags" in content:
                response["original_llm_tags"] = content["llm_tags"]
            if "tag_categories" in content:
                response["original_tag_categories"] = content["tag_categories"]
            if "tagging_info" in content:
                response["original_tagging_info"] = content["tagging_info"]
        

        # Add process S3 information from event metadata
        logger.info("📋 🔍 STARTING S3 EXTRACTION BLOCK")
        logger.info(f"📋 🔍 Event keys available: {list(event.keys())}")
        logger.info(f"📋 🔍 Checking for 'metadata' in event...")


        if "metadata" in event:
            event_metadata = event["metadata"]
            logger.info(f"📋 ✅ Found event metadata: {event_metadata}")
            logger.info(f"📋 Found event metadata with keys: {list(event_metadata.keys())}")
            if "s3_key" in event_metadata:  # Changed from "process_s3_key"
                response["process_s3_key"] = event_metadata["s3_key"]
                logger.info(f"📋 ✅ Added process_s3_key: {event_metadata['s3_key']}")
            else:
                logger.warning("📋 ❌ s3_key not found in event metadata")
            if "bucket" in event_metadata:  # Changed from "process_bucket"
                response["process_bucket"] = event_metadata["bucket"]
                logger.info(f"📋 ✅ Added process_bucket: {event_metadata['bucket']}")
            else:
                logger.warning("📋 ❌ bucket not found in event metadata")
        else:
            logger.warning("📋 ❌ No 'metadata' found in event")
            logger.warning(f"📋 ❌ Available event keys: {list(event.keys())}")

        logger.info("📋 🔍 S3 EXTRACTION BLOCK COMPLETED")


        # Final comprehensive logging
        logger.info("=== PROCESSING COMPLETE ===")
        logger.info(f"✅ Successfully processed content into {total_chunks} total chunks")
        logger.info(f"📊 Breakdown: {text_chunk_count} text chunks, {image_chunk_count} image chunks, {tagging_chunk_count} tagging chunks")
        logger.info(f"🖼️  Input image references: {input_image_count}")
        logger.info(f"🖼️  Image references in extracted text: {image_refs_in_extracted_text}")
        logger.info(f"🖼️  Text chunks containing image references: {text_chunks_with_images}")
        logger.info(f"🖼️  Total image references in text chunks: {total_image_refs_in_text_chunks}")
        logger.info(f"🖼️  Separate image chunks: {image_chunk_count}")
        logger.info(f"🖼️  Final image references in output: {total_image_refs_in_text_chunks + image_chunk_count}")
        logger.info(f"🏷️  Input LLM tags: {input_tags_count}")
        logger.info(f"🏷️  Tag references in extracted text: {tag_refs_in_extracted_text}")
        logger.info(f"🏷️  Text chunks containing tag references: {text_chunks_with_tags}")
        logger.info(f"🏷️  Total tag references in text chunks: {total_tag_refs_in_text_chunks}")
        logger.info(f"🏷️  Separate tagging chunks: {tagging_chunk_count}")
        logger.info(f"🏷️  Final tag references in output: {total_tag_refs_in_text_chunks + tagging_chunk_count}")
        
        # Critical verification and warnings
        expected_output_images = total_image_refs_in_text_chunks + image_chunk_count
        expected_output_tags = total_tag_refs_in_text_chunks + tagging_chunk_count
        
        if input_image_count > 0 and expected_output_images == 0:
            logger.error("🚨 CRITICAL ERROR: Image references found in input but ZERO in output!")
            logger.error(f"🚨 Expected: {input_image_count}, Got: {expected_output_images}")
        elif input_image_count > 0 and expected_output_images < input_image_count:
            logger.warning(f"⚠️  WARNING: Some image references may be missing. Expected: {input_image_count}, Got: {expected_output_images}")
        elif input_image_count > 0 and expected_output_images >= input_image_count:
            logger.info(f"✅ SUCCESS: All image references processed! Expected: {input_image_count}, Got: {expected_output_images}")
        
        if input_tags_count > 0 and expected_output_tags == 0:
            logger.error("🚨 CRITICAL ERROR: LLM tags found in input but ZERO in output!")
            logger.error(f"🚨 Expected: {input_tags_count}, Got: {expected_output_tags}")
        elif input_tags_count > 0 and expected_output_tags < input_tags_count:
            logger.warning(f"⚠️  WARNING: Some LLM tags may be missing. Expected: {input_tags_count}, Got: {expected_output_tags}")
        elif input_tags_count > 0 and expected_output_tags >= input_tags_count:
            logger.info(f"✅ SUCCESS: All LLM tags processed! Expected: {input_tags_count}, Got: {expected_output_tags}")
        
        logger.info(f"📋 Final response top-level keys: {list(response.keys())}")
        if "process_s3_key" in response:
            logger.info(f"📋 ✅ CONFIRMED: process_s3_key in final response: {response['process_s3_key']}")
        else:
            logger.error("📋 ❌ MISSING: process_s3_key NOT in final response")
        if "process_bucket" in response:
            logger.info(f"📋 ✅ CONFIRMED: process_bucket in final response: {response['process_bucket']}")
        else:
            logger.error("📋 ❌ MISSING: process_bucket NOT in final response")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error processing content: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "chunks": [],
            "metadata": {
                "total_chunks": 0,
                "text_chunks": 0,
                "image_chunks": 0,
                "tagging_chunks": 0,
                "request_id": context.aws_request_id,
                "error_occurred": True,
                "environment_settings": {
                    "include_image_refs": INCLUDE_IMAGE_REFS,
                    "include_tagging_info": INCLUDE_TAGGING_INFO,
                    "separate_image_chunks": SEPARATE_IMAGE_CHUNKS,
                    "separate_tagging_chunks": os.environ.get("SEPARATE_TAGGING_CHUNKS", "false").lower() == "true"
                }
            }
        }