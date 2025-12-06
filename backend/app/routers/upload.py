"""
MedGuard AI - Upload Router
Phase 3: Backend Skeleton

Handles file uploads (CSV and PDF).
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import pandas as pd
import shutil
from datetime import datetime

from ..models.schemas import UploadResponse

router = APIRouter()

# Upload directory
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload provider data file (CSV or PDF).
    
    - **file**: CSV file with provider data or PDF documents
    
    Returns upload confirmation with file metadata.
    """
    try:
        # Validate file type
        allowed_extensions = ['.csv', '.pdf']
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / safe_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = file_path.stat().st_size
        
        # If CSV, count rows
        rows_detected = None
        if file_ext == '.csv':
            try:
                df = pd.read_csv(file_path)
                rows_detected = len(df)
            except Exception as e:
                # File saved but couldn't parse - still return success
                pass
        
        return UploadResponse(
            success=True,
            filename=safe_filename,
            file_size=file_size,
            rows_detected=rows_detected,
            message=f"File uploaded successfully: {safe_filename}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/uploads")
async def list_uploads():
    """
    List all uploaded files.
    
    Returns list of uploaded files with metadata.
    """
    try:
        files = []
        
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # Sort by creation time (newest first)
        files.sort(key=lambda x: x['created'], reverse=True)
        
        return {
            "total": len(files),
            "files": files
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list uploads: {str(e)}"
        )


@router.delete("/upload/{filename}")
async def delete_upload(filename: str):
    """
    Delete uploaded file.
    
    - **filename**: Name of file to delete
    
    Returns deletion confirmation.
    """
    try:
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {filename}"
            )
        
        file_path.unlink()
        
        return {
            "success": True,
            "message": f"File deleted: {filename}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )
