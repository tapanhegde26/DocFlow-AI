import json
import os
from services.llm_integration import query_bedrock_knowledgebase, LLMIntegration
from utils.shared_api import insert_feedback
from utils.shared_api import log_event

APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")
AUDIT_LOG_GROUP = os.getenv("AUDIT_LOG_GROUP")
APP_NAME = os.getenv("APP_NAME")

'''
Handles chat queries by interacting with Bedrock RAG and storing the query in the database.
NOW SUPPORTS BOTH:
- Traditional intelligent routing (existing functionality)
- NEW: Multi-agent LangGraph workflow for enhanced query processing

Uses intelligent routing to automatically select the appropriate knowledge base based on query content.
API Gateway will handle validating the JWT token.
The frontend will call this endpoint to submit a chat query and will pass in the following:
    - query: The user's chat query
    - user_id: The ID of the user making the request
    - client_name: The ID of the client making the request
    - use_agents: NEW - Boolean flag to enable multi-agent processing

This function returns the query_id and the generated response from Bedrock RAG.
'''

def handle_chat_query(event):
    """
    Enhanced chat query handler that supports both traditional and multi-agent processing.
    Uses intelligent routing to automatically select the appropriate knowledge base based on query content.
    """
    try:
        body = json.loads(event.get("body", "{}"))
        print(f"handle_chat_query: received body: {body}")
        
        query = body.get("query")
        user_id = body.get("user_id")
        client_name = body.get("client_name")
        
        # NEW: Check for multi-agent flag
        use_agents = body.get("use_agents", False)
        
        # NEW: Global feature flag override
        if os.environ.get("ENABLE_MULTI_AGENT", "false").lower() == "true":
            use_agents = True
        
        if not query:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"error": "Missing 'query'"})
            }

        log_event({
            "appName": APP_NAME,
            "message": f"chat_query.py: handle_chat_query: Processing query with {'multi-agent' if use_agents else 'traditional'} approach: {query}",
            "level": "info",
            "context": {
                "userId": user_id,
                "clientName": client_name,
                "query": query,
                "useAgents": use_agents  # NEW
            },
            "log_group": APP_LOG_GROUP,
        })

        # Call enhanced Bedrock RAG with automatic KB selection and optional multi-agent processing
        print(f"chat_query.py: calling query bedrock kb with query: {query}, use_agents: {use_agents}")
        bedrock_response = query_bedrock_knowledgebase(query, user_id, client_name, use_agents=use_agents)

        # Extract response and metadata (enhanced for multi-agent)
        generated_text = bedrock_response.get("response", "No response generated")
        confidence = bedrock_response.get("confidence", 0)
        source = bedrock_response.get("source", "unknown")
        query_type = bedrock_response.get("query_type", "general")
        citations = bedrock_response.get("citations", [])
        
        # NEW: Multi-agent specific metadata
        processing_mode = "multi-agent" if use_agents else "traditional"
        routing_decision = bedrock_response.get("routing_decision", {})
        agent_responses = bedrock_response.get("agent_responses", {})
        image_references = bedrock_response.get("image_references", [])
        llm_tags = bedrock_response.get("llm_tags", [])

        # Determine which KB was selected for logging/analytics (enhanced logic)
        is_process_query = False
        selected_kb = "unknown"
        
        if use_agents and routing_decision:
            # Multi-agent routing information
            primary_type = routing_decision.get("primary_type", "REFERENCE")
            is_process_query = primary_type in ["PROCESS", "BOTH"]
            
            if "multi-agent-synthesis" in source:
                selected_kb = "multi_agent_synthesis"
            elif "process-agent" in source:
                selected_kb = "process_agent_kb"
                is_process_query = True
            elif "reference-agent" in source:
                selected_kb = "reference_agent_kb"
            elif "fallback-llm" in source:
                selected_kb = "fallback_llm"
        else:
            # Traditional routing logic (existing)
            if "distinct-processes" in source:
                selected_kb = "distinct_processes_kb"
                is_process_query = True
            elif "non-distinct-processes" in source:
                selected_kb = "non_distinct_processes_kb"
                is_process_query = False
            elif "bedrock-llm" in source:
                is_process_query = False
                selected_kb = "direct_llm_fallback"

        feedback_id = None
        try:
            print("chat_query.py: Before call to insert_feedback")
            
            # Enhanced feedback data for multi-agent responses
            feedback_data = {
                "userId": user_id,
                "clientName": client_name,
                "query": query,
                "response": json.dumps(generated_text),
                "confidence": confidence,
                "source": source,
                "query_type": query_type,
                "selected_kb": selected_kb,
                "citations_count": len(citations),
                "is_process_query": is_process_query,
            }
            print(f"chat_query.py: feedback_data: {feedback_data}")
            
            # Add routing decision metadata if available
            if routing_decision:
                feedback_data["routing_confidence"] = routing_decision.get("confidence", 0)
                feedback_data["routing_primary_type"] = routing_decision.get("primary_type", "")
                feedback_data["routing_reasoning"] = routing_decision.get("reasoning", "")
            
            # Call the shared Lambda through insert_feedback to insert initial feedback record
            feedback_id = insert_feedback(feedback_data)
            print(f"Query successfully stored in database, feedback_id: {feedback_id}")
            
        except Exception as db_error:
            print(f"Failed to store query in database: {str(db_error)}")

        # Log routing decision and agent responses for internal tracking (not returned to user)
        if use_agents:
            log_event({
                "appName": APP_NAME,
                "message": f"Multi-agent routing decision and performance",
                "level": "info",
                "context": {
                    "userId": user_id,
                    "clientName": client_name,
                    "routing_decision": routing_decision,
                    "agent_responses": {
                        "process_confidence": agent_responses.get("process", {}).get("confidence", 0),
                        "reference_confidence": agent_responses.get("reference", {}).get("confidence", 0),
                        "process_citations_count": len(agent_responses.get("process", {}).get("citations", [])),
                        "reference_citations_count": len(agent_responses.get("reference", {}).get("citations", []))
                    }
                },
                "log_group": APP_LOG_GROUP,
            })
        
        # Clean response body - only essential fields for user
        response_body = {
            "feedback_id": feedback_id,
            "response": generated_text,
            "image_references": image_references,
            "llm_tags": llm_tags,
            "processing_mode": "multi-agent" if use_agents else "traditional"
        }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(response_body)
        }

    except Exception as e:
        # Log the error for debugging
        print(f"Error in handle_chat_query: {str(e)}")
        log_event({
            "appName": APP_NAME,
            "message": f"Error in handle_chat_query: {str(e)}",
            "level": "error",
            "context": {
                "userId": body.get("user_id", "unknown") if 'body' in locals() else "unknown",
                "clientName": body.get("client_name", "unknown") if 'body' in locals() else "unknown",
                "error": str(e)
            },
            "log_group": APP_LOG_GROUP,
        })
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e)
            })
        }


