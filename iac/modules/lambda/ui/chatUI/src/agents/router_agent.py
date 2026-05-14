from typing import Dict, Any, List
from .base_agent import BaseAgent

class RouterAgent(BaseAgent):
    """Router agent that classifies incoming queries"""
    
    def __init__(self):
        super().__init__()
        self.process_keywords = [
            'process', 'procedure', 'workflow', 'step', 'steps', 'how to',
            'implementation', 'execute', 'perform', 'conduct', 'carry out',
            'methodology', 'approach', 'protocol', 'guideline', 'instruction'
        ]
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Classify the query and determine routing strategy"""
        query = state.get('query', '')
        user_id = state.get('user_id', '')
        client_name = state.get('client_name', '')
        
        self._log_event(
            f"RouterAgent: Analyzing query for routing",
            "info",
            {"userId": user_id, "clientName": client_name, "query": query}
        )
        
        # Analyze query intent
        classification = self._classify_query(query, user_id, client_name)
        
        # Update state with routing decision
        state.update({
            'routing_decision': classification,
            'needs_process_kb': classification['is_process_related'],
            'needs_reference_kb': classification['needs_reference'],
            'confidence': classification['confidence']
        })
        
        self._log_event(
            f"RouterAgent: Query classified as {classification}",
            "info",
            {"userId": user_id, "clientName": client_name, "classification": classification}
        )
        
        return state
    
    def _classify_query(self, query: str, user_id: str, client_name: str) -> Dict[str, Any]:
        """Classify query using keyword analysis and LLM"""
        query_lower = query.lower()
        
        # Keyword-based classification
        keyword_matches = sum(1 for keyword in self.process_keywords if keyword in query_lower)
        keyword_confidence = min(keyword_matches / 3, 1.0)
        
        # LLM-based classification
        classification_prompt = f"""
        Analyze the following user query and classify it based on these categories:
        
        1. PROCESS: Questions about procedures, workflows, how-to instructions, step-by-step processes
        2. REFERENCE: Questions about branding, tone, general information, policies, guidelines
        3. BOTH: Questions that might need both procedural and reference information
        
        Query: "{query}"
        
        Respond in JSON format:
        {{
            "primary_type": "PROCESS|REFERENCE|BOTH",
            "reasoning": "brief explanation",
            "confidence": 0.0-1.0,
            "secondary_needs": ["PROCESS", "REFERENCE"] or []
        }}
        """
        
        try:
            llm_response = self._invoke_bedrock_model(classification_prompt)
            import json
            classification_result = json.loads(llm_response)
            
            primary_type = classification_result.get('primary_type', 'REFERENCE')
            confidence = classification_result.get('confidence', 0.5)
            
            return {
                'is_process_related': primary_type in ['PROCESS', 'BOTH'],
                'needs_reference': primary_type in ['REFERENCE', 'BOTH'],
                'primary_type': primary_type,
                'confidence': max(confidence, keyword_confidence),
                'reasoning': classification_result.get('reasoning', ''),
                'llm_classification': classification_result
            }
            
        except Exception as e:
            self._log_event(
                f"RouterAgent: LLM classification failed: {str(e)}",
                "warning",
                {"userId": user_id, "clientName": client_name, "error": str(e)}
            )
            
            # Fallback to keyword-based classification
            is_process = keyword_confidence > 0.3
            return {
                'is_process_related': is_process,
                'needs_reference': not is_process,
                'primary_type': 'PROCESS' if is_process else 'REFERENCE',
                'confidence': keyword_confidence,
                'reasoning': 'Keyword-based fallback classification'
            }
