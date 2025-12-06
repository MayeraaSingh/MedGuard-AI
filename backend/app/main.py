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
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
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