# Enhanced version with detailed logging for multi-agent workflows
def handle_chat_query_with_detailed_logging(event):
    """
    Enhanced version with comprehensive logging for both traditional and multi-agent approaches
    """
    try:
        body = json.loads(event.get("body", "{}"))
        query = body.get("query")
        user_id = body.get("user_id")
        client_name = body.get("client_name")
        use_agents = body.get("use_agents", False)
        
        # Global feature flag override
        if os.environ.get("ENABLE_MULTI_AGENT", "false").lower() == "true":
            use_agents = True
        
        if not query:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"error": "Missing 'query'"})
            }

        print(f"Processing query for user {user_id}, client {client_name} with {'multi-agent' if use_agents else 'traditional'} approach: {query}")

        # Use the LLMIntegration class directly for more control
        llm_integration = LLMIntegration()
        
        # Enhanced call with multi-agent support
        bedrock_response = llm_integration.query_bedrock_knowledgebase(
            query, user_id, client_name, use_agents=use_agents
        )

        # Extract all available information (enhanced for multi-agent)
        generated_text = bedrock_response.get("response", "No response generated")
        confidence = bedrock_response.get("confidence", 0)
        source = bedrock_response.get("source", "unknown")
        query_type = bedrock_response.get("query_type", "general")
        citations = bedrock_response.get("citations", [])
        routing_decision = bedrock_response.get("routing_decision", {})
        agent_responses = bedrock_response.get("agent_responses", {})
        
        is_process_query = query_type == "process-related"
        if routing_decision:
            is_process_query = routing_decision.get("primary_type") in ["PROCESS", "BOTH"]

        # Enhanced KB identification with multi-agent support
        kb_routing_info = {
            "selected_kb": "unknown",
            "routing_reason": "automatic_analysis",
            "is_process_query": is_process_query,
            "processing_mode": "multi-agent" if use_agents else "traditional"
        }

        if use_agents:
            # Multi-agent routing logic
            if "multi-agent-synthesis" in source:
                kb_routing_info["selected_kb"] = "multi_agent_synthesis"
                kb_routing_info["routing_reason"] = "multiple_agents_combined"
            elif "process-agent" in source:
                kb_routing_info["selected_kb"] = "process_agent_only"
                kb_routing_info["routing_reason"] = "process_specialized_agent"
            elif "reference-agent" in source:
                kb_routing_info["selected_kb"] = "reference_agent_only"
                kb_routing_info["routing_reason"] = "reference_specialized_agent"
            elif "fallback-llm" in source:
                kb_routing_info["selected_kb"] = "agent_fallback_llm"
                kb_routing_info["routing_reason"] = "agents_low_confidence"
        else:
            # Traditional routing logic
            if "distinct-processes" in source:
                kb_routing_info["selected_kb"] = "distinct_processes_kb"
                kb_routing_info["routing_reason"] = "process_keywords_detected"
            elif "non-distinct-processes" in source:
                kb_routing_info["selected_kb"] = "non_distinct_processes_kb"
                kb_routing_info["routing_reason"] = "general_query_classification"
            elif "bedrock-llm" in source:
                kb_routing_info["selected_kb"] = "direct_llm_fallback"
                kb_routing_info["routing_reason"] = "low_kb_confidence"

        print(f"Query routed to: {kb_routing_info['selected_kb']}, Reason: {kb_routing_info['routing_reason']}")
        print(f"Response confidence: {confidence}, Source: {source}")
        
        if use_agents and routing_decision:
            print(f"Router decision: {routing_decision.get('primary_type')}, Confidence: {routing_decision.get('confidence')}")
            print(f"Agent responses - Process: {agent_responses.get('process', {}).get('confidence', 0)}, Reference: {agent_responses.get('reference', {}).get('confidence', 0)}")

        # Store comprehensive query data with enhanced metadata
        feedback_data = {
            "userId": user_id,
            "clientName": client_name,
            "query": query,
            "response": json.dumps(generated_text),
            "confidence": confidence,
            "source": source,
            "query_type": query_type,
            "selected_kb": kb_routing_info["selected_kb"],
            "citations_count": len(citations),
            "is_process_query": is_process_query,
            "processing_mode": kb_routing_info["processing_mode"]
        }
        
        # Add routing metadata if available
        if routing_decision:
            feedback_data["routing_confidence"] = routing_decision.get("confidence", 0)
            feedback_data["routing_primary_type"] = routing_decision.get("primary_type", "")
        
        feedback_id = insert_feedback(feedback_data)
        print(f"Query successfully stored in database, feedback_id: {feedback_id}")

        response_body = {
            "feedback_id": feedback_id,
            "response": generated_text,
            "confidence": confidence,
            "query_type": query_type,
            "kb_info": kb_routing_info,
            "citations_count": len(citations),
            "processing_mode": kb_routing_info["processing_mode"]
        }
        
        # Include detailed multi-agent information
        if use_agents:
            response_body["routing_decision"] = routing_decision
            response_body["agent_performance"] = {
                "process_agent": agent_responses.get("process", {}),
                "reference_agent": agent_responses.get("reference", {})
            }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(response_body)
        }

    except Exception as e:
        print(f"Error in handle_chat_query_with_detailed_logging: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e)
            })
        }


