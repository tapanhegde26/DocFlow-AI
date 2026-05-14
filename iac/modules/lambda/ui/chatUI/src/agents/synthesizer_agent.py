from typing import Dict, Any, List
import re
from .base_agent import BaseAgent


class SynthesizerAgent(BaseAgent):
   """Agent for combining and synthesizing results from multiple knowledge bases"""
  
   def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
       """Synthesize responses from multiple agents"""
       user_id = state.get('user_id', '')
       client_name = state.get('client_name', '')
       query = state.get('query', '')
      
       self._log_event(
           f"SynthesizerAgent: Synthesizing responses",
           "info",
           {"userId": user_id, "clientName": client_name}
       )
      
       # Collect available responses
       process_response = state.get('process_response')
       reference_response = state.get('reference_response')
       process_confidence = state.get('process_confidence', 0)
       reference_confidence = state.get('reference_confidence', 0)
      
       # Build structured response object
       structured_response = {}
       source = 'unknown'
       confidence = 0
      
       if process_response and reference_response:
           # Both responses available - return as structured object
           structured_response = {
               'process_knowledge_response': self._clean_response_text(process_response),
               'reference_knowledge_response': self._clean_response_text(reference_response)
           }
           source = 'multi-agent-synthesis'
           confidence = max(process_confidence, reference_confidence)
       elif process_response:
           # Only process response available
           structured_response = {
               'process_knowledge_response': self._clean_response_text(process_response),
               'reference_knowledge_response': None
           }
           source = 'process-agent'
           confidence = process_confidence
       elif reference_response:
           # Only reference response available
           structured_response = {
               'process_knowledge_response': None,
               'reference_knowledge_response': self._clean_response_text(reference_response)
           }
           source = 'reference-agent'
           confidence = reference_confidence
       else:
           # No responses available - fallback to direct LLM
           fallback_response = self._fallback_llm_response(query, user_id, client_name)
           structured_response = {
               'process_knowledge_response': None,
               'reference_knowledge_response': self._clean_response_text(fallback_response)
           }
           source = 'fallback-llm'
           confidence = 0.6
      
       # Use structured response as final response
    #    cleaned_response = structured_response
       cleaned_response = self._flatten_structured_response(structured_response)
      
       # Combine citations and metadata
       all_citations = []
       all_citations.extend(state.get('process_citations', []))
       all_citations.extend(state.get('reference_citations', []))
      
       # Merge image references and tags from both agents
       all_image_references = []
       all_image_references.extend(state.get('process_image_references', []))
       all_image_references.extend(state.get('reference_image_references', []))
      
       all_llm_tags = []
       all_llm_tags.extend(state.get('process_llm_tags', []))
       all_llm_tags.extend(state.get('reference_llm_tags', []))
      
       # Remove duplicates while preserving order
       all_image_references = list(dict.fromkeys(all_image_references))
       all_llm_tags = list(dict.fromkeys(all_llm_tags))
      
       # Prepare final response with structured format
       state.update({
           'final_response': cleaned_response,
           'final_source': source,
           'final_confidence': confidence,
           'all_citations': all_citations,
           'image_references': all_image_references,
           'llm_tags': all_llm_tags,
           'synthesis_complete': True
       })
      
       self._log_event(
           f"SynthesizerAgent: Synthesis complete",
           "info",
           {"userId": user_id, "clientName": client_name, "source": source, "confidence": confidence}
       )
      
       return state
  
   def _synthesize_multiple_responses(self, query: str, process_response: str,
                                    reference_response: str, process_confidence: float,
                                    reference_confidence: float, user_id: str, client_name: str) -> str:
       """Synthesize multiple responses using rules-based approach (NO Gen-AI)"""
      
       self._log_event(
           f"SynthesizerAgent: Combining responses using rules-based logic",
           "info",
           {"userId": user_id, "clientName": client_name,
            "process_confidence": process_confidence,
            "reference_confidence": reference_confidence}
       )
      
       # Rules-based combination logic
       try:
           # Rule 1: If process confidence is significantly higher, prioritize process
           if process_confidence > reference_confidence + 0.3:
               combined = f"{process_response}\n\nAdditional Context:\n{reference_response}"
               self._log_event(
                   "SynthesizerAgent: Process response prioritized (higher confidence)",
                   "info",
                   {"userId": user_id, "clientName": client_name}
               )
          
           # Rule 2: If reference confidence is significantly higher, prioritize reference
           elif reference_confidence > process_confidence + 0.3:
               combined = f"{reference_response}\n\nRelated Process Information:\n{process_response}"
               self._log_event(
                   "SynthesizerAgent: Reference response prioritized (higher confidence)",
                   "info",
                   {"userId": user_id, "clientName": client_name}
               )
          
           # Rule 3: Similar confidence - combine with clear section headers
           else:
               combined = f"Process Information:\n{process_response}\n\nReference Information:\n{reference_response}"
               self._log_event(
                   "SynthesizerAgent: Responses combined with equal weight",
                   "info",
                   {"userId": user_id, "clientName": client_name}
               )
          
           return combined
          
       except Exception as e:
           self._log_event(
               f"SynthesizerAgent: Error during rules-based combination: {str(e)}",
               "error",
               {"userId": user_id, "clientName": client_name, "error": str(e)}
           )
           # Fallback to the response with higher confidence
           return process_response if process_confidence >= reference_confidence else reference_response
  
   def _fallback_llm_response(self, query: str, user_id: str, client_name: str) -> str:
       """Generate fallback response using rules-based approach (NO Gen-AI)"""
      
       self._log_event(
           f"SynthesizerAgent: Using rules-based fallback (no KB results found)",
           "warning",
           {"userId": user_id, "clientName": client_name, "query": query}
       )
      
       # Rules-based fallback response - static, helpful message
       fallback_message = (
           "I apologize, but I couldn't find relevant information in our knowledge bases for your query. "
           "\n\nHere are some suggestions:\n"
           "1. Try rephrasing your question with different keywords\n"
           "2. Break down complex questions into simpler parts\n"
           "3. Contact our support team for personalized assistance\n"
           "4. Check our documentation portal for additional resources\n\n"
           "If you believe this information should be available, please let us know so we can improve our knowledge base."
       )
      
       return fallback_message
  
   def _clean_response_text(self, response_text: str) -> str:
       """
       Clean the response text by removing XML-like tags for llm_tags and image_references.
       These tags are extracted separately and should not appear in the final response.
       """
       if not response_text:
           return response_text

       cleaned_text = response_text
      
    #    # Remove <llm_tags>...</llm_tags> tags and their content
    #    cleaned_text = re.sub(r'<llm_tags>.*?</llm_tags>', '', response_text, flags=re.DOTALL)
      
    #    # Remove <image_references>...</image_references> tags and their content
    #    cleaned_text = re.sub(r'<image_references>.*?</image_references>', '', cleaned_text, flags=re.DOTALL)

       # Remove square brackets from within XML tags
       cleaned_text = re.sub(r'(<(?:llm_tags|image_references)>)\[([^\]]*)\](<\/(?:llm_tags|image_references)>)', r'\1\2\3', cleaned_text)

    
       # Remove extra blank lines that may result from tag removal
       cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)
      
       # Trim leading/trailing whitespace
       cleaned_text = cleaned_text.strip()
      
       return cleaned_text

   def _flatten_structured_response(self, structured_response: Dict[str, Any]) -> str:
    """Convert structured response to flat string format for UI consistency"""
    process_resp = structured_response.get('process_knowledge_response')
    reference_resp = structured_response.get('reference_knowledge_response')
    
    if process_resp and reference_resp:
        return f"{process_resp}\n\nAdditional Reference Information:\n{reference_resp}"
    elif process_resp:
        return process_resp
    elif reference_resp:
        return reference_resp
    else:
        return "No response available"