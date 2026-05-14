import json
import boto3
import os
from typing import Dict, Any, Tuple, Optional
from utils.shared_api import log_event
APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")
AUDIT_LOG_GROUP = os.getenv("AUDIT_LOG_GROUP")
APP_NAME = os.getenv("APP_NAME")

class LLMIntegration:
    """
    Unified LLM integration class that combines sophisticated query analysis,
    multiple knowledge base routing, and fallback mechanisms.
    """
    def __init__(self):
        # Initialize AWS clients
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get("AWS_REGION", "ca-central-1"))
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=os.environ.get("AWS_REGION", "ca-central-1"))

        # Configuration - can be overridden via environment variables
        self.bedrock_model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        self.distinct_processes_kb_id = os.environ.get("DISTINCT_PROCESSES_KB_ID", "BPWCDNTK6T")
        self.non_distinct_processes_kb_id = os.environ.get("NON_DISTINCT_PROCESSES_KB_ID", "SNVHCYP09Z")
        self.default_kb_id = os.environ.get("BEDROCK_KNOWLEDGE_BASE_ID")  # For backward compatibility

        # Keywords to identify process-related queries
        self.process_keywords = [
            'process', 'procedure', 'workflow', 'step', 'steps', 'how to',
            'implementation', 'execute', 'perform', 'conduct', 'carry out',
            'methodology', 'approach', 'protocol', 'guideline', 'instruction'
        ]

    def query_bedrock_knowledgebase(self, query: str, user_id: str, client_name : str,  kb_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Enhanced version of the original query_bedrock_knowledgebase function
        with intelligent routing and fallback mechanisms.

        Args:
            query: The user's query string
            kb_id: Optional specific knowledge base ID to use

        Returns:
            Dictionary containing response, source, confidence, and metadata
        """
        print(f"LLMIntegration:query_bedrock_knowledgebase: received user_id: {user_id}, client_name: {client_name}, query: {query}, kb_id: {kb_id}")
        try:
            log_event({
                "appName": APP_NAME,
                "message": f"llm_integration.py: query_bedrock_knowledgebase: Processing query: {query}",
                "level": "info",
                "context": {
                    "userId": user_id,
                    "clientName": client_name,
                    "query": query
                },
                "log_group": APP_LOG_GROUP,
            })


            # If specific KB ID provided, use it directly (backward compatibility)
            if kb_id:
                print("Calling specific kb")
                return self._query_specific_kb(client_name, user_id, query, kb_id, "specified")

            # Use intelligent routing
            print("Using intelligent query routing")
            return self._intelligent_query_routing(user_id, client_name, query)

        except Exception as e:
            log_event({
                "appName": APP_NAME,
                "message": f"Error in query_bedrock_knowledgebase: {str(e)}",
                "level": "error",
                "context": {
                    "userId": user_id,
                    "clientName": client_name,
                    "query": query
                },
                "log_group": APP_LOG_GROUP,
            })

            return {
                'response': 'I apologize, but I encountered an error while processing your request. Please try again.',
                'source': 'error',
                'confidence': 0,
                'error': str(e)
            }

    def _intelligent_query_routing(self, user_id, client_name, query: str) -> Dict[str, Any]:
        """
        Analyze query and route to appropriate knowledge base with fallback mechanisms.
        """
        print("_inside intelligent query routing")
        # Analyze query to determine the appropriate knowledge base
        is_process_related, confidence = self._analyze_query_intent(client_name, user_id, query)
        print(f"_intelligent_query_routing: found query intent is_process_related: {is_process_related} and confidence: {confidence}")

        # Get response from appropriate knowledge base
        if is_process_related:
            print("_intelligent_query_routing:process query path")
            response = self._query_specific_kb(client_name, user_id, query, self.distinct_processes_kb_id, "distinct-processes")
        else:
            # Try non-distinct processes KB first
            print("_intelligent_query_routing:non-process query path")
            response = self._query_specific_kb(client_name, user_id, query, self.non_distinct_processes_kb_id, "non-distinct-processes")

            # If that fails and default KB is available, try it
            if (not response or response.get('confidence', 0) < 0.3) and self.default_kb_id:
                print("did not receiv a response")

                log_event({
                    "appName": APP_NAME,
                    "message": "Trying default knowledge base as fallback",
                    "level": "info",
                    "context": {
                        "userId": user_id,
                        "clientName": client_name,
                        "query": query
                    },
                    "log_group": APP_LOG_GROUP,
                })

                response = self._query_specific_kb(client_name, user_id, query, self.default_kb_id, "default")

        # If knowledge base doesn't have relevant information, fallback to direct LLM
        if not response or response.get('confidence', 0) < 0.3:
            log_event({
                    "appName": APP_NAME,
                    "message": "Low confidence from knowledge base, falling back to direct LLM",
                    "level": "info",
                    "context": {
                        "userId": user_id,
                        "clientName": client_name,
                        "query": query
                    },
                    "log_group": APP_LOG_GROUP,
            })

            response = self._query_bedrock_llm(client_name, user_id, query)

        # Add query type metadata
        response['query_type'] = 'process-related' if is_process_related else 'general'

        return response

    def _analyze_query_intent(self, client_name, user_id, query: str) -> Tuple[bool, float]:
        """
        Analyze if the query is process-related using keyword matching and LLM classification
        """
        print("inside _analyze_query_intent")
        query_lower = query.lower()

        # Simple keyword-based classification
        keyword_matches = sum(1 for keyword in self.process_keywords if keyword in query_lower)
        keyword_confidence = min(keyword_matches / 3, 1.0)  # Normalize to 0-1

        # Use LLM for more sophisticated classification
        classification_prompt = f"""
        Analyze the following user query and determine if it's asking about a specific process, procedure, or workflow.

        Query: "{query}"

        Respond with only "PROCESS" if it's asking about processes/procedures/workflows, or "GENERAL" if it's a general question.
        Consider questions about "how to do something", "steps to follow", "procedures", "workflows" as PROCESS-related.
        """

        try:
            print("attempting to invoke bedrock model")
            llm_response = self._invoke_bedrock_model(classification_prompt)
            print(f"response from invoke, llm_response: {llm_response}")
            is_process_llm = "PROCESS" in llm_response.upper()

            # Combine keyword and LLM classification
            if keyword_confidence > 0.3 or is_process_llm:
                final_confidence = max(keyword_confidence, 0.7 if is_process_llm else 0.5)
                return True, final_confidence
            else:
                return False, 1 - keyword_confidence

        except Exception as e:
            
            log_event({
                    "appName": APP_NAME,
                    "message": f"LLM classification failed, using keyword-based: {str(e)}",
                    "level": "warning",
                    "context": {
                        "userId": user_id,
                        "clientName": client_name,
                        "query": query
                    },
                    "log_group": APP_LOG_GROUP,
            })

            return keyword_confidence > 0.3, keyword_confidence

    def _query_specific_kb(self, client_name, user_id, query: str, kb_id: str, kb_type: str) -> Dict[str, Any]:
        """
        Query the specified knowledge base with enhanced configuration
        """
        print("_query_specific_kb: inside _query_specific_kb, with properties kb_id: {kb_id} and kb_type: {kb_type}")
        try:
            log_event({
                    "appName": APP_NAME,
                    "message": f"Querying {kb_type} knowledge base: {kb_id}",
                    "level": "info",
                    "context": {
                        "userId": user_id,
                        "clientName": client_name,
                        "query": query
                    },
                    "log_group": APP_LOG_GROUP,
            })

            # Enhanced query with specific instructions for image references and tags
            enhanced_query = f"""
            {query}

            IMPORTANT INSTRUCTIONS:
            - If any image_references are found under process_details tags in the source documents, please include them in your response with the <image_references> tag.
            - Please include any llm_tags from the process documents in your response with the <llm_tags> tag.
            - Format image references as: <image_references>[list of image references]</image_references>
            - Format LLM tags as: <llm_tags>[list of llm tags]</llm_tags>
            """

            # Build model ARN
            model_arn = os.environ.get("BEDROCK_MODEL_ARN",
                                    f'arn:aws:bedrock:ca-central-1::foundation-model/{self.bedrock_model_id}')

            print(f"Model arn: {model_arn}")
            response = self.bedrock_agent_runtime.retrieve_and_generate(
                input={
                    'text': enhanced_query
                },
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': kb_id,
                        'modelArn': model_arn,
                        'retrievalConfiguration': {
                            'vectorSearchConfiguration': {
                                'numberOfResults': int(os.environ.get('VECTOR_SEARCH_RESULTS', 5))
                            }
                        },
                        'generationConfiguration': {
                            'promptTemplate': {
                                'textPromptTemplate': """
                                Based on the retrieved context, please answer the user's question comprehensively.

                                CRITICAL REQUIREMENTS:
                                1. If you find any image_references within process_details tags in the source documents, you MUST include them in your response using this exact format:
                                <image_references>
                                [list each image reference on a new line]
                                </image_references>

                                2. If you find any llm_tags from the process documents, you MUST include them in your response using this exact format:
                                <llm_tags>
                                [list each llm tag]
                                </llm_tags>

                                3. Provide your main answer to the question, then append the image references and llm tags at the end if found.

                                Question: $query$

                                Context: $search_results$

                                Answer:
                                """
                            }
                        }
                    }
                }
            )

            answer = response['output']['text']
            citations = response.get('citations', [])

            # Calculate confidence based on citation relevance
            confidence = self._calculate_confidence(citations)

            extracted_tags = self._extract_tags_from_response(answer)

            print(f'retrieved data - citations: {citations}, extracted_tags: {extracted_tags}')
            return {
                'response': answer,
                'source': f'knowledge-base-{kb_type}',
                'confidence': confidence,
                'citations': citations,
                'image_references': extracted_tags['image_references'],
                'llm_tags': extracted_tags['llm_tags']
            }

        except Exception as e:
            log_event({
                "appName": APP_NAME,
                "message": f"Error querying knowledge base {kb_id}: {str(e)}",
                "level": "error",
                "context": {
                    "userId": user_id,
                    "clientName": client_name,
                    "query": query
                },
                "log_group": APP_LOG_GROUP,
            })
            return None


    def _query_bedrock_llm(self, client_name, user_id, query: str) -> Dict[str, Any]:
        """
        Query Bedrock LLM directly when knowledge base doesn't have relevant information
        """
        try:
            enhanced_prompt = f"""
            You are a helpful assistant. Please provide a comprehensive and accurate answer to the following question:

            Question: {query}

            IMPORTANT INSTRUCTIONS:
            - If your response involves processes that typically have associated documentation, please note that image references and detailed process documentation may be available in the knowledge base.
            - If you're not certain about the answer, please indicate your level of confidence and suggest where the user might find more specific information.
            - If you have access to any process documentation with image_references or llm_tags, please include them using:
            <image_references>[references]</image_references>
            <llm_tags>[tags]</llm_tags>
            """

            response = self._invoke_bedrock_model(enhanced_prompt)

            return {
                'response': response,
                'source': 'bedrock-llm',
                'confidence': 0.7
            }

        except Exception as e:
            
            log_event({
                "appName": APP_NAME,
                "message": f"Error querying Bedrock LLM: {str(e)}",
                "level": "error",
                "context": {
                    "userId": user_id,
                    "clientName": client_name,
                    "query": query
                },
                "log_group": APP_LOG_GROUP,
            })

            return {
                'response': 'I apologize, but I encountered an error while processing your request. Please try again.',
                'source': 'error',
                'confidence': 0
            }

    def _extract_tags_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        Extract image references and LLM tags from the response text
        """
        import re

        # Extract image references
        image_refs_pattern = r'<image_references>(.*?)</image_references>'
        image_refs_match = re.search(image_refs_pattern, response_text, re.DOTALL)
        image_references = []
        if image_refs_match:
            image_refs_content = image_refs_match.group(1).strip()
            image_references = [ref.strip() for ref in image_refs_content.split('\n') if ref.strip()]

        # Extract LLM tags
        llm_tags_pattern = r'<llm_tags>(.*?)</llm_tags>'
        llm_tags_match = re.search(llm_tags_pattern, response_text, re.DOTALL)
        llm_tags = []
        if llm_tags_match:
            llm_tags_content = llm_tags_match.group(1).strip()
            llm_tags = [tag.strip() for tag in llm_tags_content.split(',') if tag.strip()]

        return {
            'image_references': image_references,
            'llm_tags': llm_tags
        }

    def _invoke_bedrock_model(self, prompt: str) -> str:
        """
        Invoke Bedrock model with the given prompt
        """
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

        print(f" medrock model id: {self.bedrock_model_id}")
        response = self.bedrock_runtime.invoke_model(
            modelId=self.bedrock_model_id,
            contentType='application/json',
            accept='application/json',
            body=json.dumps(body)
        )

        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']

    def _calculate_confidence(self, citations: list) -> float:
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


# Global instance for backward compatibility and easy import
_llm_integration = LLMIntegration()

# Backward compatible function that matches your lead's original signature
def query_bedrock_knowledgebase(query: str, user_id: str, client_name : str, kb_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Main function to query knowledge base with intelligent routing and fallback.
    This function maintains backward compatibility while providing enhanced functionality.

    Args:
        query: The user's query string
        kb_id: Optional specific knowledge base ID (for backward compatibility)

    Returns:
        Dictionary containing response and metadata
    """
    print(f"llm_integration.py:query_bedrock_kb: with query: {query}, kb_id: {kb_id}")
    return _llm_integration.query_bedrock_knowledgebase(query, user_id, client_name, kb_id)

# Additional convenience functions for specific use cases
def query_with_process_detection(query: str) -> Dict[str, Any]:
    """
    Query with automatic process detection and routing
    """
    return _llm_integration._intelligent_query_routing(query)

def query_specific_kb(query: str, kb_id: str) -> Dict[str, Any]:
    """
    Query a specific knowledge base directly
    """
    return _llm_integration._query_specific_kb(query, kb_id, "direct")

def query_llm_direct(query: str) -> Dict[str, Any]:
    """
    Query Bedrock LLM directly without knowledge base
    """
    return _llm_integration._query_bedrock_llm(query)


if __name__ == "__main__":
    # Example usage and testing
    sample_queries = [
        "What is the process for deploying applications?",
        "Tell me about machine learning",
        "How do I configure the system?"
    ]

    for query in sample_queries:
        print(f"\nQuery: {query}")
        result = query_bedrock_knowledgebase(query)
        print(f"Response: {result.get('response', 'No response')[:100]}...")
        print(f"Source: {result.get('source')}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"image_references: {result.get('image_references')}")
        print(f"llm_tags: {result.get('llm_tags')}")