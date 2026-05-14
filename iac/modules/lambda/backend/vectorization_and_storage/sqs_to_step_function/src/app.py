import json
import boto3
import os

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

            # Build the actual input to the Step Function
            payload = {
                "s3_key": s3_key,
                "bucket": bucket
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
