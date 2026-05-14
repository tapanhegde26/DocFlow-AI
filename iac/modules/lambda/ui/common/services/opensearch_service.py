import os
import json
import requests
import boto3
from requests_aws4auth import AWS4Auth
from datetime import datetime, timezone

from common.utils.config import get_secret
from common.services.logger import log_to_cloudwatch

# Environment setup
APP_LOG_GROUP = os.getenv("APP_LOG_GROUP")
AUDIT_LOG_GROUP = os.getenv("AUDIT_LOG_GROUP")
APP_NAME = os.getenv("APP_NAME")

REGION = os.getenv("AWS_REGION", "ca-central-1")
SERVICE = "aoss"

# Two endpoints for different document types
PROCESS_OPENSEARCH_ENDPOINT = os.getenv("PROCESS_OPENSEARCH_ENDPOINT")
DOCUMENT_OPENSEARCH_ENDPOINT = os.getenv("DOCUMENT_OPENSEARCH_ENDPOINT")

# Default index names (optional — can be overridden via event or parameter)
PROCESS_INDEX_NAME = os.getenv("PROCESS_INDEX_NAME")
DOCUMENT_INDEX_NAME = os.getenv("DOCUMENT_INDEX_NAME")

# Prepare AWS SigV4 authentication
session = boto3.Session()
credentials = session.get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    REGION,
    SERVICE,
    session_token=credentials.token
)


def get_endpoint_and_index(doc_type: str):
    """
    Determine which endpoint and index to use based on document type.
    """
    if not doc_type:
        raise ValueError("Document type (process/document) is required")

    if doc_type.lower() == "process":
        endpoint = PROCESS_OPENSEARCH_ENDPOINT
        index = PROCESS_INDEX_NAME
    elif doc_type.lower() == "document":
        endpoint = DOCUMENT_OPENSEARCH_ENDPOINT
        index = DOCUMENT_INDEX_NAME
    else:
        raise ValueError(f"Unsupported document type: {doc_type}")

    if not endpoint:
        raise ValueError(f"Missing OpenSearch endpoint for document type '{doc_type}'")

    return endpoint, index

def get_full_url(doc_type: str, path: str) -> str:
    """Construct full OpenSearch endpoint URL with correct index path."""
    endpoint, index = get_endpoint_and_index(doc_type)
    return f"{endpoint}/{index}/{path.strip('/')}"

def search_documents(doc_type: str, query: dict, log_context: dict = None):
    """Perform a search query in the correct OpenSearch collection."""

    url = get_full_url(doc_type, "_search")

    try:
        response = requests.get(
            url,
            auth=awsauth,
            headers={"Content-Type": "application/json"},
            data=json.dumps(query)
        )
        response.raise_for_status()

        results = response.json()
        hits = results.get("hits", {}).get("hits", [])

        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"Executed OpenSearch query for doc_type:{doc_type} and query: {query} and received {len(hits)} hits",
            "info",
            **(log_context or {})
        )

        return hits

    except Exception as e:
        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"OpenSearch query failed doc_type:{doc_type} and query: {query} : {str(e)}",
            "error",
            **(log_context or {})
        )
        raise

def update_document(doc_type: str, doc_id: str, document: dict, upsert: bool = True, log_context: dict = None):
    """Update (or upsert) a document in the correct OpenSearch collection."""
    
    url = get_full_url(doc_type, f"_update/{doc_id}")
    body = { "doc": document }

    try:
        response = requests.post(
            url,
            auth=awsauth,
            headers={"Content-Type": "application/json"},
            data=json.dumps(body)
        )

        response.raise_for_status()
        json_response = response.json()

        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"Successfully updated OpenSearch {doc_type} document for doc_id={doc_id} with document:{document},",
            "info",
            **(log_context or {})
        )

        return response.json()

    except requests.HTTPError as http_err:
        error_detail = http_err.response.text if http_err.response else str(http_err)

        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"OpenSearch update failed for doc_type={doc_type}, doc_id={doc_id}, error={error_detail}",
            "error",
            **(log_context or {})
        )
        raise

    except Exception as e:
        if isinstance(e, requests.HTTPError) and e.response is not None:
            err_text = e.response.text
        else:
            err_text = str(e)

        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"OpenSearch update failed doc_type: {doc_type} for doc_id={doc_id} with document:{document}, error_details: {err_text}",
            "error",
            **(log_context or {})
        )
        raise

