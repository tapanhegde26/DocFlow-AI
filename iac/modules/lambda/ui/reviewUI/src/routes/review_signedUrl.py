import os, json, boto3
from botocore.exceptions import ClientError

s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "ca-central-1"))

def handle_signed_url(event):
    """
    POST /reviews/signed-url
    Body: { "process_url": "bucket-name/path/to/file.json" }
    Returns: { "signedUrl": "<temporary_s3_link>" }
    """
    try:
        body = json.loads(event.get("body", "{}"))
        process_url = body.get("process_url")

        if not process_url:
            return _response(400, {"error": "Missing process_url"})

        s3_path = process_url.replace("s3://", "")
        bucket_name, key = s3_path.split("/", 1)

        signed_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": key, "ResponseContentDisposition": "inline"},
            ExpiresIn=300  # 5 minutes
        )

        return _response(200, {"signedUrl": signed_url})

    except ClientError as e:
        return _response(500, {"error": "Failed to generate pre-signed URL"})
    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }