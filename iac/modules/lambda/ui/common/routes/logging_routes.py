import json
import os
from common.services.logger import log_to_cloudwatch

APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")

def handle_log(data: dict):
    """
    Expects normalized HTTP API v2 request dict:
    req = { method, path, headers, query, body, raw_event }
    """

    app_name = data.get("app", "unknown-app")
    message = data.get("message", "No message provided")
    level = data.get("level", "INFO")
    context = data.get("context", {})
    log_group = APP_LOG_GROUP

    if not data or not all(k in data for k in ("context", "appName", "level", "message")):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Missing required fields"})
        }

    # ✅ structured logging with optional context
    log_to_cloudwatch(log_group, app_name, message, level=level, **context)

    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": json.dumps({
            "ok": True,
            "app": app_name,
            "level": level,
            "message": message
        })
    }