def bulk_update(doc_type: str, documents: list, log_context: dict = None):
    """Perform a bulk update operation in the correct OpenSearch collection."""
    url = get_full_url(doc_type, "_bulk")
    event_time = datetime.now(timezone.utc).isoformat()

    bulk_payload = ""
    for doc_id, data in documents:
        bulk_payload += json.dumps({"update": {"_id": doc_id}}) + "\n"
        bulk_payload += json.dumps({"doc": data, "doc_as_upsert": True}) + "\n"

    try:
        response = requests.post(
            url,
            auth=awsauth,
            headers={"Content-Type": "application/x-ndjson"},
            data=bulk_payload
        )
        response.raise_for_status()

        results = response.json()

        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"Executed OpenSearch bulk update ({doc_type})",
            "info",
            event_time=event_time,
            doc_type=doc_type,
            document_count=len(documents),
            errors=results.get("errors", False),
            **(log_context or {})
        )

        return results

    except Exception as e:
        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"OpenSearch bulk update failed ({doc_type}): {str(e)}",
            "error",
            event_time=event_time,
            doc_type=doc_type,
            document_count=len(documents),
            **(log_context or {})
        )
        raise

def delete_document(doc_type: str, doc_id: str, log_context: dict = None):
    """
    Delete a document from the specified OpenSearch collection.

    :param doc_type: To generate correct full url
    :param doc_id: Document ID to delete
    :param log_context: Optional logging context for CloudWatch
    """
    print(f"reviewUI: common: opensearch_service.py: delete_document: received data - doc_type: {doc_type}, doc_id: {doc_id}")

    url = get_full_url(doc_type, f"_doc/{doc_id}")

    print(f"reviewUI: common: opensearch_service.py: delete_document: url: {url}")

    try:
        response = requests.delete(
            url,
            auth=awsauth,
            headers={"Content-Type": "application/json"}
        )

        response.raise_for_status()

        json_response = response.json()
        print(f"reviewUI: common: opensearch_service.py: delete_document: response: {json_response}")

        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"Successfully deleted OpenSearch {doc_type} document with doc_id={doc_id}",
            "info",
            **(log_context or {})
        )

        return json_response

    except requests.HTTPError as http_err:
        error_detail = http_err.response.text if http_err.response else str(http_err)
        print(f"reviewUI: common: opensearch_service.py: delete_document: HTTPError: {error_detail}")

        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"OpenSearch delete failed for doc_type={doc_type}, doc_id={doc_id}, error={error_detail}",
            "error",
            **(log_context or {})
        )
        raise

    except Exception as e:
        err_text = e.response.text if isinstance(e, requests.HTTPError) and e.response else str(e)

        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"OpenSearch delete failed for doc_type={doc_type}, doc_id={doc_id}, error_details: {err_text}",
            "error",
            **(log_context or {})
        )
        raise
    
def update_status(doc_type: str, index_name: str, doc_id: str, new_state: str, extra_fields: dict = None, log_context: dict = None):
    """
    Update only the 'state' field of a document in the appropriate OpenSearch collection.
    Optionally include other fields like timestamps or audit data.
    """

    document_update =  {
        "original_metadata": {
            "document_status": new_state
        }
    }
    if extra_fields:
        document_update.update(extra_fields)

    try:
        result = update_document(doc_type, doc_id, document_update, upsert=True, log_context=log_context)
        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"Updated status on index: {index_name} for doc_id:{doc_id} with status:{new_state}",
            "info",
            **(log_context or {})
        )

        return result

    except Exception as e:
        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"OpenSearch status update failed on index: {index_name} for doc_id={doc_id} with status:{new_state}: {str(e)}",
            "error",
            **(log_context or {})
        )
        raise

