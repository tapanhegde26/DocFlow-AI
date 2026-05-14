import os, boto3, json
from botocore.exceptions import ClientError

s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "ca-central-1"))

def handle_fetch_content(event):
    """
    POST /review/content
    Body: { "s3_path": "s3://bucket/key" }
    Returns the text content of a process file.
    """
    try:
        body = json.loads(event.get("body", "{}"))
        s3_path = body.get("s3_path")

        if not s3_path or "/" not in s3_path:
            return _response(400, {"error": "Invalid or missing s3_path"})

        bucket, key = s3_path.split("/", 1)

        # Fetch object
        obj = s3.get_object(Bucket=bucket, Key=key)
        content = obj["Body"].read().decode("utf-8")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/plain",
                "Access-Control-Allow-Origin": "*"
            },
            "body": content
        }

    except ClientError as e:
        print("reviewUI:review_fetch.py:handle_fetch_content: S3 Error:", e)
        return _response(500, {"error": f"Failed to read file: {e}"})
    except Exception as e:
        print("reviewUI:review_fetch.py:handle_fetch_content: Unexpected Error:", e)
        return _response(500, {"error": str(e)})

def _response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }

   