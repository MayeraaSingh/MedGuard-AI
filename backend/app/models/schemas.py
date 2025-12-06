"""
MedGuard AI - Pydantic Models
Phase 3: Backend Skeleton

Request/response schemas for API validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class ValidationStatus(str, Enum):
    """Validation status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProviderStatus(str, Enum):
    """Provider status enum."""
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"
    FLAGGED = "flagged"


class RiskLevel(str, Enum):
    """Risk level enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Upload schemas
class UploadResponse(BaseModel):
    """Response for file upload."""
    success: bool
    filename: str
    file_size: int
    rows_detected: Optional[int] = None
    message: str


# Validation schemas
class ValidationRequest(BaseModel):
    """Request to start validation."""
    file_path: str = Field(..., description="Path to uploaded file")
    batch_size: Optional[int] = Field(10, description="Number of providers to process in batch")
    
    @field_validator('batch_size')
    @classmethod
    def validate_batch_size(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('Batch size must be between 1 and 1000')
        return v


class ValidationJobResponse(BaseModel):
    """Response when validation job is created."""
    job_id: str
    status: ValidationStatus
    created_at: datetime
    message: str


class ValidationStatusResponse(BaseModel):
    """Response for validation status check."""
    job_id: str
    status: ValidationStatus
    progress: float = Field(..., ge=0.0, le=100.0, description="Progress percentage")
    providers_processed: int
    providers_total: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None


class ValidationResultSummary(BaseModel):
    """Summary of validation results."""
    total_providers: int
    approved: int
    needs_review: int
    flagged: int
    average_confidence: float
    throughput_per_hour: float


# Provider schemas
class ProviderBase(BaseModel):
    """Base provider model."""
    npi: str = Field(..., description="National Provider Identifier")
    first_name: str
    last_name: str
    degree: Optional[str] = None
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    license_number: Optional[str] = None
    license_state: Optional[str] = None


class ProviderCreate(ProviderBase):
    """Schema for creating provider."""
    pass


class ProviderResponse(ProviderBase):
    """Schema for provider response."""
    provider_id: int
    status: ProviderStatus
    overall_confidence: float
    validation_confidence: Optional[float] = None
    enrichment_confidence: Optional[float] = None
    requires_review: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    flags: List[str] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProviderListResponse(BaseModel):
    """Paginated list of providers."""
    total: int
    page: int
    page_size: int
    providers: List[ProviderResponse]


class ProviderDetailResponse(ProviderResponse):
    """Detailed provider information."""
    medical_school: Optional[str] = None
    matched_medical_school: Optional[str] = None
    sub_specialties: List[str] = []
    services_offered: List[str] = []
    validation_results: Optional[Dict[str, Any]] = None
    enrichment_results: Optional[Dict[str, Any]] = None
    qa_results: Optional[Dict[str, Any]] = None


# Review queue schemas
class ReviewQueueItem(BaseModel):
    """Review queue item."""
    provider_id: str
    provider_name: str
    priority: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    flags: List[str]
    confidence: float
    issue_type: str
    created_date: datetime


class ReviewQueueResponse(BaseModel):
    """Review queue response."""
    total_items: int
    items: List[ReviewQueueItem]


# Export schemas
class ExportRequest(BaseModel):
    """Request to export data."""
    format: str = Field(..., description="Export format: csv or json")
    filters: Optional[Dict[str, Any]] = None
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        if v not in ['csv', 'json']:
            raise ValueError('Format must be csv or json')
        return v


class ExportResponse(BaseModel):
    """Response for export request."""
    job_id: str
    format: str
    status: str
    download_url: Optional[str] = None
    created_at: datetime


# Statistics schemas
class SystemStats(BaseModel):
    """System statistics."""
    total_providers: int
    approved_providers: int
    needs_review: int
    flagged_providers: int
    average_confidence: float
    total_validations: int
    average_throughput: float
    last_updated: datetime


# Error schemas
class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
