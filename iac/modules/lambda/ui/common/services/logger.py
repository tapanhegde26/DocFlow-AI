import boto3
import json
import logging
import time
import uuid

from datetime import datetime, timezone
from botocore.config import Config

# Configure a custom timeout (e.g., 60 seconds)
config = Config(
    connect_timeout=60,  # Timeout for establishing a connection
    read_timeout=60,     # Timeout for receiving data after connection
    retries={'max_attempts': 10} # Optional: configure retries
)

# Configure root logger (Lambda automatically streams this to CloudWatch)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

logs_client = boto3.client("logs", config=config, region_name="ca-central-1")

session_streams = {}

def generate_lambda_style_stream_name():
    date_prefix = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    random_hex = uuid.uuid4().hex  # 32-character hex string
    return f"{date_prefix}/[$LATEST]{random_hex}"

def get_or_create_stream(log_group: str, app_name: str, user_id: str) -> str:
    """Get or create a CloudWatch log stream for a user session."""
    key = (log_group, user_id) 
    
    if key in session_streams:
        return session_streams[key]

    session_id = uuid.uuid4().hex[:8]  # short random ID
    stream_name = f"{app_name}/{user_id}/{session_id}"

    try:
        logs_client.create_log_stream(
            logGroupName=log_group,
            logStreamName=stream_name
        )
    except logs_client.exceptions.ResourceAlreadyExistsException:
        print(f"[DEBUG] Log stream already exists: {stream_name}")
    except Exception as e:
        print(f"[ERROR] Error creating log stream: {e}")

    session_streams[key] = stream_name
    return stream_name


def log_to_cloudwatch(log_group: str, 
                      app_name: str,
                      message: str, 
                      level: str = "INFO",
                      context: dict = None,
                      **kwargs) -> None:
    """
    Structured logging helper for CloudWatch.

    Args:
        log_group (str): log group to post to
        app_name (str): Name of the app or Lambda (e.g., "review-handler").
        message (str): Human-readable message.
        level (str): Log level ("INFO", "ERROR", "WARNING", "DEBUG").
        kwargs: Extra structured context (e.g., process_id="123", user="alice").
    """

    user_id = "anonymous"
    combined_context = {}
    if context:
        combined_context.update(context)
    if kwargs:
        combined_context.update(kwargs)

    # Pull user_id from the merged context
    user_id = combined_context.get("user_id", "anonymous")

    stream_name = get_or_create_stream(log_group, app_name, user_id)

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app": app_name,
        "level": level.upper(),
        "message": message,
    }

    combined_context = {}
    if context:
        combined_context.update(context)
    if kwargs:
        combined_context.update(kwargs)

    if combined_context:
        log_entry["context"] = combined_context

    serialized = json.dumps(log_entry)

    # Push the event
    logs_client.put_log_events(
        logGroupName=log_group,
        logStreamName=stream_name,
        logEvents=[{
            "timestamp": int(time.time() * 1000),
            "message": serialized
        }]
    )

