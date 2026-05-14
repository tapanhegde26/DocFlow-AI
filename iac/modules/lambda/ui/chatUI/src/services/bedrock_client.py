
import boto3
import os

################## DELETE THIS FILE IT IS NOT BEING USED 

def query_bedrock_knowledgebase(user_query):
    bedrock = boto3.client("bedrock-agent-runtime", region_name=os.environ.get("AWS_REGION", "ca-central-1"))

    response = bedrock.retrieve_and_generate(
        input={"text": user_query},
        knowledgeBaseId=os.environ["BEDROCK_KNOWLEDGE_BASE_ID"],
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults": 3
                    }
                },
                "generationConfiguration": {
                    "modelArn": os.environ.get(
                        "BEDROCK_MODEL_ARN",
                        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
                    )
                }
            }
        }
    )

    return response