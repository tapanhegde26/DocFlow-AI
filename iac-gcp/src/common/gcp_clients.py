"""
GCP Client Utilities - Common module for GCP service interactions
Replaces AWS boto3 clients with Google Cloud SDK equivalents
"""

import os
import json
from typing import Optional, Dict, Any, List
from functools import lru_cache

from google.cloud import storage
from google.cloud import pubsub_v1
from google.cloud import secretmanager
from google.cloud import aiplatform
from google.cloud.sql.connector import Connector
import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel
import pg8000
import sqlalchemy


class GCPConfig:
    """Configuration for GCP services"""
    
    def __init__(self):
        self.project_id = os.environ.get("GCP_PROJECT")
        self.region = os.environ.get("REGION", "us-central1")
        self.vertex_model_id = os.environ.get("VERTEX_MODEL_ID", "gemini-1.5-pro")
        self.embedding_model_id = os.environ.get("VERTEX_EMBEDDING_MODEL", "text-embedding-004")


@lru_cache()
def get_config() -> GCPConfig:
    """Get cached GCP configuration"""
    return GCPConfig()


class StorageClient:
    """
    Google Cloud Storage client
    Replaces: boto3.client('s3')
    """
    
    def __init__(self):
        self.client = storage.Client()
    
    def get_object(self, bucket: str, key: str) -> bytes:
        """Download object from GCS"""
        bucket_obj = self.client.bucket(bucket)
        blob = bucket_obj.blob(key)
        return blob.download_as_bytes()
    
    def put_object(self, bucket: str, key: str, body: bytes, content_type: str = "application/octet-stream") -> Dict:
        """Upload object to GCS"""
        bucket_obj = self.client.bucket(bucket)
        blob = bucket_obj.blob(key)
        blob.upload_from_string(body, content_type=content_type)
        return {"bucket": bucket, "key": key}
    
    def list_objects(self, bucket: str, prefix: str = "") -> List[Dict]:
        """List objects in bucket"""
        bucket_obj = self.client.bucket(bucket)
        blobs = bucket_obj.list_blobs(prefix=prefix)
        return [{"Key": blob.name, "Size": blob.size} for blob in blobs]
    
    def delete_object(self, bucket: str, key: str) -> None:
        """Delete object from GCS"""
        bucket_obj = self.client.bucket(bucket)
        blob = bucket_obj.blob(key)
        blob.delete()


class PubSubClient:
    """
    Google Cloud Pub/Sub client
    Replaces: boto3.client('sqs')
    """
    
    def __init__(self):
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.config = get_config()
    
    def publish_message(self, topic_id: str, message: Dict) -> str:
        """Publish message to Pub/Sub topic"""
        topic_path = self.publisher.topic_path(self.config.project_id, topic_id)
        data = json.dumps(message).encode("utf-8")
        future = self.publisher.publish(topic_path, data)
        return future.result()
    
    def pull_messages(self, subscription_id: str, max_messages: int = 10) -> List[Dict]:
        """Pull messages from subscription"""
        subscription_path = self.subscriber.subscription_path(
            self.config.project_id, subscription_id
        )
        response = self.subscriber.pull(
            subscription=subscription_path,
            max_messages=max_messages
        )
        messages = []
        for msg in response.received_messages:
            messages.append({
                "ack_id": msg.ack_id,
                "data": json.loads(msg.message.data.decode("utf-8")),
                "attributes": dict(msg.message.attributes)
            })
        return messages
    
    def acknowledge(self, subscription_id: str, ack_ids: List[str]) -> None:
        """Acknowledge messages"""
        subscription_path = self.subscriber.subscription_path(
            self.config.project_id, subscription_id
        )
        self.subscriber.acknowledge(subscription=subscription_path, ack_ids=ack_ids)


class SecretManagerClient:
    """
    Google Cloud Secret Manager client
    Replaces: boto3.client('secretsmanager')
    """
    
    def __init__(self):
        self.client = secretmanager.SecretManagerServiceClient()
        self.config = get_config()
    
    def get_secret(self, secret_id: str, version: str = "latest") -> str:
        """Get secret value"""
        name = f"projects/{self.config.project_id}/secrets/{secret_id}/versions/{version}"
        response = self.client.access_secret_version(name=name)
        return response.payload.data.decode("utf-8")
    
    def get_secret_json(self, secret_id: str, version: str = "latest") -> Dict:
        """Get secret value as JSON"""
        secret_str = self.get_secret(secret_id, version)
        return json.loads(secret_str)


