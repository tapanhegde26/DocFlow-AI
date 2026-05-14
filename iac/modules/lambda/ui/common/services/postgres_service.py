import os
import psycopg2

from datetime import datetime, timezone
from common.utils.config import get_secret
from common.services.logger import log_to_cloudwatch

APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")
APP_NAME = os.getenv("APP_NAME")

# Environment configuration
region = os.environ.get("AWS_REGION", "ca-central-1")

def sanitize_for_json(obj):
    """
    Recursively convert datetimes and other non-JSON-serializable types 
    into safe strings so they can be logged.
    """
    from datetime import datetime
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, (list, tuple)):
        return tuple(sanitize_for_json(x) for x in obj)
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    else:
        return obj

def get_connection():
    host = os.getenv("PGHOST") #"host.docker.internal" for local testing only
    dbname = os.getenv("PGDATABASE")
    port = int(os.getenv("PGPORT", "5432"))
    secret_name = os.getenv("DB_SECRET_NAME")

    # Validate required environment variables
    if host is None:
        raise ValueError("Missing required environment variable: PGHOST")
    if dbname is None:
        raise ValueError("Missing required environment variable: PGDATABASE")
    if secret_name is None:
        raise ValueError("Missing required environment variable: DB_SECRET_NAME")

    secret_store = get_secret(secret_name)
    user = secret_store["username"]
    password = secret_store["password"]

    try:
        # Establish database connection
        conn = psycopg2.connect(
            host=host,
            dbname=dbname,
            user=user,
            password=password,
            port=int(port)
        )

        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
        raise

def run_query(log_group, query, params=None):
    print(f"{query}, {params}")
    """
    Execute a query that modifies data (INSERT, UPDATE, DELETE).
    Returns affected row count.
    """
    conn = get_connection()
    cur = conn.cursor()
    event_time = datetime.now(timezone.utc).isoformat()

    context = {}
    context["query"] = query
    context["params"] = params

    try:
        cur.execute(query, params)
        affected = cur.rowcount
        conn.commit()
        context["row_count"] = affected
        log_to_cloudwatch(
            APP_LOG_GROUP, 
            APP_NAME,
            f"Executed write query, query: {query}",
            "info",
            **context
        )
        print(f"printing affected: {affected}")
        return affected
    except Exception as e:
        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"Database write failed query={query}, params={params}, error={str(e)}",
            "error",
            **context
        )
        raise
    finally:
        cur.close()
        conn.close()

def run_query_results(log_group, query, params=None):
    print(f"{query}, {params}")
    """
    Execute a query that modifies data (INSERT, UPDATE, DELETE).
    Returns affected row count.
    """
    conn = get_connection()
    cur = conn.cursor()
    event_time = datetime.now(timezone.utc).isoformat()

    context = {}
    context["query"] = query
    context["params"] = params

    try:
        cur.execute(query, params)
        rows = cur.fetchone()[0]
        conn.commit()
        log_to_cloudwatch(
            APP_LOG_GROUP, 
            APP_NAME,
            f"Executed write query, query: {query}",
            "info",
            **context
        )
        print(f"printing rows: {rows}")
        return rows
    except Exception as e:
        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"Database write failed query={query}, params={params}, error={str(e)}",
            "error",
            **context
        )
        raise
    finally:
        cur.close()
        conn.close()

def fetch_query(query, params=None):
    """
    Execute a SELECT query and return results as list of dicts.
    """
    conn = get_connection()
    cur = conn.cursor()
    event_time = datetime.now(timezone.utc).isoformat()

    context = {}
    context["query"] = query
    context["params"] = params

    try:
        cur.execute(query, params)
        rows = cur.fetchall()
        context["row_count"] = len(rows)

        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"Executed query={query},params={params},row_count={len(rows)}",
            "info",
            **context
        )
        
        return rows

    except Exception as e:
        print(f"postgres_service.py: fetch_query:query: Caught an error: {e}")
        log_to_cloudwatch(
            APP_LOG_GROUP,
            APP_NAME,
            f"Database SELECT failed query={query},params={params},error={str(e)}",
            "error",
            **context
        )
        raise
    finally:
        cur.close()
        conn.close()