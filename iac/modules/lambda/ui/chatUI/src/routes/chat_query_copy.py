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
Uses intelligent routing to automatically select the appropriate knowledge base based on query content.
Uses intelligent routing to automatically select the appropriate knowledge base based on query content.
API Gateway will handle validating the JWT token.
The frontend will call this endpoint to submit a chat query and will pass in the following:
    - query: The user's chat query
    - user_id: The ID of the user making the request
    - client_name: The ID of the client making the request

This function returns the query_id and the generated response from Bedrock RAG.
'''


def handle_chat_query(event):
    """
    Handles chat queries by interacting with Bedrock RAG and storing the query in the database.
    Uses intelligent routing to automatically select the appropriate knowledge base based on query content.
    """
    try:
        body = json.loads(event.get("body", "{}"))
        print(f"handle_chat_query: received body: {body}")
        query = body.get("query")
        user_id = body.get("user_id")
        client_name = body.get("client_name")

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
            "message": f"chat_query.py: handle_chat_query: Processing query: {query}",
            "level": "info",
            "context": {
                "userId": user_id,
                "clientName": client_name,
                "query": query
            },
            "log_group": APP_LOG_GROUP,
        })

        # Call enhanced Bedrock RAG with automatic KB selection
        print(f"chat_query.py: calling query bedrock kb with query: {query}")
        bedrock_response = query_bedrock_knowledgebase(query, user_id, client_name)

        # Extract response and metadata
        generated_text = bedrock_response.get("response", "No response generated")
        confidence = bedrock_response.get("confidence", 0)
        source = bedrock_response.get("source", "unknown")
        query_type = bedrock_response.get("query_type", "general")
        citations = bedrock_response.get("citations", [])

        # Determine which KB was selected for logging/analytics
        is_process_query = False
        selected_kb = "unknown"
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
            # Call the shared Lambda through insert_feedback to insert initial feedback record
            # Store query in DB with enhanced metadata
            feedback_id = insert_feedback({
                "userId": user_id,
                "clientName": client_name,
                "query": query,
                "response": generated_text,
                "confidence": confidence,
                "source": source,
                "query_type": query_type,
                "selected_kb": selected_kb,
                "citations_count": len(citations),
                "is_process_query": is_process_query
            })

            print(f"Query successfully stored in database, feedback_id: {feedback_id}")
        except Exception as db_error:
            print(f"Failed to store query in database: {str(db_error)}")


        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "feedback_id": feedback_id,
                "response": generated_text,
                "confidence": confidence,
                "source": source,
                "query_type": query_type,
                "selected_kb": selected_kb,
                "citations_count": len(citations)
            })
        }

    except Exception as e:
        # Log the error for debugging
        print(f"Error in handle_chat_query: {str(e)}")

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

# Alternative implementation with more detailed logging
def handle_chat_query_with_detailed_logging(event):
    try:
        body = json.loads(event.get("body", "{}"))
        query = body.get("query")
        user_id = body.get("user_id")
        client_name = body.get("client_name")

        if not query:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"error": "Missing 'query'"})
            }

        print(f"Processing query for user {user_id}, client {client_name}: {query}")

        # Use the LLMIntegration class directly for more control
        llm_integration = LLMIntegration()

        # This will automatically:
        # 1. Analyze query intent (process vs general)
        # 2. Route to appropriate KB (distinct_processes_kb vs non_distinct_processes_kb)
        # 3. Fallback to direct LLM if needed
        bedrock_response = llm_integration.query_bedrock_knowledgebase(query)

        # Extract all available information
        generated_text = bedrock_response.get("response", "No response generated")
        confidence = bedrock_response.get("confidence", 0)
        source = bedrock_response.get("source", "unknown")
        query_type = bedrock_response.get("query_type", "general")
        citations = bedrock_response.get("citations", [])
        is_process_query = query_type == "process-related"

        # Enhanced KB identification
        kb_routing_info = {
            "selected_kb": "unknown",
            "routing_reason": "automatic_analysis",
            "is_process_query": is_process_query
        }

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

        # Store comprehensive query data.
        feedback_id = insert_feedback({
                "userId": user_id,
                "clientName": client_name,
                "query": query,
                "response": generated_text,
                "confidence": confidence,
                "source": source,
                "query_type": query_type,
                "selected_kb": kb_routing_info["selected_kb"],
                "citations_count": len(citations),
                "is_process_query": is_process_query
            })

        print(f"Query successfully stored in database, feedback_id: {feedback_id}")
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "feedback_id": feedback_id,
                "response": generated_text,
                "confidence": confidence,
                "query_type": query_type,
                "kb_info": kb_routing_info,
                "citations_count": len(citations)
            })
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

# Simplified version for production use
def handle_chat_query_simple(event):
    """
    Simplified version that focuses on the core functionality:
    - Automatic KB selection based on query content
    - Clean response format
    - Essential error handling
    """
    try:
        body = json.loads(event.get("body", "{}"))
        query = body.get("query", "").strip()
        user_id = body.get("user_id")
        client_name = body.get("client_name")

        if not query:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Query is required"})
            }

        # Automatic KB selection and query processing
        response = query_bedrock_knowledgebase(query)

        print(f"llm_integration.py:handle_chat_query_simple: calling insert feedback with {user_id}, {client_name}, {response.get("confidence", 0)}", response.get("query_type", "general"))
        # Store in database
        feedback_id = insert_feedback({
                "userId": user_id,
                "clientName": client_name,
                "query": query,
                "response": response,
                "confidence": response.get("confidence", 0),
                "query_type": response.get("query_type", "general"),
                "citations_count": 0 # needed for db insert, an integer type can not be None          
            })
        print(f"Query successfully stored in database, feedback_id: {feedback_id}")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "feedback_id": feedback_id,
                "response": response.get("response", "No response generated"),
                "confidence": response.get("confidence", 0),
                "query_type": response.get("query_type", "general")
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Internal server error"})
        }