class VertexAIClient:
    """
    Vertex AI client for LLM and embeddings
    Replaces: boto3.client('bedrock-runtime')
    """
    
    def __init__(self):
        self.config = get_config()
        vertexai.init(project=self.config.project_id, location=self.config.region)
        self.llm_model = GenerativeModel(self.config.vertex_model_id)
        self.embedding_model = TextEmbeddingModel.from_pretrained(self.config.embedding_model_id)
    
    def generate_text(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.7) -> str:
        """
        Generate text using Vertex AI
        Replaces: bedrock.invoke_model() with Claude/Titan
        """
        response = self.llm_model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        return response.text
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using Vertex AI
        Replaces: bedrock.invoke_model() with Titan Embeddings
        """
        embeddings = self.embedding_model.get_embeddings(texts)
        return [emb.values for emb in embeddings]
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate single embedding"""
        embeddings = self.generate_embeddings([text])
        return embeddings[0]


class CloudSQLClient:
    """
    Cloud SQL client using Cloud SQL Connector
    Replaces: boto3.client('rds-data') or direct psycopg2 connection
    """
    
    def __init__(self, secret_id: str):
        self.secret_client = SecretManagerClient()
        self.credentials = self.secret_client.get_secret_json(secret_id)
        self.connector = Connector()
        self.engine = self._create_engine()
    
    def _create_engine(self) -> sqlalchemy.Engine:
        """Create SQLAlchemy engine with Cloud SQL Connector"""
        def getconn() -> pg8000.Connection:
            conn = self.connector.connect(
                self.credentials["connection_name"],
                "pg8000",
                user=self.credentials["username"],
                password=self.credentials["password"],
                db=self.credentials["database"],
            )
            return conn
        
        return sqlalchemy.create_engine(
            "postgresql+pg8000://",
            creator=getconn,
        )
    
    def execute(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute SQL query"""
        with self.engine.connect() as conn:
            result = conn.execute(sqlalchemy.text(query), params or {})
            if result.returns_rows:
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
            return []
    
    def execute_many(self, query: str, params_list: List[Dict]) -> int:
        """Execute SQL query with multiple parameter sets"""
        with self.engine.connect() as conn:
            for params in params_list:
                conn.execute(sqlalchemy.text(query), params)
            conn.commit()
        return len(params_list)
    
    def close(self):
        """Close connections"""
        self.connector.close()


class VectorSearchClient:
    """
    Vertex AI Vector Search client
    Replaces: opensearchpy client for AOSS
    """
    
    def __init__(self, index_endpoint_id: str, deployed_index_id: str):
        self.config = get_config()
        aiplatform.init(project=self.config.project_id, location=self.config.region)
        self.index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_id)
        self.deployed_index_id = deployed_index_id
    
    def upsert_vectors(self, vectors: List[Dict]) -> Dict:
        """
        Upsert vectors to index
        vectors: List of {"id": str, "embedding": List[float], "metadata": Dict}
        """
        datapoints = []
        for v in vectors:
            datapoints.append({
                "datapoint_id": v["id"],
                "feature_vector": v["embedding"],
                "restricts": [
                    {"namespace": k, "allow_list": [str(val)]}
                    for k, val in v.get("metadata", {}).items()
                ]
            })
        
        self.index_endpoint.upsert_datapoints(
            deployed_index_id=self.deployed_index_id,
            datapoints=datapoints
        )
        return {"upserted": len(vectors)}
    
    def search(self, query_embedding: List[float], top_k: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar vectors
        Replaces: OpenSearch knn query
        """
        restricts = []
        if filters:
            restricts = [
                {"namespace": k, "allow_list": [str(v)]}
                for k, v in filters.items()
            ]
        
        response = self.index_endpoint.find_neighbors(
            deployed_index_id=self.deployed_index_id,
            queries=[query_embedding],
            num_neighbors=top_k,
            filter=restricts if restricts else None
        )
        
        results = []
        for neighbor in response[0]:
            results.append({
                "id": neighbor.id,
                "score": neighbor.distance,
            })
        return results


# Convenience functions for common operations
def get_storage_client() -> StorageClient:
    """Get Storage client instance"""
    return StorageClient()


def get_pubsub_client() -> PubSubClient:
    """Get Pub/Sub client instance"""
    return PubSubClient()


def get_secret_manager_client() -> SecretManagerClient:
    """Get Secret Manager client instance"""
    return SecretManagerClient()


def get_vertex_ai_client() -> VertexAIClient:
    """Get Vertex AI client instance"""
    return VertexAIClient()


def get_cloud_sql_client(secret_id: str) -> CloudSQLClient:
    """Get Cloud SQL client instance"""
    return CloudSQLClient(secret_id)


def get_vector_search_client(index_endpoint_id: str, deployed_index_id: str) -> VectorSearchClient:
    """Get Vector Search client instance"""
    return VectorSearchClient(index_endpoint_id, deployed_index_id)
