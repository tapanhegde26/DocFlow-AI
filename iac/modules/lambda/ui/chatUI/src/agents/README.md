# Multi-Agent RAG System Documentation

## Overview

This is a **multi-agent Retrieval-Augmented Generation (RAG) system** built with LangGraph that intelligently routes user queries to specialized knowledge bases and synthesizes comprehensive responses. The system uses AWS Bedrock for LLM capabilities and manages multiple knowledge bases for different types of information.

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     User Query Input                         │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    Router Agent                              │
│  • Classifies query intent (PROCESS/REFERENCE/BOTH)         │
│  • Keyword + LLM-based classification                        │
│  • Determines routing strategy                               │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
         ┌─────────────┴─────────────┐
         ↓                           ↓
┌──────────────────┐        ┌──────────────────┐
│  Process Agent   │        │ Reference Agent  │
│  • Workflows     │        │  • Branding      │
│  • Procedures    │        │  • Tone          │
│  • Step-by-step  │        │  • Policies      │
└────────┬─────────┘        └────────┬─────────┘
         └─────────────┬─────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  Synthesizer Agent                           │
│  • Combines multi-source responses                           │
│  • Eliminates redundancy                                     │
│  • Preserves metadata & citations                            │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              Final Response with Metadata                    │
└─────────────────────────────────────────────────────────────┘
```

---

## File Descriptions

### 1. `__init__.py`
Empty initialization file for the agents package.

---

### 2. `base_agent.py`

**Purpose**: Abstract base class providing common functionality for all agents.

**Key Features**:
- AWS Bedrock client initialization (runtime and agent runtime)
- Common LLM invocation method
- Centralized logging functionality

**Main Methods**:
```python
class BaseAgent(ABC):
    def __init__(self):
        # Initializes Bedrock clients
        
    @abstractmethod
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Must be implemented by child classes
        
    def _invoke_bedrock_model(self, prompt: str) -> str:
        # Invokes Claude model via Bedrock
        
    def _log_event(self, message: str, level: str, context: Dict[str, Any]):
        # Logs events with context
```

**Environment Variables**:
- `AWS_REGION` - AWS region (default: ca-central-1)
- `BEDROCK_MODEL_ID` - Model ID (default: anthropic.claude-3-sonnet-20240229-v1:0)
- `MAX_TOKENS` - Max tokens for LLM response (default: 1000)
- `APP_NAME` - Application name for logging
- `APP_LOG_GROUP` - CloudWatch log group

---

### 3. `router_agent.py`

**Purpose**: Classifies incoming queries and determines routing strategy.

**Classification Categories**:
- **PROCESS**: Procedural questions (workflows, how-to, step-by-step)
- **REFERENCE**: Branding, tone, policies, general information
- **BOTH**: Queries requiring both types of information

**Classification Strategy**:
1. **Keyword-based**: Matches against process-related keywords
2. **LLM-based**: Uses Claude to classify with reasoning
3. **Confidence scoring**: Combines both approaches

**Process Keywords**:
```python
['process', 'procedure', 'workflow', 'step', 'steps', 'how to',
 'implementation', 'execute', 'perform', 'conduct', 'carry out',
 'methodology', 'approach', 'protocol', 'guideline', 'instruction']
```

**State Updates**:
```python
{
    'routing_decision': {
        'is_process_related': bool,
        'needs_reference': bool,
        'primary_type': 'PROCESS|REFERENCE|BOTH',
        'confidence': float,
        'reasoning': str
    },
    'needs_process_kb': bool,
    'needs_reference_kb': bool,
    'confidence': float
}
```

**Example Flow**:
```
Query: "How do I escalate a customer complaint?"
  ↓
Keyword Analysis: High process keyword match
  ↓
LLM Classification: PROCESS (confidence: 0.9)
  ↓
