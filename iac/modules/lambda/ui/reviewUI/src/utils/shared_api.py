import os
from typing import Any, Dict
from common.routes import process_routes, review_routes, logging_routes, audit_routes, status_routes

APP_NAME        = os.getenv("APP_NAME")

def get_processes(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get list of processed by client or process id."""
    enriched_data = {
        **data,
        "app": APP_NAME
    }
    result = process_routes.handle_process_routes(enriched_data)
    return result

def insert_review(data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a review into the process_review_history table"""
    enriched_data = {
        **data,
        "app": APP_NAME
    }
    result = review_routes.handle_insert_review(enriched_data)
    return result

def get_reviews(data: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve review into the process_review_history table"""
    enriched_data = {
        **data,
        "app": APP_NAME
    }
    result = review_routes.handle_get_reviews(enriched_data)
    return result

def get_latest_review(data: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve latest review into the process_review_history table"""
    enriched_data = {
        **data,
        "app": APP_NAME
    }
    result = review_routes.handle_get_latest_review(enriched_data)
    return result

def update_state(data: Dict[str, Any]) -> Dict[str, Any]:
    """Update document state in PostgreSQL and OpenSearch"""
    enriched_data = {
        **data,
        "app": APP_NAME
    }
    result = status_routes.handle_status_routes(enriched_data)
    return result


def audit_event(data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a generic audit event (login, client selection, query, etc.)."""
    enriched_data = {
        **data,
        "appName": APP_NAME
    }
    return audit_routes.handle_audit(enriched_data)

def log_event(data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a generic log event (info, warning, error)."""
    enriched_data = {
        **data,
        "app": APP_NAME
    }
    return logging_routes.handle_log(enriched_data)
