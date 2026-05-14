import boto3
import os
import json
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Union
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize AWS clients
bedrock_client = boto3.client("bedrock-runtime")
s3_client = boto3.client("s3")

# Configuration
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.titan-embed-text-v2:0")
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", "8000"))  # Titan embed limit

def validate_and_truncate_text(text: str) -> str:
    """
    Validate and truncate text to fit within model limits.
    
    Args:
        text: Input text to validate
        
    Returns:
        Validated and potentially truncated text
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected string, got {type(text)}")
    
    if len(text) == 0:
        raise ValueError("Text cannot be empty")
    
    # Truncate if too long
    if len(text) > MAX_TEXT_LENGTH:
        logger.warning(f"Text length {len(text)} exceeds limit {MAX_TEXT_LENGTH}, truncating")
        text = text[:MAX_TEXT_LENGTH]
    
    return text.strip()

def get_embedding(text: str) -> List[float]:
    """
    Generate embedding for the given text using Amazon Bedrock.
    
    Args:
        text: Input text to embed
        
    Returns:
        List of float values representing the embedding
        
    Raises:
        RuntimeError: If embedding generation fails
    """
    try:
        # Validate and prepare text
        validated_text = validate_and_truncate_text(text)
        
        
        # Prepare request body
        body = json.dumps({
            "inputText": validated_text,
            "dimensions": 1024,  # Optional: specify dimensions for Titan v2
            "normalize": True    # Optional: normalize the embedding
        })
        
        # Invoke Bedrock model
        response = bedrock_client.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        
        # Parse response
        response_body = json.loads(response["body"].read())
        embedding = response_body.get("embedding")
        
        if not embedding:
            raise RuntimeError("No embedding returned from Bedrock")
        
        logger.info(f"Successfully generated embedding with {len(embedding)} dimensions")
        return embedding
        
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Bedrock client error: {str(e)}")
        raise RuntimeError(f"Failed to get embedding from Bedrock: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Bedrock response: {str(e)}")
        raise RuntimeError(f"Invalid response from Bedrock: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error generating embedding: {str(e)}", exc_info=True)
        raise RuntimeError(f"Embedding generation failed: {str(e)}")

def extract_chunk_content(chunk: Union[str, Dict[str, Any]]) -> str:
    """
    Extract text content from chunk object or return string as-is.
    
    Args:
        chunk: Chunk data (string or dict with content field)
        
    Returns:
        Text content to embed
    """
    if isinstance(chunk, str):
        return chunk
    elif isinstance(chunk, dict):
        if "content" in chunk:
            return chunk["content"]
        else:
            logger.warning(f"Chunk dict missing 'content' field. Available keys: {list(chunk.keys())}")
            # Try to use the chunk as JSON string
            return json.dumps(chunk)
    else:
        logger.warning(f"Unexpected chunk type: {type(chunk)}, converting to string")
        return str(chunk)

def save_embeddings_to_s3(vectors: List[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
    """
    Save embeddings and metadata to S3.
    
    Args:
        vectors: List of embedding vectors with metadata
        metadata: Additional metadata about the embedding process
        
    Returns:
        S3 key where the data was saved
    """
    try:
        # Generate unique output key with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_key = f"embeddings/{timestamp}_{uuid.uuid4().hex[:8]}.json"
        
        # Prepare output data
        output_data = {
            "embeddings": vectors,
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "model_id": MODEL_ID
        }
        
        # Save to S3
        logger.info(f"Saving {len(vectors)} embeddings to s3://{OUTPUT_BUCKET}/{output_key}")
        
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=json.dumps(output_data, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
            Metadata={
                "embedding-count": str(len(vectors)),
                "model-id": MODEL_ID,
                "created-by": "embedding-lambda"
            }
        )
        
        logger.info(f"Successfully saved embeddings to S3: {output_key}")
        return output_key
        
    except Exception as e:
        logger.error(f"Failed to save embeddings to S3: {str(e)}", exc_info=True)
        raise RuntimeError(f"S3 save failed: {str(e)}")

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Generate embeddings for text chunks using Amazon Bedrock.
    
    Args:
        event: Input event containing chunks to embed
        context: Lambda context
        
    Returns:
        Dictionary with S3 location and metadata
    """
    logger.info(f"Lambda invocation started. Request ID: {context.aws_request_id}")
    logger.debug(f"Event keys: {list(event.keys())}")
    
    try:
        # Print the complete event for debugging
        print("======= COMPLETE EVENT ====")
        print(json.dumps(event, indent=2, default=str))
        
        # Extract chunks from event - handle both direct chunks and nested payload
        chunks = None
        original_event_data = {}
        original_metadata = None
        original_llm_tags = None
        original_tag_categories = None
        original_tagging_info = None
        
        
        if "chunks" in event:
            # Direct chunks in event
            chunks = event["chunks"]
            original_event_data = {k: v for k, v in event.items() if k != "chunks"}
            original_metadata = event.get("original_metadata")
            original_llm_tags = event.get("original_llm_tags")
            original_tag_categories = event.get("original_tag_categories")
            original_tagging_info = event.get("original_tagging_info")
        elif "Payload" in event and "chunks" in event["Payload"]:
            # Chunks nested in Payload (from Step Functions)
            payload = event["Payload"]
            chunks = payload["chunks"]
            original_event_data = {k: v for k, v in payload.items() if k != "chunks"}
            original_metadata = payload.get("original_metadata")
            original_llm_tags = payload.get("original_llm_tags")
            original_tag_categories = payload.get("original_tag_categories")
            original_tagging_info = payload.get("original_tagging_info")
            # Also preserve top-level event data
            original_event_data.update({k: v for k, v in event.items() if k != "Payload"})
        else:
            logger.error("No chunks found in event")
            raise ValueError("Missing required field: chunks")
        
        if not chunks:
            logger.error("Chunks is empty or None")
            raise ValueError("Missing required field: chunks")
            
        if not isinstance(chunks, list):
            logger.error(f"Expected chunks to be a list, got {type(chunks)}")
            raise ValueError(f"chunks must be a list, got {type(chunks)}")
            
        if len(chunks) == 0:
            logger.warning("No chunks provided for embedding")
            return {
                "success": True,
                "output_bucket": OUTPUT_BUCKET,
                "output_key": None,
                "embedding_count": 0,
                "message": "No chunks to process",
                "original_event_data": original_event_data,
                "original_metadata": original_metadata,
                "original_llm_tags" : original_llm_tags,
                "original_tag_categories" : original_tag_categories,
                "original_tagging_info" : original_tagging_info
            }
            
        logger.info(f"Processing {len(chunks)} chunks for embedding generation")
        if original_metadata:
            logger.info(f"Extracted original_metadata for process: {original_metadata.get('process_name', 'Unknown')}")
            logger.info(f"Process UUID: {original_metadata.get('process_uuid', 'Unknown')}")
            logger.info(f"Client: {original_metadata.get('client_name', 'Unknown')}")
        else:
            logger.warning("No original_metadata found in event")
            
        logger.info(f"Processing {len(chunks)} chunks for embedding generation")
        
        # Process each chunk
        vectors = []
        successful_embeddings = 0
        failed_embeddings = 0
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            
            try:
                # Extract text content from chunk
                text_content = extract_chunk_content(chunk)
                
                # Generate embedding
                embedding = get_embedding(text_content)
                
                # Prepare vector data
                vector_data = {
                    "chunk_id": chunk.get("chunk_id", f"chunk_{i}") if isinstance(chunk, dict) else f"chunk_{i}",
                    "content": text_content,
                    "embedding": embedding,
                    "metadata": {
                        "chunk_index": i,
                        "embedding_dimensions": len(embedding),
                        "text_length": len(text_content),
                        "model_id": MODEL_ID,
                        "process_uuid": original_metadata.get("process_uuid") if original_metadata else None,
                        "process_name": original_metadata.get("process_name") if original_metadata else None,
                        "client_name": original_metadata.get("client_name") if original_metadata else None
                    }
                }
                
                # Add original chunk metadata if present
                if isinstance(chunk, dict) and "metadata" in chunk:
                    vector_data["original_metadata"] = chunk["metadata"]
                
                vectors.append(vector_data)
                successful_embeddings += 1
                
                logger.info(f"Successfully generated embedding for chunk {i+1}")
                
            except Exception as e:
                logger.error(f"Failed to generate embedding for chunk {i+1}: {str(e)}")
                failed_embeddings += 1
                # Continue processing other chunks
                continue
        
        if successful_embeddings == 0:
            raise RuntimeError("Failed to generate embeddings for any chunks")
        
        # Prepare metadata with ALL original data preserved
        processing_metadata = {
            "total_chunks": len(chunks),
            "successful_embeddings": successful_embeddings,
            "failed_embeddings": failed_embeddings,
            "model_id": MODEL_ID,
            "request_id": context.aws_request_id,
            # Preserve all original event data
            "original_complete_payload": original_event_data,
            "original_metadata": original_metadata,
            "original_llm_tags": original_llm_tags,
            "original_tag_categories": original_tag_categories,
            "original_tagging_info": original_tagging_info
        }
        
        # Save embeddings to S3
        output_key = save_embeddings_to_s3(vectors, processing_metadata)
        
        # Prepare response with all original data preserved
        response = {
            "success": True,
            "output_bucket": OUTPUT_BUCKET,
            "output_key": output_key,
            "embedding_count": successful_embeddings,
            "failed_count": failed_embeddings,
            "metadata": processing_metadata,
            "original_metadata": original_metadata,
            "original_llm_tags": original_llm_tags,
            "original_tag_categories": original_tag_categories,
            "original_tagging_info": original_tagging_info,
            # Include all original data in the response
            **{k: v for k, v in original_event_data.items() 
            if k not in ["original_metadata", "original_llm_tags", "original_tag_categories", "original_tagging_info"]}
        }
        
        logger.info(f"Successfully processed {successful_embeddings}/{len(chunks)} chunks")
        return response
        
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "output_bucket": OUTPUT_BUCKET,
            "output_key": None,
            "embedding_count": 0,
            "request_id": context.aws_request_id
        }
