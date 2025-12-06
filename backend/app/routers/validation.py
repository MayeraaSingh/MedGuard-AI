"""
MedGuard AI - Validation Router
Phase 3: Backend Skeleton

Handles validation pipeline triggers and status checks.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from datetime import datetime
import uuid
from typing import Dict, Any

from ..models.schemas import (
    ValidationRequest, 
    ValidationJobResponse, 
    ValidationStatusResponse,
    ValidationStatus,
    ValidationResultSummary
)

router = APIRouter()

# In-memory job storage (will move to Redis in production)
validation_jobs: Dict[str, Dict[str, Any]] = {}


@router.post("/start-validation", response_model=ValidationJobResponse)
async def start_validation(
    request: ValidationRequest,
    background_tasks: BackgroundTasks
):
    """
    Start validation pipeline for uploaded provider data.
    
    - **file_path**: Path to uploaded CSV file
    - **batch_size**: Number of providers to process in batch (default: 10)
    
    Returns job ID for tracking validation progress.
    """
    try:
        # Validate file exists
        file_path = Path(request.file_path)
        if not file_path.exists():
            # Try relative to data/uploads
            file_path = Path("data/uploads") / request.file_path
            if not file_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"File not found: {request.file_path}"
                )
        
        # Create job
        job_id = str(uuid.uuid4())
        
        validation_jobs[job_id] = {
            "job_id": job_id,
            "status": ValidationStatus.PENDING,
            "file_path": str(file_path),
            "batch_size": request.batch_size,
            "created_at": datetime.now(),
            "progress": 0.0,
            "providers_processed": 0,
            "providers_total": 0,
            "started_at": None,
            "completed_at": None,
            "error": None,
            "results": None
        }
        
        # Add validation task to background
        background_tasks.add_task(run_validation_pipeline, job_id, str(file_path), request.batch_size)
        
        return ValidationJobResponse(
            job_id=job_id,
            status=ValidationStatus.PENDING,
            created_at=validation_jobs[job_id]["created_at"],
            message=f"Validation job created: {job_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start validation: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=ValidationStatusResponse)
async def get_validation_status(job_id: str):
    """
    Get validation job status and progress.
    
    - **job_id**: Validation job ID
    
    Returns current status, progress, and timing information.
    """
    if job_id not in validation_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )
    
    job = validation_jobs[job_id]
    
    # Calculate duration if completed
    duration_seconds = None
    if job["started_at"] and job["completed_at"]:
        duration_seconds = (job["completed_at"] - job["started_at"]).total_seconds()
    
    return ValidationStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        providers_processed=job["providers_processed"],
        providers_total=job["providers_total"],
        started_at=job["started_at"],
        completed_at=job["completed_at"],
        duration_seconds=duration_seconds,
        error=job["error"]
    )


@router.get("/results/{job_id}")
async def get_validation_results(job_id: str):
    """
    Get validation results for completed job.
    
    - **job_id**: Validation job ID
    
    Returns complete validation results with summary statistics.
    """
    if job_id not in validation_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )
    
    job = validation_jobs[job_id]
    
    if job["status"] != ValidationStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed yet. Status: {job['status']}"
        )
    
    if not job.get("results"):
        raise HTTPException(
            status_code=500,
            detail="Results not available"
        )
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "duration_seconds": (job["completed_at"] - job["started_at"]).total_seconds(),
        "results": job["results"]
    }


@router.get("/jobs")
async def list_validation_jobs():
    """
    List all validation jobs.
    
    Returns list of all jobs with their current status.
    """
    jobs_list = []
    
    for job_id, job in validation_jobs.items():
        duration_seconds = None
        if job["started_at"] and job["completed_at"]:
            duration_seconds = (job["completed_at"] - job["started_at"]).total_seconds()
        
        jobs_list.append({
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "created_at": job["created_at"].isoformat(),
            "duration_seconds": duration_seconds
        })
    
    # Sort by creation time (newest first)
    jobs_list.sort(key=lambda x: x['created_at'], reverse=True)
    
    return {
        "total": len(jobs_list),
        "jobs": jobs_list
    }


async def run_validation_pipeline(job_id: str, file_path: str, batch_size: int):
    """
    Background task to run validation pipeline.
    
    Args:
        job_id: Job identifier
        file_path: Path to CSV file
        batch_size: Batch size for processing
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    try:
        from app.orchestrator_adk import AgentOrchestratorADK
        import pandas as pd
        
        # Update job status
        validation_jobs[job_id]["status"] = ValidationStatus.PROCESSING
        validation_jobs[job_id]["started_at"] = datetime.now()
        
        # Load providers
        df = pd.read_csv(file_path)
        providers = df.to_dict('records')
        validation_jobs[job_id]["providers_total"] = len(providers)
        
        # Run orchestrator
        orchestrator = AgentOrchestratorADK()
        
        # Process in batches with progress updates
        all_results = {
            "validation_results": [],
            "enrichment_results": [],
            "qa_results": [],
            "directory_summary": {}
        }
        
        for i in range(0, len(providers), batch_size):
            batch = providers[i:i+batch_size]
            summary = orchestrator.process_providers(batch)
            
            # Append results
            all_results["validation_results"].extend(summary["validation_results"])
            all_results["enrichment_results"].extend(summary["enrichment_results"])
            all_results["qa_results"].extend(summary["qa_results"])
            all_results["directory_summary"] = summary["directory_summary"]
            
            # Update progress
            validation_jobs[job_id]["providers_processed"] = min(i + batch_size, len(providers))
            validation_jobs[job_id]["progress"] = (validation_jobs[job_id]["providers_processed"] / len(providers)) * 100
        
        # Mark completed
        validation_jobs[job_id]["status"] = ValidationStatus.COMPLETED
        validation_jobs[job_id]["completed_at"] = datetime.now()
        validation_jobs[job_id]["progress"] = 100.0
        validation_jobs[job_id]["results"] = all_results
        
    except Exception as e:
        validation_jobs[job_id]["status"] = ValidationStatus.FAILED
        validation_jobs[job_id]["completed_at"] = datetime.now()
        validation_jobs[job_id]["error"] = str(e)
        print(f"Validation failed for job {job_id}: {e}")
