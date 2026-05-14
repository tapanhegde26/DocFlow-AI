from abc import ABC, abstractmethod
from typing import Dict, Any, List
import boto3
import os
import json
from utils.shared_api import log_event

class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self):
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get("AWS_REGION", "ca-central-1"))
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=os.environ.get("AWS_REGION", "ca-central-1"))
        self.bedrock_model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        
    @abstractmethod
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main functionality"""
        pass
    
    def _invoke_bedrock_model(self, prompt: str) -> str:
        """Invoke Bedrock model with the given prompt"""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": int(os.environ.get('MAX_TOKENS', 1000)),
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = self.bedrock_runtime.invoke_model(
            modelId=self.bedrock_model_id,
            contentType='application/json',
            accept='application/json',
            body=json.dumps(body)
        )
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    def _log_event(self, message: str, level: str, context: Dict[str, Any]):
        """Helper method for logging"""
        log_event({
            "appName": os.getenv("APP_NAME"),
            "message": message,
            "level": level,
            "context": context,
            "log_group": os.getenv("APP_LOG_GROUP"),
        })
