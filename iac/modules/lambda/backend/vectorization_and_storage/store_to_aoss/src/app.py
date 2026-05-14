import boto3
import os
import json
import logging
from typing import Dict, Any, List, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from urllib.parse import urlparse
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
AOSS_ENDPOINT = os.environ.get("AOSS_ENDPOINT")
AOSS_INDEX = os.environ.get("AOSS_INDEX")
AWS_REGION = os.environ.get("AWS_REGION", "ca-central-1")

if not AOSS_ENDPOINT or not AOSS_INDEX:
    raise ValueError("AOSS_ENDPOINT and AOSS_INDEX environment variables are required")

# Extract hostname from URL
parsed_url = urlparse(AOSS_ENDPOINT)
hostname = parsed_url.netloc

# Initialize clients
s3_client = boto3.client("s3")
credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, AWS_REGION, 'aoss')

client = OpenSearch(
    hosts=[{"host": hostname, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    pool_maxsize=20,
    timeout=30,
    max_retries=3,
    retry_on_timeout=True
)

def extract_vectors_from_s3_data(s3_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract vector data from S3 object, handling different data structures.
    
    Args:
        s3_data: Data loaded from S3
        
    Returns:
        List of vector objects with text and embedding
    """
    vectors = []
    
    # Check if data has the expected structure from embedding Lambda
    if isinstance(s3_data, dict) and "embeddings" in s3_data:
        logger.info("Found structured embedding data")
        embeddings_data = s3_data["embeddings"]
        
        for item in embeddings_data:
            if isinstance(item, dict):
                # Extract text content
                text_content = None
                if "content" in item:
                    text_content = item["content"]
                elif "chunk" in item:
                    text_content = item["chunk"]
                elif "text" in item:
                    text_content = item["text"]
                
                # Extract embedding
                embedding = item.get("embedding")
                
                if text_content and embedding:
                    vector_item = {
                        "text": text_content,
                        "embedding": embedding,
                        "chunk_id": item.get("chunk_id", f"chunk_{len(vectors)}"),
                        "metadata": item.get("metadata", {}),
                        "original_metadata": item.get("original_metadata", {}),
                        "original_llm_tags": item.get("original_llm_tags", []),
                        "original_tag_categories": item.get("original_tag_categories", []),
                        "original_tagging_info": item.get("original_tagging_info", {})
                    }
                    vectors.append(vector_item)
                else:
                    logger.warning(f"Skipping item with missing text or embedding: {list(item.keys())}")
            else:
                logger.warning(f"Unexpected item type in embeddings: {type(item)}")
    
    # Fallback: treat as direct list of vectors
    elif isinstance(s3_data, list):
        logger.info("Found direct list of vectors")
        for i, item in enumerate(s3_data):
            if isinstance(item, dict):
                text_content = item.get("chunk") or item.get("text") or item.get("content")
                embedding = item.get("embedding")
                
                if text_content and embedding:
                    vectors.append({
                        "text": text_content,
                        "embedding": embedding,
                        "chunk_id": item.get("chunk_id", f"chunk_{i}"),
                        "metadata": item.get("metadata", {}),
                        "original_metadata": item.get("original_metadata", {}),
                        "original_llm_tags": item.get("original_llm_tags", []),
                        "original_tag_categories": item.get("original_tag_categories", []),
                        "original_tagging_info": item.get("original_tagging_info", {})
                    })
    
    else:
        logger.error(f"Unexpected S3 data structure. Type: {type(s3_data)}, Keys: {list(s3_data.keys()) if isinstance(s3_data, dict) else 'Not a dict'}")
        raise ValueError(f"Unsupported S3 data structure: {type(s3_data)}")
    
    logger.info(f"Extracted {len(vectors)} vectors from S3 data")
    return vectors

def extract_metadata_from_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metadata from the Step Function event.
    
    Args:
        event: Lambda event from Step Function
        
    Returns:
        Dictionary containing metadata fields
    """
    metadata = {}
    
    # Extract from Payload if it exists (Step Function format)
    payload = event.get("Payload", {})
    
    # Extract process S3 information
    if "process_s3_key" in event:
        metadata["process_s3_key"] = event["process_s3_key"]
    elif "process_s3_key" in payload:
        metadata["process_s3_key"] = payload["process_s3_key"]

    if "process_bucket" in event:
        metadata["process_bucket"] = event["process_bucket"]
    elif "process_bucket" in payload:
        metadata["process_bucket"] = payload["process_bucket"]

    # Extract original metadata if passed through Step Function
    if "original_metadata" in event:
        metadata["original_metadata"] = event["original_metadata"]
    elif "original_metadata" in payload:
        metadata["original_metadata"] = payload["original_metadata"]
    
    if "original_llm_tags" in event:
        metadata["original_llm_tags"] = event["original_llm_tags"]
    elif "original_llm_tags" in payload:
        metadata["original_llm_tags"] = payload["original_llm_tags"]
    
    if "original_tag_categories" in event:
        metadata["original_tag_categories"] = event["original_tag_categories"]
    elif "original_tag_categories" in payload:
        metadata["original_tag_categories"] = payload["original_tag_categories"]
    
    if "original_tagging_info" in event:
        metadata["original_tagging_info"] = event["original_tagging_info"]
    elif "original_tagging_info" in payload:
        metadata["original_tagging_info"] = payload["original_tagging_info"]
    
    # Extract client information from original_metadata
    original_metadata = metadata.get("original_metadata", {})
    
    # Client name from original_metadata
    if "client_name" in original_metadata:
        metadata["client_name"] = original_metadata["client_name"]
    elif "client_name" in event:
        metadata["client_name"] = event["client_name"]
    elif "client_name" in payload:
        metadata["client_name"] = payload["client_name"]
    
    # Source document URL from original_metadata.source_file.original_filename
    source_file = original_metadata.get("source_file", {})
    if "original_filename" in source_file:
        metadata["source_document_url"] = source_file["original_filename"]
    elif "source_document_url" in event:
        metadata["source_document_url"] = event["source_document_url"]
    elif "source_document_url" in payload:
        metadata["source_document_url"] = payload["source_document_url"]
    
    # Provider name - you can set a default or extract from somewhere else
    if "provider_name" in event:
        metadata["provider_name"] = event["provider_name"]
    elif "provider_name" in payload:
        metadata["provider_name"] = payload["provider_name"]
    else:
        metadata["provider_name"] = "Conservice"  # Default value
    
    # Also extract process information that might be useful
    if original_metadata:
        metadata["process_uuid"] = original_metadata.get("process_uuid")
        metadata["process_id"] = original_metadata.get("process_id")
        metadata["process_name"] = original_metadata.get("process_name")
        metadata["created_timestamp"] = original_metadata.get("created_timestamp")
        metadata["processing_info"] = original_metadata.get("processing_info", {})
    
    # Log the extracted process S3 information
    logger.info(f"📋 Extracted process_s3_key: {metadata.get('process_s3_key')}")
    logger.info(f"📋 Extracted process_bucket: {metadata.get('process_bucket')}")
    
    return metadata

def create_index_if_not_exists(index_name: str, embedding_dimension: int = 1024) -> bool:
    """
    Create OpenSearch index if it doesn't exist.
    """
    try:
        if client.indices.exists(index=index_name):
            logger.info(f"Index {index_name} already exists")
            return True
        
        logger.info(f"Creating index {index_name} with dimension {embedding_dimension}")
        
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100
                }
            },
            "mappings": {
                "properties": {
                    "text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "bedrock-knowledge-base-default-vector": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "engine": "faiss",
                            "space_type": "l2",
                            "parameters": {
                                "ef_construction": 512,
                                "m": 16
                            }
                        }
                    },
                    "chunk_id": {
                        "type": "keyword"
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": True
                    },
                    "original_metadata": {
                        "type": "object",
                        "enabled": True
                    },
                    "timestamp": {
                        "type": "date"
                    },
                    "created_date": {
                        "type": "date"
                    },
                    "created_timestamp": {
                        "type": "date"
                    },
                    "client_name": {
                        "type": "keyword"
                    },
                    "provider_name": {
                        "type": "keyword"
                    },
                    "source_document_url": {
                        "type": "keyword",
                        "index": False
                    },
                    "llm_tags": {
                        "type": "keyword"
                    },
                    "process_uuid": {
                        "type": "keyword"
                    },
                    "process_id": {
                        "type": "keyword"
                    },
                    "process_name": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "processing_info": {
                        "type": "object",
                        "enabled": True
                    },
                    "source_file": {
                        "type": "object",
                        "properties": {
                            "s3_key": {
                                "type": "keyword",
                                "index": False
                            },
                            "bucket": {
                                "type": "keyword",
                                "index": False
                            },
                            "process_s3_key":{
                                "type": "keyword",
                                "index": False
                            },
                            "process_bucket": {
                                "type": "keyword",
                                "index": False
                            }
                        }
                    },
                    "AMAZON_BEDROCK_METADATA": {
                        "type": "text",
                        "index": True
                    },
                    "AMAZON_BEDROCK_TEXT_CHUNK": {
                        "type": "text",
                        "index": True
                    }
                }
            }
        }
        
        response = client.indices.create(index=index_name, body=index_body)
        logger.info(f"Successfully created index {index_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create index {index_name}: {str(e)}")
        raise RuntimeError(f"Index creation failed: {str(e)}")


