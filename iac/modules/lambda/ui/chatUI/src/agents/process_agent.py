from typing import Dict, Any, Optional
from .base_agent import BaseAgent
import re
import os

class ProcessAgent(BaseAgent):
    """Agent for retrieving procedural and workflow information"""
    
    def __init__(self):
        super().__init__()
        self.process_kb_id = os.environ.get("DISTINCT_PROCESSES_KB_ID")
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve process-related information"""
        if not state.get('needs_process_kb', False):
            return state
        
        query = state.get('query', '')
        user_id = state.get('user_id', '')
        client_name = state.get('client_name', '')
        
        self._log_event(
            f"ProcessAgent: Querying process knowledge base",
            "info",
            {"userId": user_id, "clientName": client_name, "kbId": self.process_kb_id}
        )
        
        try:
            result = self._query_process_kb(query, user_id, client_name)
            
            state.update({
                'process_response': result['response'],
                'process_citations': result.get('citations', []),
                'process_confidence': result.get('confidence', 0),
                'process_image_references': result.get('image_references', []),
                'process_llm_tags': result.get('llm_tags', [])
            })
            
            self._log_event(
                f"ProcessAgent: Successfully retrieved process information",
                "info",
                {"userId": user_id, "clientName": client_name, "confidence": result.get('confidence', 0)}
            )
            
        except Exception as e:
            self._log_event(
                f"ProcessAgent: Error querying process KB: {str(e)}",
                "error",
                {"userId": user_id, "clientName": client_name, "error": str(e)}
            )
            
            state.update({
                'process_response': None,
                'process_error': str(e),
                'process_confidence': 0
            })
        
        return state
    
    def _query_process_kb(self, query: str, user_id: str, client_name: str) -> Dict[str, Any]:
        """Query the process knowledge base"""
        enhanced_query = f"""
        {query}
        
        IMPORTANT INSTRUCTIONS:
        - Focus on procedural and workflow information
        - Include step-by-step instructions when available
        - If any image_references are found under process_details tags, include them with <image_references> tag
        - Include any llm_tags from process documents with <llm_tags> tag
        """
        
        model_arn = os.environ.get("BEDROCK_MODEL_ARN",
                                f'arn:aws:bedrock:ca-central-1::foundation-model/{self.bedrock_model_id}')
        
        response = self.bedrock_agent_runtime.retrieve_and_generate(
            input={'text': enhanced_query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': self.process_kb_id,
                    'modelArn': model_arn,
                    'retrievalConfiguration': {
                        'vectorSearchConfiguration': {
                            'numberOfResults': int(os.environ.get('VECTOR_SEARCH_RESULTS', 20))
                        }
                    },
                    'generationConfiguration': {
                        'promptTemplate': {
                            'textPromptTemplate': f"""
                            You are a process and workflow expert for {client_name}. Based on the retrieved context, provide detailed procedural information ONLY for {client_name}.

                            CRITICAL REQUIREMENTS:
                            1. Focus on step-by-step processes and workflows for {client_name} ONLY
                            2. Include image references ONLY if they belong to {client_name}: <image_references>[references]</image_references>
                            3. Include llm tags ONLY if they belong to {client_name}: <llm_tags>[tags]</llm_tags>
                            4. EXCLUDE any content, images, or references from other clients.

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
        extracted_tags = self._extract_tags_from_response(answer)
        
        return {
            'response': answer,
            'citations': citations,
            'confidence': confidence,
            'image_references': extracted_tags['image_references'],
            'llm_tags': extracted_tags['llm_tags']
        }
    
    def _extract_tags_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract image references and LLM tags from response"""
        # Extract image references
        image_refs_pattern = r'<image_references>(.*?)</image_references>'
        image_refs_match = re.search(image_refs_pattern, response_text, re.DOTALL)
        image_references = []
        if image_refs_match:
            image_refs_content = image_refs_match.group(1).strip()
            # Remove surrounding square brackets if present
            image_refs_content = re.sub(r'^\[|\]$', '', image_refs_content.strip())
            # Split by newlines or commas and clean each reference
            refs = re.split(r'[\n,]', image_refs_content)
            image_references = [ref.strip() for ref in refs if ref.strip()]
        
        # Extract LLM tags
        llm_tags_pattern = r'<llm_tags>(.*?)</llm_tags>'
        llm_tags_match = re.search(llm_tags_pattern, response_text, re.DOTALL)
        llm_tags = []
        if llm_tags_match:
            llm_tags_content = llm_tags_match.group(1).strip()
            # Remove surrounding square brackets if present
            llm_tags_content = re.sub(r'^\[|\]$', '', llm_tags_content.strip())
            # Split by commas and clean each tag
            llm_tags = [tag.strip() for tag in llm_tags_content.split(',') if tag.strip()]
        
        return {
            'image_references': image_references,
            'llm_tags': llm_tags
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
