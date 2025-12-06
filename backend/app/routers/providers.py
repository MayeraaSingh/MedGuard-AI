"""
MedGuard AI - Providers Router
Phase 3: Backend Skeleton

Handles provider queries and directory management.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from ..models.schemas import (
    ProviderResponse,
    ProviderListResponse,
    ProviderDetailResponse,
    ReviewQueueResponse,
    ReviewQueueItem,
    ProviderStatus,
    RiskLevel,
    SystemStats
)

router = APIRouter()

# In-memory provider storage (will move to database in production)
providers_db: dict = {}


@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[ProviderStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name or NPI")
):
    """
    List providers with pagination and filtering.
    
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 100)
    - **status**: Filter by provider status
    - **search**: Search by provider name or NPI
    
    Returns paginated list of providers.
    """
    try:
        # Get all providers
        all_providers = list(providers_db.values())
        
        # Apply filters
        if status:
            all_providers = [p for p in all_providers if p.get("status") == status]
        
        if search:
            search_lower = search.lower()
            all_providers = [
                p for p in all_providers 
                if search_lower in p.get("first_name", "").lower() or
                   search_lower in p.get("last_name", "").lower() or
                   search_lower in str(p.get("npi", ""))
            ]
        
        # Paginate
        total = len(all_providers)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        providers_page = all_providers[start_idx:end_idx]
        
        return ProviderListResponse(
            total=total,
            page=page,
            page_size=page_size,
            providers=providers_page
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list providers: {str(e)}"
        )


@router.get("/provider/{provider_id}", response_model=ProviderDetailResponse)
async def get_provider(provider_id: str):
    """
    Get detailed provider information.
    
    - **provider_id**: Provider ID or NPI
    
    Returns complete provider details including validation and enrichment results.
    """
    if provider_id not in providers_db:
        raise HTTPException(
            status_code=404,
            detail=f"Provider not found: {provider_id}"
        )
    
    return providers_db[provider_id]


@router.get("/review-queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    limit: int = Query(50, ge=1, le=500, description="Maximum items to return"),
    risk_level: Optional[RiskLevel] = Query(None, description="Filter by risk level")
):
    """
    Get prioritized review queue.
    
    - **limit**: Maximum number of items to return
    - **risk_level**: Filter by risk level (low, medium, high)
    
    Returns sorted list of providers requiring manual review.
    """
    try:
        # Get providers requiring review
        review_items = [
            p for p in providers_db.values() 
            if p.get("requires_review", False)
        ]
        
        # Apply risk level filter
        if risk_level:
            review_items = [p for p in review_items if p.get("risk_level") == risk_level]
        
        # Sort by priority (descending)
        review_items.sort(key=lambda x: x.get("priority", 0), reverse=True)
        
        # Limit results
        review_items = review_items[:limit]
        
        # Convert to ReviewQueueItem format
        queue_items = []
        for item in review_items:
            queue_items.append(ReviewQueueItem(
                provider_id=str(item.get("npi", item.get("provider_id"))),
                provider_name=f"{item.get('first_name', '')} {item.get('last_name', '')}".strip(),
                priority=item.get("priority", 0),
                risk_level=item.get("risk_level", RiskLevel.LOW),
                flags=item.get("flags", []),
                confidence=item.get("overall_confidence", 0.0),
                issue_type="general",  # Will be categorized from flags
                created_date=item.get("created_at", datetime.now())
            ))
        
        return ReviewQueueResponse(
            total_items=len(queue_items),
            items=queue_items
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get review queue: {str(e)}"
        )


@router.get("/stats", response_model=SystemStats)
async def get_system_stats():
    """
    Get system statistics.
    
    Returns overall system statistics including provider counts and performance metrics.
    """
    try:
        providers = list(providers_db.values())
        total = len(providers)
        
        if total == 0:
            return SystemStats(
                total_providers=0,
                approved_providers=0,
                needs_review=0,
                flagged_providers=0,
                average_confidence=0.0,
                total_validations=0,
                average_throughput=0.0,
                last_updated=datetime.now()
            )
        
        approved = sum(1 for p in providers if p.get("status") == ProviderStatus.APPROVED)
        needs_review = sum(1 for p in providers if p.get("status") == ProviderStatus.NEEDS_REVIEW)
        flagged = sum(1 for p in providers if p.get("status") == ProviderStatus.FLAGGED)
        
        confidences = [p.get("overall_confidence", 0.0) for p in providers]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return SystemStats(
            total_providers=total,
            approved_providers=approved,
            needs_review=needs_review,
            flagged_providers=flagged,
            average_confidence=avg_confidence,
            total_validations=total,
            average_throughput=37000.0,  # From Phase 2 benchmarks
            last_updated=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system stats: {str(e)}"
        )


@router.post("/provider/{provider_id}/approve")
async def approve_provider(provider_id: str):
    """
    Manually approve a provider.
    
    - **provider_id**: Provider ID or NPI
    
    Returns updated provider status.
    """
    if provider_id not in providers_db:
        raise HTTPException(
            status_code=404,
            detail=f"Provider not found: {provider_id}"
        )
    
    providers_db[provider_id]["status"] = ProviderStatus.APPROVED
    providers_db[provider_id]["requires_review"] = False
    providers_db[provider_id]["updated_at"] = datetime.now()
    
    return {
        "success": True,
        "provider_id": provider_id,
        "status": ProviderStatus.APPROVED,
        "message": "Provider approved successfully"
    }


@router.post("/provider/{provider_id}/flag")
async def flag_provider(provider_id: str, reason: str):
    """
    Flag a provider for issues.
    
    - **provider_id**: Provider ID or NPI
    - **reason**: Reason for flagging
    
    Returns updated provider status.
    """
    if provider_id not in providers_db:
        raise HTTPException(
            status_code=404,
            detail=f"Provider not found: {provider_id}"
        )
    
    providers_db[provider_id]["status"] = ProviderStatus.FLAGGED
    providers_db[provider_id]["flags"].append(reason)
    providers_db[provider_id]["updated_at"] = datetime.now()
    
    return {
        "success": True,
        "provider_id": provider_id,
        "status": ProviderStatus.FLAGGED,
        "message": f"Provider flagged: {reason}"
    }
