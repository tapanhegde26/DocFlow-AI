from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph import Graph
from typing_extensions import TypedDict
from .router_agent import RouterAgent
from .process_agent import ProcessAgent
from .reference_agent import ReferenceAgent
from .synthesizer_agent import SynthesizerAgent
import os
from utils.shared_api import log_event

class AgentWorkflowState:
    """State management for the agent workflow"""
    
    def __init__(self):
        self.query: str = ""
        self.user_id: str = ""
        self.client_name: str = ""
        self.routing_decision: Dict[str, Any] = {}
        self.needs_process_kb: bool = False
        self.needs_reference_kb: bool = False
        self.process_response: str = None
        self.reference_response: str = None
        self.process_confidence: float = 0
        self.reference_confidence: float = 0
        self.process_citations: List = []
        self.reference_citations: List = []
        self.process_image_references: List = []
        self.process_llm_tags: List = []
        self.final_response: str = ""
        self.final_source: str = ""
        self.final_confidence: float = 0
        self.all_citations: List = []
        self.image_references: List = []
        self.llm_tags: List = []
        self.synthesis_complete: bool = False
        self.errors: List = []

class MultiAgentWorkflow:
    """LangGraph-based multi-agent workflow"""
    
    def __init__(self):
        self.router_agent = RouterAgent()
        self.process_agent = ProcessAgent()
        self.reference_agent = ReferenceAgent()
        self.synthesizer_agent = SynthesizerAgent()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Define the state schema
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("router", self._route_query)
        workflow.add_node("process_agent", self._process_query)
        workflow.add_node("reference_agent", self._reference_query)
        workflow.add_node("synthesizer", self._synthesize_response)
        
        # Define edges and conditional routing
        workflow.set_entry_point("router")
        
        # Router decides which agents to call
        workflow.add_conditional_edges(
            "router",
            self._decide_agents,
            {
                "process_only": "process_agent",
                "reference_only": "reference_agent", 
                "both": "process_agent",  # Start with process, then reference
                "synthesizer": "synthesizer"  # Direct to synthesizer if no KB needed
            }
        )
        
        # Process agent can go to reference agent or synthesizer
        workflow.add_conditional_edges(
            "process_agent",
            self._after_process,
            {
                "reference_agent": "reference_agent",
                "synthesizer": "synthesizer"
            }
        )
        
        # Reference agent always goes to synthesizer
        workflow.add_edge("reference_agent", "synthesizer")
        
        # Synthesizer is the end
        workflow.add_edge("synthesizer", END)
        
        return workflow.compile()
    
    def _route_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Router node execution"""
        return self.router_agent.execute(state)
    
    def _process_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process agent node execution"""
        return self.process_agent.execute(state)
    
    def _reference_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Reference agent node execution"""
        return self.reference_agent.execute(state)
    
    def _synthesize_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesizer node execution"""
        return self.synthesizer_agent.execute(state)
    
    def _decide_agents(self, state: Dict[str, Any]) -> str:
        """Conditional edge function to decide which agents to call"""
        needs_process = state.get('needs_process_kb', False)
        needs_reference = state.get('needs_reference_kb', False)
        
        if needs_process and needs_reference:
            return "both"
        elif needs_process:
            return "process_only"
        elif needs_reference:
            return "reference_only"
        else:
            return "synthesizer"  # Direct to synthesizer for fallback
    
    def _after_process(self, state: Dict[str, Any]) -> str:
        """Conditional edge function after process agent"""
        needs_reference = state.get('needs_reference_kb', False)
        
        if needs_reference:
            return "reference_agent"
        else:
            return "synthesizer"
    
    def invoke(self, query: str, user_id: str, client_name: str, **kwargs) -> Dict[str, Any]:
        """Main invoke method for the workflow"""
        
        # Log workflow start
        log_event({
            "appName": os.getenv("APP_NAME"),
            "message": f"MultiAgentWorkflow: Starting workflow for query",
            "level": "info",
            "context": {
                "userId": user_id,
                "clientName": client_name,
                "query": query
            },
            "log_group": os.getenv("APP_LOG_GROUP"),
        })
        
        # Initialize state
        initial_state = {
            'query': query,
            'user_id': user_id,
            'client_name': client_name,
            'routing_decision': {},
            'needs_process_kb': False,
            'needs_reference_kb': False,
            'process_response': None,
            'reference_response': None,
            'process_confidence': 0,
            'reference_confidence': 0,
            'process_citations': [],
            'reference_citations': [],
            'process_image_references': [],
            'process_llm_tags': [],
            'final_response': "",
            'final_source': "",
            'final_confidence': 0,
            'all_citations': [],
            'image_references': [],
            'llm_tags': [],
            'synthesis_complete': False,
            'errors': []
        }
        
        try:
            # Execute the workflow
            final_state = self.workflow.invoke(initial_state)
            
            # Format response to match existing API
            response = {
                'response': final_state.get('final_response', ''),
                'source': final_state.get('final_source', 'multi-agent'),
                'confidence': final_state.get('final_confidence', 0),
                'citations': final_state.get('all_citations', []),
                'image_references': final_state.get('image_references', []),
                'llm_tags': final_state.get('llm_tags', []),
                'routing_decision': final_state.get('routing_decision', {}),
                'agent_responses': {
                    'process': {
                        'response': final_state.get('process_response'),
                        'confidence': final_state.get('process_confidence', 0),
                        'citations': final_state.get('process_citations', [])
                    },
                    'reference': {
                        'response': final_state.get('reference_response'),
                        'confidence': final_state.get('reference_confidence', 0),
                        'citations': final_state.get('reference_citations', [])
                    }
                }
            }
            
            log_event({
                "appName": os.getenv("APP_NAME"),
                "message": f"MultiAgentWorkflow: Workflow completed successfully",
                "level": "info",
                "context": {
                    "userId": user_id,
                    "clientName": client_name,
                    "finalSource": final_state.get('final_source'),
                    "confidence": final_state.get('final_confidence')
                },
                "log_group": os.getenv("APP_LOG_GROUP"),
            })
            
            return response
            
        except Exception as e:
            error_msg = f"MultiAgentWorkflow: Error executing workflow: {str(e)}"
            log_event({
                "appName": os.getenv("APP_NAME"),
                "message": error_msg,
                "level": "error",
                "context": {
                    "userId": user_id,
                    "clientName": client_name,
                    "error": str(e)
                },
                "log_group": os.getenv("APP_LOG_GROUP"),
            })
            
            return {
                'response': 'I apologize, but I encountered an error while processing your request. Please try again.',
                'source': 'error',
                'confidence': 0,
                'error': str(e),
                'citations': [],
                'image_references': [],
                'llm_tags': []
            }

# Global instance
_multi_agent_workflow = MultiAgentWorkflow()

def get_workflow() -> MultiAgentWorkflow:
    """Get the global workflow instance"""
    return _multi_agent_workflow