def find_document_by_type_and_url(document_type: str, client_name: str, process_url: str, log_context: dict = None):
    """
    Find a document in OpenSearch by document_type and process_url.
    Returns a list of matching documents (usually one).
    """
    print(f"reviewUI: common: opensearch_service.py: find_document_by_type_and_url: received data - document_type: {document_type}, process_url: {process_url}")

    if (document_type == 'process'):
        print(f"reviewUI: common: opensearch_service.py: handling a process")
        parsed = parse_s3_path(process_url)
        print(f"reviewUI: common: opensearch_service.py: find_document_by_type_and_url: parsed: {parsed}")
        query = {
            "_source": [
                "original_metadata.document_status"
            ],
            "size": 10000,
            "query": {
                "bool": {
                    "must": [
                        { "term": { "original_metadata.source_file.process_bucket.keyword": parsed["s3_bucket"] } },
                        { "term": { "original_metadata.source_file.process_s3_key.keyword": parsed["s3_key"] } },
                        { "term": { "original_metadata.client_name.keyword": client_name } }
                    ]
                }
            }
        }
        print(f"reviewUI: common: opensearch_service.py: find_document_by_type_and_url: inside process document type - query: {query}")

    elif (document_type == 'document'):
        print(f"reviewUI: common: opensearch_service.py: handling a document")
        parsed = parse_s3_path(process_url)
        print(f"reviewUI: common: opensearch_service.py: find_document_by_type_and_url: parsed: {parsed}")

        query = {
            "_source": [
                "original_metadata.document_status"
            ],
            "size": 10000,
           "query": {
                "bool": {
                    "must": [
                        { "term": { "original_metadata.source_file.s3_bucket.keyword": parsed["s3_bucket"] } },
                        { "term": { "original_metadata.source_file.s3_key.keyword": parsed["s3_key"] } },
                        { "term": { "original_metadata.client_name.keyword": client_name } }
                    ]
                }
            } 
        }
        print(f"reviewUI: common: opensearch_service.py: find_document_by_type_and_url: inside non-process document type - query: {query}")


    try:
        print(f"reviewUI: common: opensearch_service.py: find_document_by_type_and_url: calling opensearch search documents")
        hits = search_documents(document_type, query, log_context)
        print(f"reviewUI: common: opensearch_service.py: find_document_by_type_and_url: received {hits} after searching openasearch")

        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"Found {len(hits)} document_type={document_type}, process_url={process_url} and received {len(hits)} hits",
            "info",
            **(log_context or {})
        )
        return hits

    except Exception as e:
        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"Error searching document_type={document_type}, url={process_url}: {str(e)}",
            "error",
            **(log_context or {})
        )
        raise

def parse_s3_path(full_path: str) -> dict:
    """
    Splits a full S3 path into bucket and key parts.

    Example:
        full_path = "rev-tsh-industries-text-extraction/non_distinct_processes/Conservice One/20251021_193658_a79e3246_unknown_file_non_distinct_processes.json"

    Returns:
        {
            "s3_bucket": "rev-tsh-industries-text-extraction",
            "s3_key": "non_distinct_processes/Conservice One/20251021_193658_a79e3246_unknown_file_non_distinct_processes.json"
        }
    """
    print(f"reviewUI: common: opensearch_service.py: parse_s3_path: received full_path: {full_path}")
    if not full_path or not isinstance(full_path, str):
        return {"s3_bucket": "", "s3_key": ""}

    # Handle full S3 URLs like s3://bucket/key
    if full_path.startswith("s3://"):
        print(f"reviewUI: common: opensearch_service.py: parse_s3_path: replacing s3:// in string")
        full_path = full_path.replace("s3://", "", 1)

    parts = full_path.split("/", 1)  # split only on the first slash
    print(f"reviewUI: common: opensearch_service.py: parse_s3_path: parts: {parts}")

    if len(parts) == 1:
        print(f"reviewUI: common: opensearch_service.py: parse_s3_path: received {len(parts)} parts")

        # Only bucket, no key
        return {"s3_bucket": parts[0], "s3_key": ""}

    s3_bucket, s3_key = parts[0], parts[1]
    print(f"reviewUI: common: opensearch_service.py: parse_s3_path: returning s3_bucket: {s3_bucket} and s3_key: {s3_key}")

    return {"s3_bucket": s3_bucket, "s3_key": s3_key}