import os
from typing import Any, Dict
from common.routes import logging_routes, feedback_routes, audit_routes

APP_NAME        = os.getenv("APP_NAME")

def insert_feedback(data: Dict[str, Any]) -> str:
    """Insert chat feedback and return its feedback_id."""
    enriched_data = {
        **data,
        "app": APP_NAME
    }

    result = feedback_routes.handle_insert_feedback(enriched_data)
    print(f"printing result: {result}")
    return result

def update_feedback_event(data: Dict[str, Any]) -> str:
    """Update chat feedback and return its feedback_id."""
    enriched_data = {
        **data,
        "app": APP_NAME
    }
    result = feedback_routes.handle_update_feedback(enriched_data)
    return result.get("feedback_id")

def audit_event(data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a generic audit event (login, client selection, query, etc.)."""
    enriched_data = {
        **data,
        "app": APP_NAME
    }
    return audit_routes.handle_audit(enriched_data)

def log_event(data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a generic log event (info, warning, error)."""

    enriched_data = {
        **data,
        "app": APP_NAME
    }
    return logging_routes.handle_log(enriched_data)