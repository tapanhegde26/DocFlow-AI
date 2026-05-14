import json
from datetime import datetime, timezone
import os
from common.services.postgres_service import run_query
from common.services.opensearch_service import find_document_by_type_and_url, delete_document
from common.services.s3_service import write_s3_file
from common.services.logger import log_to_cloudwatch
from utils.user import extract_user_info, has_role

APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")
AUDIT_LOG_GROUP = os.getenv("AUDIT_LOG_GROUP")
APP_NAME = os.getenv("APP_NAME")

def handle_get_review_history(event):
    """Fetch all reviews for a process_id"""
    user = extract_user_info(event)
    role = user.get("role")

    # Only admin or approver can view review history
    if not has_role(role, ["admin", "approver"]):
        return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}

    params = event.get("pathParameters", {}) or {}
    process_id = params.get("process_id")
    if not process_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing process_id"})}

    reviews = query_reviews_by_process(process_id)
    return {"statusCode": 200, "body": json.dumps(reviews)}

def handle_get_latest_review(event):
    """Fetch latest review for a process_id"""
    user = extract_user_info(event)
    role = user.get("role")

    if not has_role(role, ["admin", "approver"]):
        return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}

    params = event.get("pathParameters", {}) or {}
    process_id = params.get("process_id")
    if not process_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing process_id"})}

    review = query_latest_review(process_id)
    if not review:
        return {"statusCode": 404, "body": json.dumps({"error": "No reviews found"})}

    return {"statusCode": 200, "body": json.dumps(review)}

def handle_create_review(event):
    """
    Insert a new review record

    POST /reviews/signed-url
    Body: { "process_id": "xxxxxx", reviewer: "xxxxx", client: "xxxx",  payload: {flags: xxxx, content: xxxx, comments: xxxxx} }
    Returns: { review id  }
    """

    print(f"reviewUI:review_history.py:handle_create_review: event: {json.dumps(event)}")

    try:
        body = json.loads(event.get("body", "{}"))
        print(f"reviewUI:review_history.py:handle_create_review: body: {body}")

    except json.JSONDecodeError:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON body"})}

    process_id = body.get("process_id")
    print(f"reviewUI:review_history.py:handle_create_review: process_id: {process_id}")

    if not process_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing process_id"})}

    status = body.get("status")
    print(f"reviewUI:review_history.py:handle_create_review: status: {status}")

    process_url = body.get("process_url")
    print(f"reviewUI:review_history.py:handle_create_review: process_url: {process_url}")

    reviewer = body.get("reviewer")
    print(f"reviewUI:review_history.py:handle_create_review: reviewer: {reviewer}")

    client_name = body.get("client")
    print(f"reviewUI:review_history.py:handle_create_review: client_name: {client_name}")

    payload = body.get("payload")
    print(f"reviewUI:review_history.py:handle_create_review: payload: {json.dumps(payload)}")
    
    flags = payload.get("flags", {})
    print(f"reviewUI:review_history.py:handle_create_review: flags : {flags}")

    comments = payload.get("comments", "") # only sent if there is as change
    print(f"reviewUI:review_history.py:handle_create_review: comments: {comments}")

    content_diff = payload.get("content", "") # only sent if there is as change
    print(f"reviewUI:review_history.py:handle_create_review: content diff: {content_diff}")

    full_content = payload.get("editableContent", "") # only sent if there is as change
    print(f"reviewUI:review_history.py:handle_create_review: full_content: {full_content}")
 
    # Update flags in process table
    if (flags != {}):
        print(f"reviewUI:review_history.py:handle_create_review: we have updated flags")

        # Update status in process table into Postgres
        sql_query = """
            UPDATE processes 
            SET flags = %s, updated_at = %s
            WHERE client_id = %s AND process_id = %s
            RETURNING process_id;
        """ 
        print(f"reviewUI:review_history.py:handle_create_review: flags query: {sql_query}")

        try: 
            # Update postgresql
            fResult = run_query(APP_LOG_GROUP, sql_query, (
                json.dumps(flags), 
                datetime.now(timezone.utc).isoformat(),
                client_name,
                process_id
            ))
            print(f"reviewUI:review_history.py:handle_create_review: result insert fResult: {fResult}")
        except Exception as e:
            print(f"ERROR during run_query: {e}")
            return {"statusCode": 500, "body": json.dumps({"error": "Internal error during flag update"})}
 
    # Insert new review record into review history
    sql_query = """
        INSERT INTO process_review_history (process_id, new_status, reviewer, comments, process_diff, reviewed_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    try: 
        hResult = run_query(APP_LOG_GROUP, sql_query, (
            process_id,
            status,
            reviewer, 
            comments,
            json.dumps(content_diff), 
            datetime.now(timezone.utc).isoformat(),
        ))

        print(f"reviewUI:review_history.py:handle_create_review: result of insert into process_review_history: {hResult}")
    except Exception as e:
        print(f"ERROR during run_query: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal error during flag update"})}

    
    # update opensearch & generate new s3 file
    if (content_diff != ""):
        print("reviewUI:review_history.py:handle_create_review: the content was updated write file back out to S3 bucket")

        # use opensearch_service/find_document_by_type_and_url to find documents that are derived from the process_url
        results = find_document_by_type_and_url("process", client_name, process_url)

        if results:
            print(f"Found {len(results)} documents to delete for file: {process_url}")
            for hit in results:
                hit_index = hit["_index"]
                hit_id = hit["_id"]
                print(f"reviewUI: review_history.py: handle_create_review: inside for loop, deleting hit: {hit}")
    
                # use opensearch+service/delete_document to delete all of the documents found
                try:
                    response = delete_document(
                        doc_type = "process",
                        doc_id=hit_id
                    )
                    print(f"Deleted document_id:{hit["_id"]} in index:{hit["_index"]} with the a response: {response}")
                except Exception as e:
                    print(f"Failed to delete document_is: {hit["_id"]}: {e}")
        else:
            print(f"No documents found for {process_url} to delete.")

        # write updated content back to S3 process url file
        print(f"reviewUI: review_history.py: handle_create_review: before updating file: {process_url}")
        s3Response = write_s3_file(process_url, full_content)
        print(f"reviewUI: review_history.py: handle_create_review: after updating file, s3 response : {s3Response}")


    print(f"reviewUI:review_history.py:handle_create_review: returning: {hResult}")
    return {"statusCode": 201, "body": json.dumps({"rows": hResult })}


def query_reviews_by_process(process_id):
    return [
        {
            "review_id": 1,
            "process_id": process_id,
            "reviewer": "test.approver",
            "previous_status": "draft",
            "new_status": "review",
            "comments": "Checked step 2",
            "flags": ["Missing Steps"],
            "reviewed_at": "2025-09-22T10:00:00Z",
        }
    ]

def query_latest_review(process_id):
    reviews = query_reviews_by_process(process_id)
    return reviews[0] if reviews else None
