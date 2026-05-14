
import json
from routes.chat_query import handle_chat_query
from routes.chat_feedback import handle_chat_feedback
from routes.chat_audit import handle_chat_audit
from routes.chat_log import handle_chat_log
from routes.chat_signedUrl import handle_signed_url

def lambda_handler(event, context):
    try:
        ##### ORIGINAL does not allow testing from Lambda Console
        #path = event.get("rawPath", "")
        #method = event.get("requestContext", {}).get("http", {}).get("method", "")

        ##### DEBUG to test from lambda test in console
        path = event.get("rawPath", "") or event.get("path", "")
        method = (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", ""))

        if path == "/chat/query" and method == "POST":
            return handle_chat_query(event)
        elif path == "/chat/feedback" and method == "PUT":
            return handle_chat_feedback(event)
        elif path == "/chat/audit" and method == "POST":
            return handle_chat_audit(event)
        elif path == "/chat/log" and method == "POST":
            return handle_chat_log(event)

        # Signed Urls
        elif path == "/chat/signed-url" and method == "POST":
            return handle_signed_url(event)

        else:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Route not found"})
            }

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Internal server error",
                "error": str(e)
            })
        }