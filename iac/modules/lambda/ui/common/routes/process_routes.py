import json
import os
from datetime import datetime, timezone

from common.services.process_service import get_processes_by_client, get_process_by_id
from common.services.logger import log_to_cloudwatch

APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")
APP_NAME = os.getenv("APP_NAME")

def handle_process_routes(data: dict):
    """
    Handles process retrieval from Postgres:
    - {"query": {"client_name": "123"}} → list processes for a client
    - {"query": {"process_id": "abc"}} → details of a single process
    """
    query_params = data.get("query") or {}

    if "client_name" in query_params:
        client_name = query_params.get("client_name")

    if "process_id" in query_params:
        process_id = query_params.get("process_id")

    context = data.get("context")

    try:
        if client_name:
            results = get_processes_by_client(client_name)
            log_to_cloudwatch(APP_LOG_GROUP, APP_NAME, f'Fetched processes by client, client_name: {client_name}, count={len(results)}', **context)
            return {"statusCode": 200, "body": json.dumps(results, default=str)}

        elif process_id:
            process = get_process_by_id(process_id)
            if not process:
                return {"statusCode": 404,
                        "body": json.dumps({"error": "Process not found"})}
            log_to_cloudwatch(APP_LOG_GROUP, APP_NAME, f'Fetched process by ID = {process_id}', **context)
            return {"statusCode": 200, "body": json.dumps(process, default=str)}

        else:
            return {"statusCode": 400,
                    "body": json.dumps({"error": "Missing required query parameter"})}

    except Exception as e:
        log_to_cloudwatch(APP_LOG_GROUP, APP_NAME, f'Error in handle_process_routes - error: str(e)',
                          level="ERROR", **context)
        return {"statusCode": 500,
                "body": json.dumps({"error": "Internal server error", "details": str(e)})}