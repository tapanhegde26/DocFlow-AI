from datetime import datetime, timezone
from common.services.postgres_service import fetch_query, run_query
from common.services.logger import log_to_cloudwatch
import os

APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")
APP_NAME = os.getenv("APP_NAME")

def insert_review(review: dict):
    """
    Insert a new process review history entry.

    Expects dict:
    {
        "process_id": "uuid",
        "reviewer": "user123",
        "previous_status": "draft",
        "new_status": "review",
        "comments": "Looks good",
        "process_diff": {"before": "...", "after": "..."},  # optional
        "flags": { "missingSteps": true, "deadEnd": false } # optional JSON
    }
    """
    query = """
        INSERT INTO process_review_history (
            process_id, reviewer, previous_status, new_status,
            comments, process_diff, flags
        )
        VALUES (%(process_id)s, %(reviewer)s, %(previous_status)s,
                %(new_status)s, %(comments)s, %(process_diff)s,%(flags)s)
    """
    affected = run_query(query, review)

    log_to_cloudwatch(
        APP_NAME,
        "Inserted process review history entry",
        process_id=review.get("process_id"),
        reviewer=review.get("reviewer"),
        previous_status=review.get("previous_status"),
        new_status=review.get("new_status"),
        flags=review.get("flags"),
        affected=affected,
        event_time=datetime.now(timezone.utc).isoformat()
    )
    return affected


def get_reviews_by_process(process_id: str):
    """
    Get all review history entries for a given process.
    """
    query = """
        SELECT review_id, process_id, reviewer, previous_status,
               new_status, comments, process_diff, flags, reviewed_at
        FROM process_review_history
        WHERE process_id = %s
        ORDER BY reviewed_at DESC
    """
    rows = fetch_query(query, (process_id,))

    log_to_cloudwatch(
        APP_NAME,
        "Fetched review history",
        process_id=process_id,
        count=len(rows),
        event_time=datetime.now(timezone.utc).isoformat()
    )
    return rows


def get_latest_review(process_id: str):
    """
    Get the most recent review entry for a given process.
    """
    query = """
        SELECT review_id, process_id, reviewer, previous_status,
               new_status, comments, process_diff, flags, reviewed_at
        FROM process_review_history
        WHERE process_id = %s
        ORDER BY reviewed_at DESC
        LIMIT 1
    """
    rows = fetch_query(query, (process_id,))
    latest = rows[0] if rows else None

    log_to_cloudwatch(
        APP_NAME,
        "Fetched latest review entry",
        process_id=process_id,
        found=bool(latest),
        event_time=datetime.now(timezone.utc).isoformat()
    )
    return latest