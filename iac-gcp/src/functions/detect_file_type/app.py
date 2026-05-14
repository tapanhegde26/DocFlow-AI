"""
Detect File Type - Cloud Run Service
Migrated from AWS Lambda to GCP Cloud Run

This service detects the type of uploaded files (PDF, Office documents, etc.)
"""

import os
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import magic

# Import GCP clients
import sys
sys.path.append('/app')
from common.gcp_clients import get_storage_client

# Configure logging
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="Detect File Type Service")

# Initialize clients
storage_client = get_storage_client()


class DetectRequest(BaseModel):
    bucket: str
    object_name: str


class DetectResponse(BaseModel):
    file_type: str
    mime_type: str
    bucket: str
    object_name: str


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/detect", response_model=DetectResponse)
async def detect_file_type(request: DetectRequest) -> DetectResponse:
    """
    Detect the type of a file in Cloud Storage
    
    Equivalent to AWS Lambda handler that detects file types from S3
    """
    try:
        logger.info(f"Detecting file type for gs://{request.bucket}/{request.object_name}")
        
        # Download first 2KB of file for type detection
        file_content = storage_client.get_object(
            bucket=request.bucket,
            key=request.object_name
        )
        
        # Use python-magic for MIME type detection
        mime = magic.Magic(mime=True)
        mime_type = mime.from_buffer(file_content[:2048])
        
        # Map MIME type to file type category
        file_type = _get_file_type(mime_type, request.object_name)
        
        logger.info(f"Detected file type: {file_type}, MIME: {mime_type}")
        
        return DetectResponse(
            file_type=file_type,
            mime_type=mime_type,
            bucket=request.bucket,
            object_name=request.object_name
        )
        
    except Exception as e:
        logger.error(f"Error detecting file type: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_file_type(mime_type: str, filename: str) -> str:
    """Map MIME type to file type category"""
    
    # PDF files
    if mime_type == "application/pdf":
        return "pdf"
    
    # Microsoft Office files
    office_types = [
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ]
    if mime_type in office_types:
        return "office"
    
    # Text files
    if mime_type.startswith("text/"):
        return "text"
    
    # Check file extension as fallback
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    
    if ext == "pdf":
        return "pdf"
    elif ext in ["doc", "docx", "xls", "xlsx", "ppt", "pptx"]:
        return "office"
    elif ext in ["txt", "md", "csv"]:
        return "text"
    
    return "unknown"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