Routing Decision: needs_process_kb = True
```

---

### 4. `process_agent.py`

**Purpose**: Retrieves procedural and workflow information from the process knowledge base.

**Knowledge Base**: `DISTINCT_PROCESSES_KB_ID`

**Focus Areas**:
- Step-by-step procedures
- Workflow instructions
- Implementation guidelines
- Process documentation

**Special Features**:
- **Image Reference Extraction**: Parses `<image_references>` tags
- **LLM Tag Extraction**: Parses `<llm_tags>` tags
- **Citation-based Confidence**: Scores based on number of citations

**Confidence Scoring**:
```python
Citations >= 3  → 0.9 confidence
Citations >= 2  → 0.7 confidence
Citations >= 1  → 0.5 confidence
Citations == 0  → 0.3 confidence
```

**State Updates**:
```python
{
    'process_response': str,
    'process_citations': List[Dict],
    'process_confidence': float,
    'process_image_references': List[str],
    'process_llm_tags': List[str]
}
```

**Environment Variables**:
- `DISTINCT_PROCESSES_KB_ID` - Process knowledge base ID
- `BEDROCK_MODEL_ARN` - Model ARN for KB queries
- `VECTOR_SEARCH_RESULTS` - Number of results (default: 5)

---

### 5. `reference_agent.py`

**Purpose**: Retrieves branding, tone, and reference information.

**Knowledge Base**: `NON_DISTINCT_PROCESSES_KB_ID`

**Focus Areas**:
- Branding guidelines
- Tone and voice
- Company policies
- General reference materials
- Background information

**Fallback Mechanism**:
- Primary KB: `NON_DISTINCT_PROCESSES_KB_ID`
- Fallback KB: `BEDROCK_KNOWLEDGE_BASE_ID` (if primary fails)

**State Updates**:
```python
{
    'reference_response': str,
    'reference_citations': List[Dict],
    'reference_confidence': float,
    'used_fallback': bool  # If fallback KB was used
}
```

**Environment Variables**:
- `NON_DISTINCT_PROCESSES_KB_ID` - Reference knowledge base ID
- `BEDROCK_KNOWLEDGE_BASE_ID` - Default/fallback KB ID
- `BEDROCK_MODEL_ARN` - Model ARN for KB queries
- `VECTOR_SEARCH_RESULTS` - Number of results (default: 5)

---

### 6. `synthesizer_agent.py`

**Purpose**: Combines and synthesizes responses from multiple agents into a coherent answer.

**Synthesis Strategies**:

1. **Multi-Agent Synthesis** (Both responses available):
   - Uses LLM to combine process + reference responses
   - Eliminates redundancy
   - Preserves important details from both sources
   - Maintains flow and readability

2. **Single-Agent Pass-through** (One response available):
   - Returns the available response directly
   - Marks source appropriately

3. **Fallback LLM** (No KB responses):
   - Generates response using direct LLM
   - Indicates general guidance disclaimer

**Synthesis Prompt Strategy**:
```
1. Combine most relevant information from both sources
2. Eliminate redundancy while preserving details
3. Maintain proper flow and readability
4. Preserve image references and tags
5. Ensure branding consistency
6. Indicate information sources
```

**State Updates**:
```python
{
    'final_response': str,
    'final_source': 'multi-agent-synthesis|process-agent|reference-agent|fallback-llm',
    'final_confidence': float,
    'all_citations': List[Dict],
    'image_references': List[str],
    'llm_tags': List[str],
    'synthesis_complete': bool
}
```

---

### 7. `langgraph_workflow.py`

**Purpose**: Orchestrates the entire multi-agent workflow using LangGraph.

**Workflow Graph**:
```
START
  ↓
Router Agent (classify query)
  ↓
Conditional Routing:
  ├─ process_only → Process Agent → Synthesizer
  ├─ reference_only → Reference Agent → Synthesizer
  ├─ both → Process Agent → Reference Agent → Synthesizer
  └─ synthesizer → Direct to Synthesizer (fallback)
  ↓
END
```

**State Schema** (`AgentWorkflowState`):
```python
{
    # Input
    'query': str,
    'user_id': str,
    'client_name': str,
    
    # Routing
    'routing_decision': Dict,
    'needs_process_kb': bool,
    'needs_reference_kb': bool,
    
    # Agent Responses
    'process_response': str,
    'reference_response': str,
    'process_confidence': float,
    'reference_confidence': float,
    'process_citations': List,
    'reference_citations': List,
    'process_image_references': List,
    'process_llm_tags': List,
    
    # Final Output
    'final_response': str,
    'final_source': str,
    'final_confidence': float,
    'all_citations': List,
    'image_references': List,
    'llm_tags': List,
    'synthesis_complete': bool,
    'errors': List
}
```

**Conditional Edge Functions**:

1. **`_decide_agents()`**: After router
   - Returns: `"both"`, `"process_only"`, `"reference_only"`, or `"synthesizer"`

2. **`_after_process()`**: After process agent
   - Returns: `"reference_agent"` or `"synthesizer"`

**Main Entry Point**:
```python
def invoke(query: str, user_id: str, client_name: str, **kwargs) -> Dict[str, Any]:
    """
    Main execution method
    
    Returns:
        {
            'response': str,
            'source': str,
            'confidence': float,
            'citations': List,
            'image_references': List,
            'llm_tags': List,
            'routing_decision': Dict,
            'agent_responses': {
                'process': {...},
                'reference': {...}
            }
        }
    """
