import json
from routes.review_audit import handle_review_audit
from routes.review_log import handle_review_log
from routes.review_fetch import handle_fetch_processes
from routes.review_fetch_content import handle_fetch_content
from routes.review_state import handle_process_state_change
from routes.review_signedUrl import handle_signed_url
from routes.review_history import (
    handle_get_review_history,
    handle_get_latest_review,
    handle_create_review,
)


def lambda_handler(event, context):
    try:
        ##### ORIGINAL does not allow testing from Lambda Console
        #path = event.get("rawPath", "")
        #method = event.get("requestContext", {}).get("http", {}).get("method", "")

        ##### DEBUG to test from lambda test in console
        path = event.get("rawPath", "") or event.get("path", "")
        method = (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", ""))

        # Process operations
        if path == "/reviews/processes" and method == "GET":
            return handle_fetch_processes(event)

        elif path == "/reviews/content" and method == "POST":
            return handle_fetch_content(event)

        elif path == "/reviews/state" and method == "POST":
            return handle_process_state_change(event)

        # Review history operations
        elif path == "/reviews/history" and method == "POST":
            return handle_create_review(event)

        elif path.startswith("/reviews/history/latest/") and method == "GET":
            return handle_get_latest_review(event)

        elif path.startswith("/reviews/history/") and method == "GET":
            return handle_get_review_history(event)

        # Audit/Logging
        elif path == "/reviews/audit" and method == "POST":
            return handle_review_audit(event)

        elif path.startswith("/reviews/log") and method == "GET":
            return handle_review_log(event)

        # Signed Urls
        elif path == "/reviews/signed-url" and method == "POST":
            return handle_signed_url(event)

        # Default
        else:
            return {"statusCode": 404, "body": json.dumps({"error": "Route not found"})}

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal server error", "error": str(e)})
        }