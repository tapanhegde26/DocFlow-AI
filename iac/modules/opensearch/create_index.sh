#!/bin/bash
set -e

ENDPOINT="$1"
INDEX_NAME="$2"
REGION="$3"

echo "Creating OpenSearch index: $INDEX_NAME"
echo "Endpoint: $ENDPOINT"
echo "Region: $REGION"

# Validate arguments
if [ -z "$ENDPOINT" ] || [ -z "$INDEX_NAME" ] || [ -z "$REGION" ]; then
    echo "Error: Missing required arguments"
    echo "Usage: $0 <endpoint> <index_name> <region>"
    exit 1
fi

# Create temporary virtual environment
TEMP_VENV="/tmp/opensearch_venv_$$"
echo "Creating virtual environment at $TEMP_VENV"

python3 -m venv "$TEMP_VENV"
source "$TEMP_VENV/bin/activate"

echo "Installing required Python packages in virtual environment..."
pip config set global.index-url https://pypi.org/simple/
pip config set global.trusted-host pypi.org
pip install -q requests requests-aws4auth boto3

echo "Creating index..."

# Pass arguments as environment variables to Python
export OPENSEARCH_ENDPOINT="$ENDPOINT"
export OPENSEARCH_INDEX="$INDEX_NAME"
export OPENSEARCH_REGION="$REGION"

python3 << 'EOF'
import sys
import boto3
import requests
from requests_aws4auth import AWS4Auth
import json
import os

def create_index():
    try:
        # Get arguments from environment variables
        endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
        index_name = os.environ.get('OPENSEARCH_INDEX') 
        region = os.environ.get('OPENSEARCH_REGION')
        
        print(f"Endpoint: {endpoint}")
        print(f"Index: {index_name}")
        print(f"Region: {region}")
        
        if not all([endpoint, index_name, region]):
            print("Error: Missing required environment variables")
            return False
        
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if not credentials:
            print("Error: No AWS credentials found")
            return False
            
        print("AWS credentials found successfully")
        
        auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'aoss',
            session_token=credentials.token
        )
        
        # First, check if index already exists
        check_url = f"{endpoint}/{index_name}"
        check_response = requests.get(check_url, auth=auth, timeout=30)
        
        if check_response.status_code == 200:
            print(f"Index {index_name} already exists. Checking if it needs updating...")
            # Optionally, you could check the mapping and update if needed
            print(f"Index {index_name} is ready for use.")
            return True
        
        # Index doesn't exist, create it
        mapping = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100
                }
            },
            "mappings": {
                "properties": {
                    "text": {"type": "text", "analyzer": "standard"},
                    "bedrock-knowledge-base-default-vector": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "engine": "faiss", 
                            "space_type": "l2",
                            "parameters": {
                                "ef_construction": 512,
                                "m": 16
                            }
                        }
                    },
                    "chunk_id": {"type": "keyword"},
                    "metadata": {"type": "object", "enabled": True},
                    "original_metadata": {"type": "object", "enabled": True},
                    "timestamp": {"type": "date"},
                    "created_date": {"type": "date"},
                    "created_timestamp": {"type": "date"},
                    "client_name": {"type": "keyword"},
                    "provider_name": {"type": "keyword"},
                    "source_document_url": {"type": "keyword", "index": False},
                    "llm_tags": {"type": "keyword"},
                    "process_uuid": {"type": "keyword"},
                    "process_id": {"type": "keyword"},
                    "process_name": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "processing_info": {"type": "object", "enabled": True},
                    "AMAZON_BEDROCK_METADATA": {"type": "text", "index": True},
                    "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text", "index": True}
                }
            }
        }
        
        print(f"Making request to create index: {check_url}")
        
        response = requests.put(
            check_url,
            auth=auth,
            headers={'Content-Type': 'application/json'},
            json=mapping,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code in [200, 201]:
            print(f"Successfully created index: {index_name}")
            return True
        elif response.status_code == 400:
            # Check if it's because index already exists
            response_data = response.json()
            if "resource_already_exists_exception" in response.text:
                print(f"Index {index_name} already exists - this is OK")
                return True
            else:
                print(f"Failed to create index due to bad request: {response_data}")
                return False
        else:
            print(f"Failed to create index: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_index()
    sys.exit(0 if success else 1)
EOF

# Cleanup
deactivate
rm -rf "$TEMP_VENV"

if [ $? -eq 0 ]; then
    echo "Index creation/verification completed successfully"
else
    echo "Index creation failed"
    exit 1
fi
