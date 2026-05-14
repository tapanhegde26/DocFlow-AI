import boto3
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse
from common.services.logger import log_to_cloudwatch

APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")
APP_NAME = os.getenv("APP_NAME")

s3 = boto3.client("s3")
region = os.environ.get("AWS_REGION", "ca-central-1")

def write_s3_file(file_key: str, content: str, bucket: str = None, content_type: str = "application/json"):
    """
    Write (or overwrite) content into an S3 file.

    :param file_key: Full path (e.g. 'bucket/key' or 's3://bucket/key')
    :param content: Content to write (str or dict)
    :param bucket: Optional bucket name (overrides file_key bucket)
    :param content_type: MIME type, default = application/json
    """
    print(f"reviewUI:common:s3_service.py:write_s3_file: file_key: {file_key}, content: will not be printed")

    if file_key.startswith("s3://"):
        bucket, file_key = _parse_s3_uri(file_key)
    elif not bucket:
        bucket, file_key = _split_key(file_key)

    print(f"reviewUI:common:s3_service.py:write_s3_file: file_key: {file_key},  bucket: {bucket}")

    # Handle dict (assume JSON)
    if isinstance(content, dict):
        content = json.dumps(content, indent=2)

    try:
        res = s3.put_object(
            Bucket=bucket, 
            Key=file_key, 
            Body=content.encode("utf-8"),
            ContentType=content_type
        )
        print(f"reviewUI:common:s3_service.py:write_s3_file: res: {res}")

        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"Wrote file to S3 bucket:{bucket},file_key:{file_key} file_size:{len(content)}",
            "info",
            None
        )
        return res
    except Exception as e:
        log_to_cloudwatch(
            APP_NAME, 
            f"Error writing to S3 bucket={bucket}, file_key={file_key}, error={str(e)}", 
            "ERROR",
            None)
        raise

def _split_key(full_key: str):
    parts = full_key.split("/", 1)
    if len(parts) != 2:
        raise ValueError("Invalid file_key format, must be bucket/path")
    return parts[0], parts[1]

def _parse_s3_uri(s3_uri: str):
    parsed = urlparse(s3_uri)
    if parsed.scheme != "s3":
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    return parsed.netloc, parsed.path.lstrip("/")