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
    Enhanced LLM integration class that supports both traditional single-agent
    and new multi-agent workflows using LangGraph.
    """
    def __init__(self):
        # Initialize AWS clients
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get("AWS_REGION", "ca-central-1"))
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=os.environ.get("AWS_REGION", "ca-central-1"))
        
        # Configuration - can be overridden via environment variables
        self.bedrock_model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        self.distinct_processes_kb_id = os.environ.get("DISTINCT_PROCESSES_KB_ID")
        self.non_distinct_processes_kb_id = os.environ.get("NON_DISTINCT_PROCESSES_KB_ID")
        self.default_kb_id = os.environ.get("BEDROCK_KNOWLEDGE_BASE_ID")  # For backward compatibility
        
        # Keywords to identify process-related queries (for legacy mode)
        self.process_keywords = [
            'process', 'procedure', 'workflow', 'step', 'steps', 'how to',
            'implementation', 'execute', 'perform', 'conduct', 'carry out',
            'methodology', 'approach', 'protocol', 'guideline', 'instruction'
        ]
        
        # Multi-agent workflow - lazy loaded to avoid import errors when not needed
        self._multi_agent_workflow = None
    
    @property
    def multi_agent_workflow(self):
        """Lazy load the multi-agent workflow only when needed"""
        if self._multi_agent_workflow is None:
            try:
                from agents.langgraph_workflow import get_workflow
                self._multi_agent_workflow = get_workflow()
                print("Multi-agent workflow loaded successfully")
            except ImportError as e:
                print(f"Warning: Could not import langgraph workflow: {e}")
                print("Multi-agent features will not be available. Please ensure langgraph is installed.")
                raise ImportError(
                    "LangGraph dependencies are not available. "
                    "Multi-agent features require langgraph to be installed. "
                    f"Original error: {str(e)}"
                )
        return self._multi_agent_workflow

    def query_bedrock_knowledgebase(self, query: str, user_id: str, client_name: str, 
                                   kb_id: Optional[str] = None, use_agents: bool = False) -> Dict[str, Any]:
        """
        Enhanced version with support for both traditional and multi-agent approaches.
        
        Args:
            query: The user's query string
            user_id: User identifier
            client_name: Client name
            kb_id: Optional specific knowledge base ID to use (legacy mode)
            use_agents: Whether to use the multi-agent LangGraph workflow
            
        Returns:
            Dictionary containing response, source, confidence, and metadata
        """
        print(f"LLMIntegration:query_bedrock_knowledgebase: received user_id: {user_id}, client_name: {client_name}, query: {query}, kb_id: {kb_id}, use_agents: {use_agents}")
        
        try:
            log_event({
                "appName": APP_NAME,
                "message": f"llm_integration.py: query_bedrock_knowledgebase: Processing query with {'multi-agent' if use_agents else 'traditional'} approach",
                "level": "info",
                "context": {
                    "userId": user_id,
                    "clientName": client_name,
                    "query": query,
                    "useAgents": use_agents
                },
                "log_group": APP_LOG_GROUP,
            })
            
            # Route to appropriate processing method
            if use_agents:
                print("Using multi-agent LangGraph workflow")
                return self._process_with_agents(query, user_id, client_name)
            else:
                print("Using traditional single-agent approach")
                return self._process_traditional(query, user_id, client_name, kb_id)
                
        except Exception as e:
            log_event({
                "appName": APP_NAME,
                "message": f"Error in query_bedrock_knowledgebase: {str(e)}",
                "level": "error",
                "context": {
                    "userId": user_id,
                    "clientName": client_name,
                    "query": query,
                    "useAgents": use_agents
                },
                "log_group": APP_LOG_GROUP,
            })
            return {
                'response': 'I apologize, but I encountered an error while processing your request. Please try again.',
                'source': 'error',
                'confidence': 0,
                'error': str(e)
            }

    def _process_with_agents(self, query: str, user_id: str, client_name: str) -> Dict[str, Any]:
        """Process query using multi-agent LangGraph workflow"""
        try:
            log_event({
                "appName": APP_NAME,
                "message": "Starting multi-agent workflow processing",
                "level": "info",
                "context": {
                    "userId": user_id,
                    "clientName": client_name,
                    "query": query
                },
                "log_group": APP_LOG_GROUP,
            })
            
            # Lazy load and invoke the multi-agent workflow
            try:
                workflow = self.multi_agent_workflow
                result = workflow.invoke(query, user_id, client_name)
            except ImportError as import_err:
                # If langgraph is not available, fall back to traditional approach
                log_event({
                    "appName": APP_NAME,
                    "message": f"LangGraph not available, falling back to traditional approach: {str(import_err)}",
                    "level": "warning",
                    "context": {
                        "userId": user_id,
                        "clientName": client_name,
                        "error": str(import_err)
                    },
                    "log_group": APP_LOG_GROUP,
                })
                return self._process_traditional(query, user_id, client_name, None)
            
            log_event({
                "appName": APP_NAME,
                "message": f"Multi-agent workflow completed successfully with source: {result.get('source')}",
                "level": "info",
                "context": {
                    "userId": user_id,
                    "clientName": client_name,
                    "source": result.get('source'),
                    "confidence": result.get('confidence')
                },
                "log_group": APP_LOG_GROUP,
            })
            
            return result
        
        except Exception as e:
            log_event({
                "appName": APP_NAME,
                "message": f"Error in multi-agent workflow: {str(e)}",
                "level": "error",
                "context": {
                    "userId": user_id,
                    "clientName": client_name,
                    "error": str(e)
                },
                "log_group": APP_LOG_GROUP,
            })
            
            # Fallback to traditional approach if multi-agent fails
            log_event({
                "appName": APP_NAME,
                "message": "Multi-agent workflow failed, falling back to traditional approach",
                "level": "warning",
                "context": {
                    "userId": user_id,
                    "clientName": client_name
                },
                "log_group": APP_LOG_GROUP,
            })
            
            return self._process_traditional(query, user_id, client_name, None)

    def _process_traditional(self, query: str, user_id: str, client_name: str, kb_id: Optional[str]) -> Dict[str, Any]:
        """Process query using traditional single-agent approach (existing logic)"""
        # If specific KB ID provided, use it directly (backward compatibility)
        if kb_id:
            print("Calling specific kb")
            return self._query_specific_kb(client_name, user_id, query, kb_id, "specified")

        # Use intelligent routing (existing logic)
        print("Using intelligent query routing")
        return self._intelligent_query_routing(user_id, client_name, query)

    def _intelligent_query_routing(self, user_id, client_name, query: str) -> Dict[str, Any]:
        """
        Analyze query and route to appropriate knowledge base with fallback mechanisms.
        (Existing method - unchanged)
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
                print("did not receive a response")
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
        (Existing method - unchanged)
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
        (Existing method - unchanged)
        """
        print(f"_query_specific_kb: inside _query_specific_kb, with properties kb_id: {kb_id} and kb_type: {kb_type}")
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
        (Existing method - unchanged)
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
        (Existing method - unchanged)
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
        (Existing method - unchanged)
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
        print(f" bedrock model id: {self.bedrock_model_id}")
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
        (Existing method - unchanged)
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

# Enhanced backward compatible function with agent support
def query_bedrock_knowledgebase(query: str, user_id: str, client_name: str, 
                               kb_id: Optional[str] = None, use_agents: bool = False) -> Dict[str, Any]:
    """
    Main function to query knowledge base with intelligent routing and fallback.
    Now supports both traditional and multi-agent approaches.
    
    Args:
        query: The user's query string
        user_id: User identifier  
        client_name: Client name
        kb_id: Optional specific knowledge base ID (for backward compatibility)
        use_agents: Whether to use the multi-agent LangGraph workflow
        
    Returns:
        Dictionary containing response and metadata
    """
    print(f"llm_integration.py:query_bedrock_kb: with query: {query}, kb_id: {kb_id}, use_agents: {use_agents}")
    return _llm_integration.query_bedrock_knowledgebase(query, user_id, client_name, kb_id, use_agents)

# Additional convenience functions for specific use cases
def query_with_process_detection(query: str, user_id: str, client_name: str) -> Dict[str, Any]:
    """
    Query with automatic process detection and routing (traditional approach)
    """
    return _llm_integration._intelligent_query_routing(user_id, client_name, query)

def query_specific_kb(query: str, user_id: str, client_name: str, kb_id: str) -> Dict[str, Any]:
    """
    Query a specific knowledge base directly
    """
    return _llm_integration._query_specific_kb(client_name, user_id, query, kb_id, "direct")

def query_llm_direct(query: str, user_id: str, client_name: str) -> Dict[str, Any]:
    """
    Query Bedrock LLM directly without knowledge base
    """
    return _llm_integration._query_bedrock_llm(client_name, user_id, query)

def query_with_agents(query: str, user_id: str, client_name: str) -> Dict[str, Any]:
    """
    Query using the multi-agent LangGraph workflow
    """
    return _llm_integration._process_with_agents(query, user_id, client_name)

if __name__ == "__main__":
    # Example usage and testing
    sample_queries = [
        "What is the process for deploying applications?",
        "Tell me about machine learning", 
        "How do I configure the system?"
    ]
    
    for query in sample_queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        
        # Test traditional approach
        print(f"\n--- Traditional Approach ---")
        result_traditional = query_bedrock_knowledgebase(query, "test_user", "test_client", use_agents=False)
        print(f"Response: {result_traditional.get('response', 'No response')[:100]}...")
        print(f"Source: {result_traditional.get('source')}")
        print(f"Confidence: {result_traditional.get('confidence')}")
        
        # Test multi-agent approach
        print(f"\n--- Multi-Agent Approach ---")
        result_agents = query_bedrock_knowledgebase(query, "test_user", "test_client", use_agents=True)
        print(f"Response: {result_agents.get('response', 'No response')[:100]}...")
        print(f"Source: {result_agents.get('source')}")
        print(f"Confidence: {result_agents.get('confidence')}")
        print(f"Routing Decision: {result_agents.get('routing_decision', {})}")
        print(f"Image References: {result_agents.get('image_references')}")
        print(f"LLM Tags: {result_agents.get('llm_tags')}")