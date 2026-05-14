import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sfn = boto3.client('stepfunctions')
STATE_MACHINE_ARN = os.environ['STEP_FUNCTION_ARN']

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    for record in event.get("Records", []):
        try:
            body_str = record["body"]
            body_json = json.loads(body_str)

            # Extract only required info
            s3_key = body_json["detail"]["object"]["key"]
            bucket = body_json["detail"]["bucket"]["name"]
            
            key_parts = s3_key.split('/')
            if len(key_parts) >= 3 and key_parts[0] == 'raw_files':
                client_folder = key_parts[1]  # e.g., "Client1-PDF"
                filename = '/'.join(key_parts[2:])  # e.g., "document.pdf"
            
                logger.info(f"Processing file upload:")
                logger.info(f"  Bucket: {bucket}")
                logger.info(f"  Complete S3 Key: {s3_key}")
                logger.info(f"  Client Folder: {client_folder}")
                logger.info(f"  Filename: {filename}")

            # Build the actual input to the Step Function
            payload = {
                "s3_key": s3_key,
                "bucket": bucket,
                "client_name": client_folder
            }

            print("Invoking Step Function with input:", json.dumps(payload))

            response = sfn.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                input=json.dumps(payload)
            )

            print("Step Function started:", response["executionArn"])

        except Exception as e:
            print(f"Error: {e}")

    return {"status": "done"}