```

**Global Instance**:
```python
_multi_agent_workflow = MultiAgentWorkflow()

def get_workflow() -> MultiAgentWorkflow:
    """Get the global workflow instance"""
    return _multi_agent_workflow
```

---

## Complete Workflow Example

### Example 1: Process Query

**Input**:
```python
query = "How do I escalate a customer complaint?"
user_id = "user123"
client_name = "ClientA"
```

**Execution Flow**:
```
1. Router Agent
   ├─ Keyword match: "escalate" → process-related
   ├─ LLM classification: PROCESS (confidence: 0.9)
   └─ Decision: needs_process_kb = True

2. Process Agent
   ├─ Query DISTINCT_PROCESSES_KB_ID
   ├─ Retrieve: "Escalation Procedure" document
   ├─ Extract: 3 citations, 2 image references
   └─ Confidence: 0.9

3. Synthesizer Agent
   ├─ Single source (process only)
   └─ Pass-through response

4. Output
   ├─ Response: Detailed escalation steps
   ├─ Source: "process-agent"
   ├─ Confidence: 0.9
   └─ Citations: [3 documents]
```

---

### Example 2: Multi-Source Query

**Input**:
```python
query = "What's our brand voice for handling refund requests?"
```

**Execution Flow**:
```
1. Router Agent
   ├─ Keywords: "brand voice" + "refund requests"
   ├─ LLM classification: BOTH (confidence: 0.85)
   └─ Decision: needs_process_kb = True, needs_reference_kb = True

2. Process Agent
   ├─ Query: Refund procedures
   ├─ Response: Step-by-step refund process
   └─ Confidence: 0.8

3. Reference Agent
   ├─ Query: Brand voice guidelines
   ├─ Response: Tone, empathy guidelines
   └─ Confidence: 0.9

4. Synthesizer Agent
   ├─ Combine both responses
   ├─ LLM synthesis: Merge procedures + brand voice
   └─ Result: Comprehensive answer with both aspects

5. Output
   ├─ Response: "When handling refunds, follow these steps [process]
   │             while maintaining [brand voice guidelines]..."
   ├─ Source: "multi-agent-synthesis"
   ├─ Confidence: 0.9 (max of both)
   └─ Citations: [5 documents from both KBs]
```

---

## Configuration

### Required Environment Variables

```bash
# AWS Configuration
AWS_REGION=ca-central-1

# Bedrock Model Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_MODEL_ARN=arn:aws:bedrock:ca-central-1::foundation-model/...
MAX_TOKENS=1000

# Knowledge Base IDs
DISTINCT_PROCESSES_KB_ID=<process-kb-id>
NON_DISTINCT_PROCESSES_KB_ID=<reference-kb-id>
BEDROCK_KNOWLEDGE_BASE_ID=<fallback-kb-id>

# Search Configuration
VECTOR_SEARCH_RESULTS=5

# Logging Configuration
APP_NAME=TSH-Industries-ChatUI
APP_LOG_GROUP=/aws/lambda/chatui
```

---

## Usage

### Basic Usage

```python
from agents.langgraph_workflow import get_workflow

# Get workflow instance
workflow = get_workflow()

# Execute query
result = workflow.invoke(
    query="How do I process a refund?",
    user_id="user123",
    client_name="ClientA"
)

