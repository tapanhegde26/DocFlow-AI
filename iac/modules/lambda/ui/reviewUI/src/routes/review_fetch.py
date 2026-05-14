import json
from utils.user import extract_user_info, has_role
from utils.shared_api import get_processes

def handle_fetch_processes(event):
    """Fetch all documents"""
    # Extract query parameter from GET ?clientName=xxx
    query_params = event.get("queryStringParameters") or {}
    client_name = query_params.get("clientName")

    user = extract_user_info(event)
    role = user.get("role")

    if not client_name or not has_role(role.lower(), ["admin", "approver"]):
        return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}

    context =  {
                "userId": user,
                "clientName": client_name,
                "role": role
            }
    processes = query_processes_by_client(client_name, context)
    return {"statusCode": 200, "body": json.dumps(processes)}

def query_processes_by_client(client_name, context):
    """Fetch process by id"""
    data = get_processes({"query": {"client_name": client_name}, "context": context})
    return data

    
    