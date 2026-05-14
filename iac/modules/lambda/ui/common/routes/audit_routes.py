import json
import os
from datetime import datetime, timezone
from common.services.postgres_service import run_query
from common.services.logger import log_to_cloudwatch

APP_LOG_GROUP    = os.getenv("APP_LOG_GROUP")
AUDIT_LOG_GROUP  = os.getenv("AUDIT_LOG_GROUP")
APP_NAME         = os.getenv("APP_NAME")

def handle_audit(data: dict):
    """
    Writes an audit log entry when a user logs in or performs an auditable action.

    Expected payload:
    {
      "message": "User login"
      "app_name": "xxxxxxx",
      "ip_address": "10.0.0.5",
      "user_agent": "Mozilla/5.0",
      "context": {
        "user_id": "abc123",
        "client_name": "Client blah",
      }
    }
DB Record format;
    
#
#user_audit_log record: 
#  audit_id SERIAL PRIMARY KEY,  -- Auto-incrementing unique ID for each log entry
#  user_id TEXT NOT NULL,  -- Identifier for the user (e.g., email or username)
#  client_id TEXT NOT NULL,  -- Client context the user is associated with
#  app_name TEXT NOT NULL, - remove contstraint to allo adding new apps
#  event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- When the event was recorded
#  ip_address TEXT,  -- Optional: IP address from which the login originated
#  user_agent TEXT,  -- Optional: Device or browser info
#  message TEXT -- Optional: message
    """

    # Validate input
    required_keys = ("context", "appName", "level", "message")
    missing_keys = [k for k in required_keys if k not in data]

    if missing_keys:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": f"Missing required fields: {', '.join(missing_keys)}",
                "missing": missing_keys
            })
        }


    app_name = data.get("appName", "unknown-app")
    message = data.get("message", "No message provided")
    level = data.get("level", "INFO")
    ip = data.get("source_ip")
    user_agent = data.get("user_agent")
    context = data.get("context")
    user_id = context["user_id"]
    client_id = context["client_name"]

    # Log to CloudWatch
    log_to_cloudwatch( APP_LOG_GROUP, APP_NAME, message, level, **context)

    # Insert into Postgres
    query = """
        INSERT INTO user_audit_log (user_id, client_id, app_name, ip_address, user_agent, message, event_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    run_query(APP_LOG_GROUP, query, (
        user_id,
        client_id,
        app_name,
        ip,
        user_agent,
        message,
        datetime.now(timezone.utc).isoformat()
    ))

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Audit log entry created successfully"})
    }