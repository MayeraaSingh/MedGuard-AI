"""
MedGuard AI - FastAPI Main Application
Phase 3: Backend Skeleton

REST API for provider validation and directory management.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import os

from .routers import upload, validation, providers


# Application metadata
APP_VERSION = "1.0.0"
APP_TITLE = "MedGuard AI API"
APP_DESCRIPTION = """
MedGuard AI - Agentic Healthcare Provider Data Validation & Directory Management System

## Features

* **Upload** - Upload provider data (CSV/PDF)
* **Validation** - Trigger multi-agent validation pipeline
* **Status** - Check validation job progress
* **Providers** - Query validated provider directory
* **Reports** - Download validation reports and review queues

## Agent Architecture

Built with Google ADK (Agent Development Kit):
- ValidationAgent: NPI Registry, phone/address/license validation
- EnrichmentAgent: Medical school matching, specialty mapping
- QAAgent: Conflict resolution, confidence scoring, fraud detection
- DirectoryAgent: Export management, review queue, email templates
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("=" * 70)
    print("MEDGUARD AI - Starting FastAPI Application")
    print("=" * 70)
    print(f"Version: {APP_VERSION}")
    print(f"Docs: http://localhost:8000/docs")
    print(f"ReDoc: http://localhost:8000/redoc")
    print("=" * 70)
    
    yield
    
    # Shutdown
    print("=" * 70)
    print("MEDGUARD AI - Shutting Down")
    print("=" * 70)


# Create FastAPI application
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Simple frontend
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include routers
app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])
app.include_router(validation.router, prefix="/api/v1", tags=["Validation"])
app.include_router(providers.router, prefix="/api/v1", tags=["Providers"])


# Root endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check."""
    return {
        "name": APP_TITLE,
        "version": APP_VERSION,
        "status": "healthy",
        "docs": "/docs",
        "message": "MedGuard AI API is running"
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "timestamp": time.time()
    }


# Test runner endpoint
@app.post("/test/{phase}", tags=["Testing"])
async def run_test(phase: str):
    """Run test suite for specified phase."""
    import subprocess
    import sys
    from pathlib import Path
    
    # Map phase to test script
    test_scripts = {
        'phase1': 'scripts/test_phase1.py',
        'phase2': 'scripts/test_phase2.py',
        'phase3': 'scripts/test_phase3.py',
        'phase4': 'scripts/test_phase4.py',
        'phase5': 'scripts/test_phase5.py',
    }
    
    # Get project root (parent of backend/)
    project_root = Path(__file__).parent.parent.parent
    
    if phase == 'all':
        # Run all tests sequentially
        all_output = []
        all_passed = True
        for p in ['phase1', 'phase2', 'phase3', 'phase4', 'phase5']:
            script = test_scripts.get(p)
            script_path = project_root / script
            if script_path.exists():
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(project_root),
                    encoding='utf-8',
                    errors='replace'
                )
                all_output.append(f"\n{'='*70}\n{p.upper()}\n{'='*70}\n{result.stdout}")
                if result.returncode != 0:
                    all_passed = False
        
        return {
            "test_name": "All Phases",
            "output": '\n'.join(all_output),
            "passed": all_passed
        }
    
    script = test_scripts.get(phase)
    if not script:
        return {
            "test_name": phase,
            "output": f"Unknown phase: {phase}",
            "passed": False
        }
    
    script_path = project_root / script
    
    if not script_path.exists():
        return {
            "test_name": phase,
            "output": f"Test script not found: {script_path}",
            "passed": False
        }
    
    try:
        # Run the test script from project root with UTF-8 encoding
        # Set PYTHONIOENCODING to force UTF-8 for Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(project_root),
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        # Combine stdout and stderr for full output
        output = result.stdout or ""
        if result.stderr:
            output += "\n\n=== ERRORS ===\n" + result.stderr
        
        if not output:
            output = "Test completed but produced no output"
        
        return {
            "test_name": f"Phase {phase[-1]}",
            "output": output,
            "passed": result.returncode == 0,
            "exit_code": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        return {
            "test_name": phase,
            "output": "Test timed out after 120 seconds",
            "passed": False
        }
    except Exception as e:
        return {
            "test_name": phase,
            "output": f"Error running test: {str(e)}",
            "passed": False
        }


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "path": str(request.url)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
