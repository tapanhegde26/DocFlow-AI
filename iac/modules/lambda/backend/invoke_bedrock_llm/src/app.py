import json
import boto3
import logging
from typing import Dict, Any, Tuple
import re

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

# Configuration
BEDROCK_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
DISTINCT_PROCESSES_KB_ID = "NUC2FMC7EE"
NON_DISTINCT_PROCESSES_KB_ID = "SNVHCYP09Z"

# Keywords to identify process-related queries
PROCESS_KEYWORDS = [
    'process', 'procedure', 'workflow', 'step', 'steps', 'how to',
    'implementation', 'execute', 'perform', 'conduct', 'carry out',
    'methodology', 'approach', 'protocol', 'guideline', 'instruction'
]

def lambda_handler(event, context):
    """
    Main Lambda handler for chat API requests
    """
    try:
        # Parse the incoming request
        body = json.loads(event.get('body', '{}'))
        user_query = body.get('query', '').strip()
        
        if not user_query:
            return create_response(400, {'error': 'Query is required'})
        
        logger.info(f"Received query: {user_query}")
        
        # Analyze query to determine the appropriate knowledge base
        is_process_related, confidence = analyze_query_intent(user_query)
        
        # Get response from appropriate knowledge base
        if is_process_related:
            response = query_knowledge_base(user_query, DISTINCT_PROCESSES_KB_ID, "distinct-processes")
        else:
            response = query_knowledge_base(user_query, NON_DISTINCT_PROCESSES_KB_ID, "non-distinct-processes")
        
        # If knowledge base doesn't have relevant information, fallback to direct LLM
        if not response or response.get('confidence', 0) < 0.3:
            logger.info("Low confidence from knowledge base, falling back to direct LLM")
            response = query_bedrock_llm(user_query)
        
        return create_response(200, {
            'response': response.get('answer', ''),
            'source': response.get('source', 'llm'),
            'confidence': response.get('confidence', 0),
            'query_type': 'process-related' if is_process_related else 'general'
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})

def analyze_query_intent(query: str) -> Tuple[bool, float]:
    """
    Analyze if the query is process-related using keyword matching and LLM classification
    """
    query_lower = query.lower()
    
    # Simple keyword-based classification
    keyword_matches = sum(1 for keyword in PROCESS_KEYWORDS if keyword in query_lower)
    keyword_confidence = min(keyword_matches / 3, 1.0)  # Normalize to 0-1
    
    # Use LLM for more sophisticated classification
    classification_prompt = f"""
    Analyze the following user query and determine if it's asking about a specific process, procedure, or workflow.
    
    Query: "{query}"
    
    Respond with only "PROCESS" if it's asking about processes/procedures/workflows, or "GENERAL" if it's a general question.
    Consider questions about "how to do something", "steps to follow", "procedures", "workflows" as PROCESS-related.
    """
    
    try:
        llm_response = invoke_bedrock_model(classification_prompt)
        is_process_llm = "PROCESS" in llm_response.upper()
        
        # Combine keyword and LLM classification
        if keyword_confidence > 0.3 or is_process_llm:
            final_confidence = max(keyword_confidence, 0.7 if is_process_llm else 0.5)
            return True, final_confidence
        else:
            return False, 1 - keyword_confidence
            
    except Exception as e:
        logger.warning(f"LLM classification failed, using keyword-based: {str(e)}")
        return keyword_confidence > 0.3, keyword_confidence

def query_knowledge_base(query: str, kb_id: str, kb_type: str) -> Dict[str, Any]:
    """
    Query the specified knowledge base
    """
    try:
        logger.info(f"Querying {kb_type} knowledge base: {kb_id}")
        
        response = bedrock_agent_runtime.retrieve_and_generate(
            input={
                'text': query
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kb_id,
                    'modelArn': f'arn:aws:bedrock:ca-central-1::foundation-model/{BEDROCK_MODEL_ID}',
                    'retrievalConfiguration': {
                        'vectorSearchConfiguration': {
                            'numberOfResults': 5
                        }
                    }
                }
            }
        )
        
        answer = response['output']['text']
        citations = response.get('citations', [])
        
        # Calculate confidence based on citation relevance
        confidence = calculate_confidence(citations)
        
        return {
            'answer': answer,
            'source': f'knowledge-base-{kb_type}',
            'confidence': confidence,
            'citations': citations
        }
        
    except Exception as e:
        logger.error(f"Error querying knowledge base {kb_id}: {str(e)}")
        return None

def query_bedrock_llm(query: str) -> Dict[str, Any]:
    """
    Query Bedrock LLM directly when knowledge base doesn't have relevant information
    """
    try:
        enhanced_prompt = f"""
        You are a helpful assistant. Please provide a comprehensive and accurate answer to the following question:
        
        Question: {query}
        
        If you're not certain about the answer, please indicate your level of confidence and suggest where the user might find more specific information.
        """
        
        response = invoke_bedrock_model(enhanced_prompt)
        
        return {
            'answer': response,
            'source': 'bedrock-llm',
            'confidence': 0.7  # Default confidence for direct LLM responses
        }
        
    except Exception as e:
        logger.error(f"Error querying Bedrock LLM: {str(e)}")
        return {
            'answer': 'I apologize, but I encountered an error while processing your request. Please try again.',
            'source': 'error',
            'confidence': 0
        }

def invoke_bedrock_model(prompt: str) -> str:
    """
    Invoke Bedrock model with the given prompt
    """
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    response = bedrock_runtime.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType='application/json',
        accept='application/json',
        body=json.dumps(body)
    )
    
    response_body = json.loads(response['body'].read())
    return response_body['content'][0]['text']

def calculate_confidence(citations: list) -> float:
    """
    Calculate confidence score based on citations
    """
    if not citations:
        return 0.3
    
    # Simple confidence calculation based on number and quality of citations
    num_citations = len(citations)
    if num_citations >= 3:
        return 0.9
    elif num_citations >= 2:
        return 0.7
    elif num_citations >= 1:
        return 0.5
    else:
        return 0.3

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create standardized API response
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': json.dumps(body)
    }
