import re
import json

def extract_user_info(event):
    username = extract_username(event)
    client_name = extract_client_name(event)

    try:
        role = extract_role(event, client_name)
    except Exception as e:
        print(f"reviewUI:extract_user_info: FAILED TO EXTRACT ROLE: {e}")
        role = "unknown_role"

    return {
        "username": username,
        "client_name": client_name,
        "role": role
    }

def has_role(role, allowed_roles):
    return role in allowed_roles

def extract_username(event):
    headers = normalize_headers(event.get("headers", {}))
    body = parse_body(event)
    claims = get_jwt_claims(event)

    return (
        claims.get("preferred_username")
        or headers.get("x-user-id")
        or body.get("user_id")
        or "unknown_user"
    )

def extract_client_name(event):
    headers = normalize_headers(event.get("headers", {}))
    body = parse_body(event)
    claims = get_jwt_claims(event)
    query_params = event.get("queryStringParameters") or {}

    client_name = (
        query_params.get("clientName")
        or headers.get("x-client-id")
        or body.get("client_name")
    )

    if not client_name and "rbac-tsh-industries" in claims:
        try:
            rbac_raw = claims["rbac-tsh-industries"]
            parsed_claim = parse_rbac_claim(rbac_raw)
            if parsed_claim:
                clients = parsed_claim.get("clients", [])
                client_names = [c.get("clientName") for c in clients]
                client_name = client_names[-1] if client_names else None
    
        except Exception:
            pass

    return client_name or "unknown_client"

def extract_role(event, client_name):
    headers = normalize_headers(event.get("headers", {}))
    body = parse_body(event)
    claims = get_jwt_claims(event)
    role = body.get("role") or headers.get("x-role")

    # Try rbac-tsh-industries
    if not role and "rbac-tsh-industries" in claims:
        try:
            rbac_raw = claims["rbac-tsh-industries"]
            
            # Look for the matching clientName block
            # Example match: clientName:Conservice Two roles:[map[name:Admin]]
            pattern = rf"clientName:{re.escape(client_name)}[^\]]*roles:\[(.*?)\]"
            match = re.search(pattern, rbac_raw)

            if match:
                roles_block = match.group(1)  # roles block e.g. map[name:Admin]
                role_match = re.search(r"name:([A-Za-z0-9_\-]+)", roles_block)
                if role_match:
                    role = role_match.group(1)

        except Exception as e:
            print(f"extract_role: error parsing rbac-tsh-industries: {e}")
   

    return role or "unknown_role"

def parse_body(event):
    if event.get("httpMethod", "").upper() == "POST" and event.get("body"):
        try:
            return json.loads(event["body"])
        except Exception:
            return {}
    return {}

def normalize_headers(headers):
    return {k.lower(): v for k, v in (headers or {}).items()}

def get_jwt_claims(event):
    return (
        event.get("requestContext", {})
             .get("authorizer", {})
             .get("jwt", {})
             .get("claims", {})
    )

def parse_rbac_claim(claim_value: str):
    """
    Converts a Go-style RBAC claim string into a real Python dictionary.
    Example input:
    "map[clients:[map[clientId:1 clientName:Conservice One roles:[map[name:Admin]]] map[clientId:2 clientName:Conservice Two roles:[map[name:Admin]]]]]"
    """
    # Step 1 — Convert Go 'map[' and ']' into JSON-style braces
    json_like = (
        claim_value
        .replace('map[', '{')
        .replace(']', '}')
        .replace('[', '[')
    )

    # Step 2 — Insert quotes around keys and values
    # Add quotes around keys (clientId:, clientName:, roles:, name:)
    json_like = re.sub(r'(\w+):', r'"\1":', json_like)
    # Add quotes around barewords that are not numbers, brackets, or braces
    json_like = re.sub(r'([:\s])([A-Za-z][A-Za-z0-9\s\-]*)', lambda m: f'{m.group(1)}"{m.group(2).strip()}"', json_like)

    # Step 3 — Fix nested object/list separators (spaces between objects → commas)
    json_like = re.sub(r'(\})(\s*)(\{)', r'\1,\3', json_like)
    json_like = re.sub(r'(\}|\])(\s+)(\{|\[)', r'\1,\3', json_like)

    # Step 4 — Attempt JSON parsing
    try:
        parsed = json.loads(json_like)

    except json.JSONDecodeError as e:
        print("Failed to decode RBAC claim:", e)
        parsed = None
    return parsed