# Enhanced simplified version with multi-agent support
def handle_chat_query_simple(event):
    """
    Simplified version that supports both traditional and multi-agent processing:
    - Automatic KB selection based on query content or multi-agent routing
    - Clean response format with optional agent metadata
    - Essential error handling
    """
    try:
        body = json.loads(event.get("body", "{}"))
        query = body.get("query", "").strip()
        user_id = body.get("user_id")
        client_name = body.get("client_name")
        use_agents = body.get("use_agents", False)
        
        # Global feature flag override
        if os.environ.get("ENABLE_MULTI_AGENT", "false").lower() == "true":
            use_agents = True
        
        if not query:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Query is required"})
            }

        # Enhanced automatic KB selection and query processing with optional multi-agent support
        response = query_bedrock_knowledgebase(query, user_id, client_name, use_agents=use_agents)
        
        print(f"chat_query.py:handle_chat_query_simple: calling insert feedback with {user_id}, {client_name}, {response.get('confidence', 0)}, {response.get('query_type', 'general')}")

        # Enhanced feedback data
        feedback_data = {
            "userId": user_id,
            "clientName": client_name,
            "query": query,
            "response": json.dumps(response.get("response", "No response generated")),
            "confidence": response.get("confidence", 0),
            "query_type": response.get("query_type", "general"),
            "citations_count": len(response.get("citations", [])),
            "processing_mode": "multi-agent" if use_agents else "traditional"
        }
        
        # Store in database
        feedback_id = insert_feedback(feedback_data)
        print(f"Query successfully stored in database, feedback_id: {feedback_id}")

        # Clean response with optional multi-agent metadata
        response_body = {
            "feedback_id": feedback_id,
            "response": response.get("response", "No response generated"),
            "confidence": response.get("confidence", 0),
            "query_type": response.get("query_type", "general"),
            "processing_mode": "multi-agent" if use_agents else "traditional"
        }
        
        # Include agent metadata if multi-agent was used
        if use_agents and response.get("routing_decision"):
            response_body["routing_summary"] = {
                "primary_type": response.get("routing_decision", {}).get("primary_type"),
                "confidence": response.get("routing_decision", {}).get("confidence")
            }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps(response_body)
        }

    except Exception as e:
        print(f"Error in handle_chat_query_simple: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Internal server error"})
        }
