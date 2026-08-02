from typing import List, Optional
from fastapi import APIRouter, HTTPException
from app.api.deps import SessionDep, CurrentUser
from app.schemas.xai import XAIExplanationItem, XAIOverviewResponse
from app.services.xai_service import xai_service

# NOTE: No prefix here — main.py registers this router with prefix="/api/xai"
router = APIRouter(tags=["Explainable AI"])


@router.get("/explanations", response_model=List[XAIExplanationItem])
def get_explanations(
    db: SessionDep,
    current_user: CurrentUser,
    request_type: Optional[str] = None,
    provider_id: Optional[int] = None,
    decision: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
):
    """
    Get Explainable AI decision explanations generated from simulation requests.
    Supports multi-attribute search and filtering.
    """
    return xai_service.get_explanations(
        db,
        request_type=request_type,
        provider_id=provider_id,
        decision=decision,
        status=status,
        search=search,
        limit=limit,
    )


@router.get("/explanations/{request_id}", response_model=XAIExplanationItem)
def get_explanation_by_id(
    request_id: int,
    db: SessionDep,
    current_user: CurrentUser,
):
    """Get explanation details for a specific request ID."""
    explanations = xai_service.get_explanations(db, search=str(request_id), limit=10)
    for exp in explanations:
        if exp.request_id == request_id:
            return exp
    raise HTTPException(status_code=404, detail=f"Explanation for Request #{request_id} not found")


@router.get("/overview", response_model=XAIOverviewResponse)
def get_xai_overview(
    db: SessionDep,
    current_user: CurrentUser,
):
    """Get aggregate XAI statistics, compatibility score distributions, and decision breakdowns."""
    return xai_service.get_overview(db)
