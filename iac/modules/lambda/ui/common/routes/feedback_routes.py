import json
import os
from datetime import datetime, timezone
from common.services.postgres_service import run_query, run_query_results
from common.services.logger import log_to_cloudwatch

APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")
APP_NAME = os.getenv("APP_NAME")

"""
    process_feedback table

    feedback_id SERIAL PRIMARY KEY,  -- Auto-incrementing ID for feedback record
    client_id TEXT NOT NULL,  -- Identifier for the client owning the Process
    user_id TEXT,  -- Identifier for the user providing feedback (optional or anonymized)
    feedback_type TEXT CHECK (feedback_type IN ('up', 'down')),  -- Thumbs up or down - initial feedback record will not contain
    query TEXT NOT NULL,  -- The natural language query issued by the user
    source TEXT, -- The kb source for response
    confidence TEXT,  -- The confidence score for the response
    query_type TEXT, -- The context of the query
    selected_kb TEXT, -- The kb the response came from
    citations_count INTEGER, -- The number of citations the response has
    response TEXT NOT NULL,  -- The GenAI-generated response returned to the user
    feedback_comment TEXT,  -- Optional additional user comment
    is_process_query BOOLEAN, -- Optional indicates the context of the query is a process query
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Timestamp when the feedback was recorded
"""


def handle_insert_feedback(data: dict):
    """
    Insert a feedback record into process_feedbaclk table

    Expected payload:
    {
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
    }
    """
    
    # Validate input
    required_keys = ("userId", "clientName", "query", "response", "confidence", "source", "query_type", "selected_kb", "citations_count", "is_process_query")
    missing_keys = [k for k in required_keys if k not in data]

    if missing_keys:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": f"Missing required fields: {', '.join(missing_keys)}",
                "missing": missing_keys
            })
        }

    user_id = data.get("userId")
    clientName = data.get("clientName")
    query = data.get("query")
    response = data.get("response")
    confidence = data.get("confidence")
    source = data.get("source")
    query_type = data.get("query_type")
    selected_kb = data.get("selected_kb")
    citations_count = data.get("citations_count")
    is_process_query = data.get("is_process_query")
    
    context = {
        "client_name": clientName,
        "user_id": user_id
    }

    # Log to CloudWatch - context is empty
    log_to_cloudwatch( APP_LOG_GROUP, APP_NAME, f"Inserting initial feedback record : user_id: {user_id}, client_name: {clientName}", "info", None)

    # Insert into Postgres
    sql_query = """
        INSERT INTO process_feedback(client_id, user_id, query, source, confidence, query_type, selected_kb, citations_count, response, is_process_query)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING feedback_id;
    """
        
    result = run_query_results(APP_LOG_GROUP, sql_query, (
        clientName,
        user_id,
        query,
        source,
        str(confidence),
        query_type,
        selected_kb,
        citations_count,
        response,
        is_process_query
    ))
    print(f"printing result: {result}")
    feedback_id = result if result else None
    print(f"printing feedback_id: {feedback_id}")
    log_to_cloudwatch( APP_LOG_GROUP, APP_NAME, f'Updating feedback_id: {feedback_id}', level="INFO", **context)

    return feedback_id

def handle_update_feedback(data: dict):
    """
    Updates a feedback from frontend UI

    Expected payload:
    {
      feedback_id": "xxxxxxx"
      "feedback_type": "thumbs up",
      "feedback_comment": "xxxx xxxxx xxxxx",
      "ip_address": "10.0.0.5",
      "user_agent": "Mozilla/5.0",
      "context": {
        "user_id": "abc123",
        "client_name": "Client blah",
      }
    }

    """

    # Validate input
    required_keys = ("context", "feedback_id", "feedback_type", "feedback_comment")
    missing_keys = [k for k in required_keys if k not in data]

    if missing_keys:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": f"Missing required fields: {', '.join(missing_keys)}",
                "missing": missing_keys
            })
        }

    feedback_id = data.get("feedback_id")
    feedback_type = data.get("feedback_type")
    feedback_comment = data.get("feedback_comment")
    context = data.get("context")
    user_id = context["user_id"]


    # Log to CloudWatch
    log_to_cloudwatch( APP_LOG_GROUP, APP_NAME, f"Updating feedback_id: {feedback_id}", "info", **context)

    # Insert to Postgres
    query = """
        UPDATE process_feedback
        SET feedback_type = %s,
            feedback_comment = %s,
            submitted_at = %s
        WHERE feedback_id = %s AND user_id = %s
        RETURNING feedback_id
    """

    feedback_id = run_query_results(APP_LOG_GROUP, query, (
        feedback_type,
        feedback_comment,
        datetime.now(timezone.utc).isoformat(),
        feedback_id,
        user_id
    ))

    log_to_cloudwatch( APP_LOG_GROUP, APP_NAME, f"Successfully updated feedback_id: {feedback_id}, {feedback_id} rows affected", "info", **context)


    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Feedback updated successfully",
            "feedback_id": feedback_id
        })
    }

