import json
import os
from datetime import datetime, timezone
from common.services.postgres_service import run_query
from common.services.logger import log_to_cloudwatch
from common.services.opensearch_service import find_document_by_type_and_url, update_status


APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")
AUDIT_LOG_GROUP = os.getenv("AUDIT_LOG_GROUP")
APP_NAME = os.getenv("APP_NAME")

def handle_status_routes(data: dict):
    """
    Handles updating the document's status and updated timestampe
    in both PostgreSQL and OpenSearch
    
    Expected payload:
        process_id : in PostgreSQL 
        new_state  : in PostgreSQL and OpenSearch
        context    : user information
    """

    required_keys = ("document_type", "process_url", "process_id", "new_state", "client_name")
    missing_keys = [k for k in required_keys if k not in data]

    if missing_keys:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": f"Missing required fields: {', '.join(missing_keys)}",
                "missing": missing_keys
            })
        }

    new_state_display = data.get("new_state")
    new_state = normalize_status(new_state_display)
    process_id = data.get("process_id")
    user_id = data.get("user_name")
    client_name = data.get("client_name")
    process_url = data.get("process_url")
    document_type = data.get("document_type")

    # Log to CloudWatch - context is empty
    log_to_cloudwatch( APP_LOG_GROUP, APP_NAME, f"Updated process record : user_id: {user_id}, client_name: {client_name}, process_id: {process_id}, process_url: {process_url}, document_type: {document_type}", "info", None)

    # Update status in process table into Postgres
    sql_query = """
        UPDATE processes 
        SET status = %s, updated_at = %s
        WHERE client_id = %s AND process_id = %s
        RETURNING process_id;
    """

    # Update postgresql
    pResult = run_query(APP_LOG_GROUP, sql_query, (
        new_state, 
        datetime.now(timezone.utc).isoformat(),
        client_name,
        process_id
    ))

    # Update OpenSearch
    results = find_document_by_type_and_url(document_type, client_name, process_url)

    if results:
        for hit in results:
            hit_index = hit["_index"]
            hit_id = hit["_id"]

 
            try:
                response = update_status(
                    doc_type = document_type,
                    index_name=hit_index,
                    doc_id=hit_id,
                    new_state=new_state
                )
            except Exception as e:
                print(f"Failed to update {hit["_id"]}: {e}")
    else:
        return {"statusCode": 500, "body": "Did not find any matching documents in OpenSearch"}

    return {"statusCode": 200, "body": json.dumps({"rows_updated": pResult})}


def normalize_status(status: str) -> str:
    """
    Converts a frontend status to the canonical DB format.
    - Converts camel case statuses to lowercase.
    - Maps 'Ready for Review' -> 'review'.
    """
    if not status:
        return status

    if status.strip().lower() == "ready for review":
        return "review"

    return status.strip().lower()