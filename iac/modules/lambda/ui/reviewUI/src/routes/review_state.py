import json
import os
from utils.user import extract_user_info
from utils.shared_api import log_event, audit_event, update_state

APP_LOG_GROUP   = os.getenv("APP_LOG_GROUP")
AUDIT_LOG_GROUP = os.getenv("AUDIT_LOG_GROUP")
APP_NAME        = os.getenv("APP_NAME")

def handle_process_state_change(event):

    try:
        raw_body = event.get("body", "{}")
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body

        source_ip = event.get("requestContext", {}).get("http", {}).get("sourceIp", "unknown-ip")
        user_agent = event.get("requestContext", {}).get("http", {}).get("userAgent", "unknown-agent")

        #add source ip and user agent to body
        body["source_ip"] = source_ip
        body["user_agent"] = user_agent

        # get data from event
        process_id = body.get("process_id")
        old_state = body.get("old_state")
        new_state = body.get("new_state")    
        client_name = body.get("client_name")
        user_id = body.get("user_id")
        process_url = body.get("process_url")
        document_type = body.get("document_type")

        # Add audit event
        audit_event({
            "appName": APP_NAME,
            "message": f"User, {user_id}, logged in using client: {client_name} is changing the state of process_id: {process_id} with process_url: {process_url} and document_type: {document_type} from: {old_state} to {new_state}",
            "level": "info",
            "context": {
                "user_id": user_id,
                "client_name": client_name
            }
        })

        # Add log event
        log_event({
            "appName": APP_NAME,
            "message": f"User, {user_id}, logged in using client: {client_name} is changing the state of process_id: {process_id} with process_url: {process_url}  and document_type: {document_type} from: {old_state} to {new_state}",
            "level": "info",
            "context": {
                "user_id": user_id,
                "client_name": client_name
            }
        })

        # Update state in DB & OpenSearch
        pResults = update_state(body)
        if (pResults):
            return {"statusCode": 200, "body": json.dumps({"message": "Process state updated"})}


    except Exception as e:
        print("Exception in handle_process_state_change:", str(e))
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}