def bulk_index_vectors(vectors: List[Dict[str, Any]], index_name: str, event_metadata: Dict[str, Any], batch_size: int = 50) -> Dict[str, int]:
    """
    Bulk index vectors into OpenSearch without custom document IDs.
    
    Args:
        vectors: List of vector documents to index
        index_name: Target index name
        event_metadata: Metadata extracted from the event
        batch_size: Number of documents to process in each batch
        
    Returns:
        Dictionary with success and failure counts
    """
    total_vectors = len(vectors)
    success_count = 0
    failed_count = 0
    
    logger.info(f"Bulk indexing {total_vectors} vectors in batches of {batch_size}")
    
    for i in range(0, total_vectors, batch_size):
        batch = vectors[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total_vectors + batch_size - 1) // batch_size
        
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} vectors)")
        
        # Prepare bulk request body
        bulk_body = []
        for vector in batch:
            # Add index action without _id (let OpenSearch generate IDs)
            bulk_body.append({
                "index": {
                    "_index": index_name
                }
            })
            
            # Create document with all available metadata
            doc = {
                "text": vector["text"],
                "embedding": vector["embedding"],
                "chunk_id": vector.get("chunk_id"),
                "metadata": vector.get("metadata", {}),
                #"original_metadata": event_metadata.get("original_metadata", {}),
                "original_metadata": {
                    **event_metadata.get("original_metadata", {}),
                    "source_file": {
                        **event_metadata.get("original_metadata", {}).get("source_file", {}),
                        "process_s3_key": event_metadata.get("process_s3_key"),
                        "process_bucket": event_metadata.get("process_bucket")
                    }
                },
                "timestamp": datetime.utcnow().isoformat(),
                "created_date": datetime.utcnow().isoformat(),
                "client_name": event_metadata.get("client_name"),
                "provider_name": event_metadata.get("client_name"),
                "source_document_url": event_metadata.get("source_document_url"),
                "llm_tags": event_metadata.get("original_llm_tags", []),
                # Additional useful fields from your data
                "process_uuid": event_metadata.get("process_uuid"),
                "process_id": event_metadata.get("process_id"),
                "process_name": event_metadata.get("process_name"),
                "created_timestamp": event_metadata.get("created_timestamp"),
                "processing_info": event_metadata.get("processing_info", {})
            }
            bulk_body.append(doc)
        
        try:
            # Execute bulk request
            response = client.bulk(body=bulk_body, index=index_name)
            
            # Process response
            if response.get("errors"):
                batch_success = 0
                batch_failed = 0
                
                for item in response.get("items", []):
                    if "index" in item:
                        if item["index"].get("status") in [200, 201]:
                            batch_success += 1
                        else:
                            batch_failed += 1
                            error_info = item["index"].get("error", {})
                            logger.error(f"Failed to index document: {error_info}")
                
                success_count += batch_success
                failed_count += batch_failed
                logger.warning(f"Batch {batch_num}: {batch_success} successful, {batch_failed} failed")
            else:
                success_count += len(batch)
                logger.info(f"Batch {batch_num}: All {len(batch)} documents indexed successfully")
                
        except Exception as e:
            logger.error(f"Failed to process batch {batch_num}: {str(e)}")
            failed_count += len(batch)
    
    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "total_count": total_vectors
    }

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler to store vectors in OpenSearch.
    
    Args:
        event: Lambda event containing S3 details and metadata
        context: Lambda context
        
    Returns:
        Processing results
    """
    logger.info(f"Lambda started. Request ID: {context.aws_request_id}")
    logger.debug(f"Event: {json.dumps(event, default=str)}")
    
    try:
        # Extract metadata from event
        event_metadata = extract_metadata_from_event(event)
        logger.info(f"Extracted metadata: {json.dumps(event_metadata, default=str)}")
        
        # Extract S3 details from event
        bucket = event.get("output_bucket") or event.get("s3_output_bucket") or event.get("bucket")
        key = event.get("output_key") or event.get("s3_output_key") or event.get("key")
        
        if not bucket or not key:
            error_msg = f"Missing S3 details. Bucket: {bucket}, Key: {key}"
            logger.error(error_msg)
            logger.error(f"Available event keys: {list(event.keys())}")
            raise ValueError(error_msg)
        
        logger.info(f"Loading vectors from s3://{bucket}/{key}")
        
        # Read vectors from S3
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            s3_data = json.loads(response["Body"].read().decode("utf-8"))
            logger.info(f"Successfully loaded S3 data. Type: {type(s3_data)}")
            
        except Exception as e:
            logger.error(f"Failed to load from S3: {str(e)}")
            raise RuntimeError(f"S3 read failed: {str(e)}")
        
        # Extract vectors from S3 data
        vectors = extract_vectors_from_s3_data(s3_data)
        
        if not vectors:
            logger.warning("No vectors found in S3 data")
            return {
                "success": True,
                "message": "No vectors to store",
                "stored": 0,
                "total": 0,
                "request_id": context.aws_request_id
            }
        
        # Determine embedding dimension from first vector
        embedding_dimension = len(vectors[0]["embedding"]) if vectors else 1024
        logger.info(f"Detected embedding dimension: {embedding_dimension}")
        
        # Create index if it doesn't exist
        create_index_if_not_exists(AOSS_INDEX, embedding_dimension)
        
        # Try bulk indexing first, fall back to individual if needed
        try:
            result = bulk_index_vectors(vectors, AOSS_INDEX, event_metadata)
            indexing_method = "bulk"
        except Exception as bulk_error:
            logger.warning(f"Bulk indexing failed: {str(bulk_error)}, trying individual indexing")
            result = individual_index_vectors(vectors, AOSS_INDEX, event_metadata)
            indexing_method = "individual"
        
        # Prepare response
        response = {
            "success": True,
            "stored": result["success_count"],
            "failed": result["failed_count"],
            "total": result["total_count"],
            "index": AOSS_INDEX,
            "indexing_method": indexing_method,
            "source": {
                "bucket": bucket,
                "key": key
            },
            "metadata": {
                "request_id": context.aws_request_id,
                "embedding_dimension": embedding_dimension,
                "event_metadata": event_metadata
            }
        }
        
        logger.info(f"Successfully stored {result['success_count']}/{result['total_count']} vectors using {indexing_method} method")
        return response
        
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "stored": 0,
            "total": 0,
            "request_id": context.aws_request_id
        }

def individual_index_vectors(vectors: List[Dict[str, Any]], index_name: str, event_metadata: Dict[str, Any]) -> Dict[str, int]:
    """
    Index vectors individually (fallback method if bulk indexing fails).
    
    Args:
        vectors: List of vector documents to index
        index_name: Target index name
        event_metadata: Metadata extracted from the event
        
    Returns:
        Dictionary with success and failure counts
    """
    success_count = 0
    failed_count = 0
    
    logger.info(f"Indexing {len(vectors)} vectors individually")
    
    for i, vector in enumerate(vectors):
        try:
            doc = {
                "text": vector["text"],
                "embedding": vector["embedding"],
                "chunk_id": vector.get("chunk_id"),
                "metadata": vector.get("metadata", {}),
                #"original_metadata": vector.get("original_metadata", event_metadata.get("original_metadata", {})),
                "original_metadata": {
                    **vector.get("original_metadata", event_metadata.get("original_metadata", {})),
                    "source_file": {
                        **event_metadata.get("original_metadata", {}).get("source_file", {}),
                        "s3_key": event_metadata.get("process_s3_key"),
                        "bucket": event_metadata.get("process_bucket")
                    }
                },                
                "timestamp": datetime.utcnow().isoformat(),
                "created_date": datetime.utcnow().isoformat(),
                "client_name": event_metadata.get("client_name"),
                #"provider_name": event_metadata.get("provider_name", "Conservice"),
                "provider_name": event_metadata.get("client_name"),
                "source_document_url": event_metadata.get("source_document_url"),
                "llm_tags": vector.get("original_llm_tags", event_metadata.get("original_llm_tags", []))
            }
            
            # Index without specifying document ID
            response = client.index(index=index_name, body=doc)
            success_count += 1
            
            if i % 10 == 0:  # Log progress every 10 documents
                logger.info(f"Indexed {i+1}/{len(vectors)} documents")
                
        except Exception as e:
            logger.error(f"Failed to index vector {i}: {str(e)}")
            failed_count += 1
    
    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "total_count": len(vectors)
    }