# Access results
print(result['response'])
print(f"Confidence: {result['confidence']}")
print(f"Source: {result['source']}")
print(f"Citations: {len(result['citations'])}")
```

### Response Structure

```python
{
    'response': str,              # Final synthesized answer
    'source': str,                # 'multi-agent-synthesis', 'process-agent', 
                                  # 'reference-agent', or 'fallback-llm'
    'confidence': float,          # 0.0 - 1.0
    'citations': [                # List of source citations
        {
            'retrievedReferences': [...],
            'generatedResponsePart': {...}
        }
    ],
    'image_references': [str],    # List of image URLs/references
    'llm_tags': [str],           # Metadata tags
    'routing_decision': {         # Router classification details
        'is_process_related': bool,
        'needs_reference': bool,
        'primary_type': str,
        'confidence': float,
        'reasoning': str
    },
    'agent_responses': {          # Individual agent responses
        'process': {
            'response': str,
            'confidence': float,
            'citations': [...]
        },
        'reference': {
            'response': str,
            'confidence': float,
            'citations': [...]
        }
    }
}
```

---

## Key Features

### 1. Intelligent Query Routing
- Dual classification (keyword + LLM)
- Confidence-based decision making
- Fallback mechanisms at every level

### 2. Parallel Knowledge Base Querying
- Process and reference agents can run in sequence
- Optimized for LangGraph's execution model

### 3. Response Synthesis
- LLM-based combination of multiple sources
- Redundancy elimination
- Metadata preservation

### 4. Comprehensive Logging
- Event logging at every stage
- Context-rich log messages
- CloudWatch integration

### 5. Graceful Error Handling
- Fallback to alternative KBs
- Direct LLM fallback when KBs fail
- Error state tracking

### 6. Metadata Management
- Citation tracking from all sources
- Image reference extraction
- LLM tag preservation

---

## Error Handling

### Agent-Level Errors
Each agent handles its own errors and updates state:
```python
try:
    result = self._query_kb(...)
    state.update({'response': result})
except Exception as e:
    state.update({
        'response': None,
        'error': str(e),
        'confidence': 0
    })
```

### Workflow-Level Errors
The workflow catches top-level errors and returns error response:
```python
{
    'response': 'I apologize, but I encountered an error...',
    'source': 'error',
    'confidence': 0,
    'error': str(e)
}
```

---

## Performance Considerations

### Optimization Strategies
1. **Conditional Execution**: Only runs necessary agents
2. **Citation Caching**: Reuses citations across synthesis
3. **Confidence Thresholds**: Early termination for low-confidence results
4. **Vector Search Limits**: Configurable result counts

### Typical Execution Times
- Router Agent: ~1-2 seconds
- Process Agent: ~3-5 seconds (KB query)
- Reference Agent: ~3-5 seconds (KB query)
- Synthesizer: ~2-3 seconds (LLM synthesis)
- **Total**: ~5-15 seconds (depending on routing)

---

## Testing

### Unit Testing Individual Agents

```python
from agents.router_agent import RouterAgent

router = RouterAgent()
state = {
    'query': 'How do I escalate?',
    'user_id': 'test',
    'client_name': 'test'
}
result = router.execute(state)
assert result['needs_process_kb'] == True
```

### Integration Testing Workflow

```python
from agents.langgraph_workflow import get_workflow

workflow = get_workflow()
result = workflow.invoke(
    query="Test query",
    user_id="test",
    client_name="test"
)
assert 'response' in result
assert result['confidence'] > 0
```

---

## Troubleshooting

### Common Issues

1. **No KB Results**
   - Check KB IDs are correct
   - Verify KB has indexed documents
   - Review vector search configuration

2. **Low Confidence Scores**
   - Increase `VECTOR_SEARCH_RESULTS`
   - Review query phrasing
   - Check KB document quality

3. **Synthesis Errors**
   - Verify Bedrock model access
   - Check token limits
   - Review prompt templates

4. **Routing Issues**
   - Add more process keywords
   - Adjust confidence thresholds
   - Review LLM classification prompts

---

## Future Enhancements

### Potential Improvements
1. **Caching Layer**: Cache frequent queries
2. **Parallel Agent Execution**: Run process + reference in parallel
3. **Dynamic Prompt Templates**: Customize per client
4. **Feedback Loop**: Learn from user feedback
5. **A/B Testing**: Test different synthesis strategies
6. **Streaming Responses**: Stream LLM outputs
7. **Multi-language Support**: Handle non-English queries

---

## Contributing

When adding new agents:
1. Inherit from `BaseAgent`
2. Implement `execute(state)` method
3. Update state with results
4. Add logging at key points
5. Handle errors gracefully
6. Update workflow graph in `langgraph_workflow.py`

---

## License

Internal use only - TSH Industries Project

---

## Contact

For questions or issues, contact the development team.
