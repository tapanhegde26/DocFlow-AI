import json
from utils.shared_api import update_feedback_event

'''
Handles chat feedback by storing user feedback in the database.
API Gateway will handle validating the JWT token.

The frontend will call this endpoint to submit feedback and will pass in the following:
    - feedback_id: The feedback_if from the query response
    - feedback_type: Optional type of feedback (e.g., "thumbs up", "thumbs down")
    - feedback_comment: Optional comment from the user regarding the feedback
    - user_id: The ID of the user providing the feedback
    - client_name: The ID of the client making the request

This function returns a confirmation message and the ID of the recorded feedback.
'''
def handle_chat_feedback(event):

    try:
        body = json.loads(event.get("body", "{}"))
        source_ip = event.get("requestContext", {}).get("http", {}).get("sourceIp", "unknown-ip")
        user_agent = event.get("requestContext", {}).get("http", {}).get("userAgent", "unknown-agent")

        # #add source ip and user agent to body
        # body["source_ip"] = source_ip
        # body["user_agent"] = user_agent
        # updated_id = update_feedback_event(body)

        #add source ip and user agent to body
        body["source_ip"] = source_ip
        body["user_agent"] = user_agent
        print(f"body sent to handle_chat_feedback: {json.dumps(body)}")
        updated_id = update_feedback_event(body)
        print(f"update_id is: {update_id}")

        return {
            "statusCode": 200,
            "body": json.dumps({"ok": True, "feedback_id": updated_id})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Updating feedback failed", "error": str(e)}),
        }
