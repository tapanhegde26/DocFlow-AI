from datetime import datetime, timezone
from common.services.postgres_service import fetch_query, run_query
from common.services.logger import log_to_cloudwatch
import os

APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")
APP_NAME = os.getenv("APP_NAME")

def get_processes_by_client(client_name: str):
    """
    Fetch all processes/documents for a given client_name.
    """

    query = """
        SELECT *
        FROM processes
        WHERE client_id = %s
    """

    rows = fetch_query(query, params=(client_name,))

    log_to_cloudwatch(
        APP_LOG_GROUP,
        APP_NAME,
        f"Fetched processes for client:{client_name} and received {len(rows)} rows from database",
        "info",
        None
    )
    return rows

def get_process_by_id(process_id: str):
    """
    Fetch a single process/document by process_id.
    """
    query = """
        SELECT *
        FROM processes
        WHERE process_id = %s
        LIMIT 1
    """
    rows = fetch_query(query, (process_id,))
    if not rows:
        log_to_cloudwatch(
            APP_NAME,
            "Process not found",
            process_id=process_id,
            level="WARNING",
            event_time=datetime.now(timezone.utc).isoformat()
        )
        return None

    log_to_cloudwatch(
        APP_NAME,
        "Fetched process by ID",
        process_id=process_id,
        event_time=datetime.now(timezone.utc).isoformat()
    )
    return rows[0]

def update_process_url(process_id: str, new_url: str):
    """
    Update the process_url of a process.
    """
    query = """
        UPDATE processes
        SET process_url = %s, updated_at = CURRENT_TIMESTAMP
        WHERE process_id = %s
    """
    affected = run_query(query, (new_url, process_id))

    log_to_cloudwatch(
        APP_NAME,
        "Updated process URL",
        process_id=process_id,
        new_url=new_url,
        affected=affected,
        event_time=datetime.now(timezone.utc).isoformat()
    )
    return affected

def insert_process(process: dict):
    """
    Insert a new process/document into the database.
    Expects keys: client_name, title, s3_key, file_hash, document_type, etc.
    """
    query = """
        INSERT INTO processes (
            process_id, client_name, provider_id, source_sop_url, title,
            domain, subdomain, llm_tags, status, file_hash, s3_key,
            version, supersedes_process_id, document_type, mermaid
        ) VALUES (
            %(process_id)s, %(client_name)s, %(provider_id)s, %(source_sop_url)s, %(title)s,
            %(domain)s, %(subdomain)s, %(llm_tags)s, %(status)s, %(file_hash)s, %(s3_key)s,
            %(version)s, %(supersedes_process_id)s, %(document_type)s, %(mermaid)s
        )
    """
    affected = run_query(query, process)

    log_to_cloudwatch(
        APP_NAME,
        "Inserted new process",
        process_id=process.get("process_id"),
        client_name=process.get("client_name"),
        affected=affected,
        event_time=datetime.now(timezone.utc).isoformat()
    )
    return affected

def delete_process(process_id: str):
    """
    Delete a process by ID.
    ***NOTE - Not exposed in UI — reserved for admin use, cleanup, or test automation.
    """
    query = "DELETE FROM processes WHERE process_id = %s"
    affected = run_query(query, (process_id,))

    log_to_cloudwatch(
        APP_NAME,
        "Deleted process",
        process_id=process_id,
        affected=affected,
        event_time=datetime.now(timezone.utc).isoformat()
    )
    return affected