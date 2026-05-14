import json
from utils.shared_api import audit_event


def handle_review_audit(event):
    """
    Handle POST /reviews/audit by forwarding the payload
    to the shared audit Lambda function.
    """

    try:
        body = json.loads(event.get("body", "{}"))
        source_ip = event.get("requestContext", {}).get("http", {}).get("sourceIp", "unknown-ip")
        user_agent = event.get("requestContext", {}).get("http", {}).get("userAgent", "unknown-agent")

        #add source ip and user agent to body
        body["source_ip"] = source_ip
        body["user_agent"] = user_agent

        result = audit_event(body)

        return {
            "statusCode": 200,
            "body": json.dumps({"ok": True, "sharedResponse": result}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Audit logging failed", "error": str(e)}),
        }