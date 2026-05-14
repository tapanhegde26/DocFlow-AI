import json
import os
from common.services.review_service import (
    insert_review,
    get_reviews_by_process,
    get_latest_review,
)
from common.services.logger import log_to_cloudwatch

APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")
APP_NAME = os.getenv("APP_NAME")

def handle_insert_review(data: dict):
    """
    Insert a new review record.
    Expects payload:
    {
        "process_id": "xxxxxxxx",
        "reviewer": "abc123",
        "previous_status": "draft",
        "new_status": "approved",
        "comments": "blah de blah blah",
        "process_diff": xxxxxxxxx,
        "flags": {"Missing steps"},
    """
    
    
    # Validate input
    body = data.get("body") or {}
    try:
        insert_review(body)
        return {
            "statusCode": 200,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"message": "Review entry created successfully"})
        }
    except Exception as e:
        log_to_cloudwatch( APP_LOG_GROUP, APP_NAME, f'Failed to insert review: {e}', **context)
        return {
            "statusCode": 500,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }


def handle_get_reviews(data: dict):
    """
    Fetch all reviews for a process.
    Query params: ?processId=uuid
    """
    process_id = (data.get("query") or {}).get("processId")
    context = data.get("context")

    if not process_id:
        return {
            "statusCode": 400,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"error": "Missing processId"})
        }

    try:
        rows = get_reviews_by_process(process_id)
        return {
            "statusCode": 200,
            "headers": {"content-type": "application/json"},
            "body": json.dumps(rows, default=str)
        }
    except Exception as e:
        log_to_cloudwatch(APP_LOG_GROUP, APP_NAME, f'Failed to fetch reviews: {str(e)}', **context)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def handle_get_latest_review(data: dict):
    """
    Fetch the most recent review entry for a process.
    Query params: ?processId=uuid
    """
    process_id = (data.get("query") or {}).get("processId")
    context = data.get("context")

    if not process_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing processId"})
        }

    try:
        latest = get_latest_review(process_id)
        return {
            "statusCode": 200,
            "body": json.dumps(latest, default=str)
        }
    except Exception as e:
        log_to_cloudwatch( APP_LOG_GROUP, APP_NAME, f'Failed to fetch latest review: {str(e)}', **context)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }