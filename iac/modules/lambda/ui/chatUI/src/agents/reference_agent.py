from typing import Dict, Any
from .base_agent import BaseAgent
import os

class ReferenceAgent(BaseAgent):
    """Agent for retrieving branding, tone, and reference information"""
    
    def __init__(self):
        super().__init__()
        self.reference_kb_id = os.environ.get("NON_DISTINCT_PROCESSES_KB_ID")
        self.default_kb_id = os.environ.get("BEDROCK_KNOWLEDGE_BASE_ID")
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve reference information"""
        if not state.get('needs_reference_kb', False):
            return state
        
        query = state.get('query', '')
        user_id = state.get('user_id', '')
        client_name = state.get('client_name', '')
        
        self._log_event(
            f"ReferenceAgent: Querying reference knowledge base",
            "info",
            {"userId": user_id, "clientName": client_name, "kbId": self.reference_kb_id}
        )
        
        try:
            result = self._query_reference_kb(query, user_id, client_name)
            
            state.update({
                'reference_response': result['response'],
                'reference_citations': result.get('citations', []),
                'reference_confidence': result.get('confidence', 0)
            })
            
            self._log_event(
                f"ReferenceAgent: Successfully retrieved reference information",
                "info",
                {"userId": user_id, "clientName": client_name, "confidence": result.get('confidence', 0)}
            )
            
        except Exception as e:
            self._log_event(
                f"ReferenceAgent: Error querying reference KB: {str(e)}",
                "error",
                {"userId": user_id, "clientName": client_name, "error": str(e)}
            )
            
            # Try fallback to default KB if available
            if self.default_kb_id:
                try:
                    result = self._query_fallback_kb(query, user_id, client_name)
                    state.update({
                        'reference_response': result['response'],
                        'reference_citations': result.get('citations', []),
                        'reference_confidence': result.get('confidence', 0),
                        'used_fallback': True
                    })
                except Exception as fallback_error:
                    state.update({
                        'reference_response': None,
                        'reference_error': str(e),
                        'reference_confidence': 0
                    })
            else:
                state.update({
                    'reference_response': None,
                    'reference_error': str(e),
                    'reference_confidence': 0
                })
        
        return state
    
    def _query_reference_kb(self, query: str, user_id: str, client_name: str) -> Dict[str, Any]:
        """Query the reference knowledge base"""
        enhanced_query = f"""
        {query}
        
        IMPORTANT INSTRUCTIONS:
        - Focus on branding guidelines, tone, and reference information
        - Provide context about company policies and general guidelines
        - Include relevant reference materials and documentation
        """
        
        model_arn = os.environ.get("BEDROCK_MODEL_ARN",
                                f'arn:aws:bedrock:ca-central-1::foundation-model/{self.bedrock_model_id}')
        
        response = self.bedrock_agent_runtime.retrieve_and_generate(
            input={'text': enhanced_query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': self.reference_kb_id,
                    'modelArn': model_arn,
                    'retrievalConfiguration': {
                        'vectorSearchConfiguration': {
                            'numberOfResults': int(os.environ.get('VECTOR_SEARCH_RESULTS', 5))
                        }
                    },
                    'generationConfiguration': {
                        'promptTemplate': {
                            'textPromptTemplate': """
                            You are a reference and branding expert. Based on the retrieved context, provide comprehensive reference information.
                            
                            REQUIREMENTS:
                            1. Focus on branding guidelines, tone, and reference materials
                            2. Provide accurate company policies and guidelines
                            3. Include relevant context and background information
                            4. Maintain appropriate tone and branding consistency
                            
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
        confidence = self._calculate_confidence(citations)
        
        return {
            'response': answer,
            'citations': citations,
            'confidence': confidence
        }
    
    def _query_fallback_kb(self, query: str, user_id: str, client_name: str) -> Dict[str, Any]:
        """Query the fallback/default knowledge base"""
        model_arn = os.environ.get("BEDROCK_MODEL_ARN",
                                f'arn:aws:bedrock:ca-central-1::foundation-model/{self.bedrock_model_id}')
        
        response = self.bedrock_agent_runtime.retrieve_and_generate(
            input={'text': query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': self.default_kb_id,
                    'modelArn': model_arn
                }
            }
        )
        
        return {
            'response': response['output']['text'],
            'citations': response.get('citations', []),
            'confidence': self._calculate_confidence(response.get('citations', []))
        }
    
    def _calculate_confidence(self, citations: list) -> float:
        """Calculate confidence score based on citations"""
        if not citations:
            return 0.3
        
        num_citations = len(citations)
        if num_citations >= 3:
            return 0.9
        elif num_citations >= 2:
            return 0.7
        elif num_citations >= 1:
            return 0.5
        else:
            return 0.3
