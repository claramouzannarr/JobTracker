"""
Job posting ingestion (Adzuna) and recommendations endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import User
from app.schemas import JobRecommendationWithReasons, AdzunaIngestRequest
from app.auth import get_current_user
from app.config import settings
from app.services.job_ingestion_service import ingest_adzuna_jobs
from app.services.job_recommendation_service import recommend_jobs

router = APIRouter()


def _require_ingest_auth(x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
    """Require X-Admin-Token header for ingest endpoint when INGEST_ADMIN_TOKEN is set."""
    if not settings.ingest_admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingest not configured (INGEST_ADMIN_TOKEN not set)",
        )
    if x_admin_token != settings.ingest_admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Admin-Token",
        )


@router.post("/ingest/adzuna")
async def ingest_adzuna(
    body: AdzunaIngestRequest,
    db: Session = Depends(get_db),
    _auth: None = Depends(_require_ingest_auth),
):
    """
    Ingest jobs from Adzuna into JobPosting table (upsert by source+external_id).
    Requires X-Admin-Token header when INGEST_ADMIN_TOKEN is set.
    """
    counts = ingest_adzuna_jobs(
        db=db,
        country=body.country,
        what=body.what,
        where=body.where,
        pages=body.pages,
        results_per_page=body.results_per_page,
        app_id=settings.adzuna_app_id,
        app_key=settings.adzuna_app_key,
        base_url=settings.adzuna_base_url,
    )
    return counts


@router.get("/recommendations", response_model=List[JobRecommendationWithReasons])
async def get_job_recommendations(
    limit: int = 20,
    remote_type: Optional[str] = None,
    where: Optional[str] = None,
    country: Optional[str] = None,
    contract_type: Optional[str] = None,
    min_salary: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get top N job recommendations for the logged-in user.
    Ranked by cosine similarity (user profile embedding vs job embeddings) with preference-based penalties.
    Returns matched_skills, missing_skills, and penalties_applied per job.
    """
    filters = {}
    if remote_type:
        filters["remote_type"] = remote_type
    if where:
        filters["where"] = where
    if country:
        filters["country"] = country
    if contract_type:
        filters["contract_type"] = contract_type
    if min_salary is not None:
        filters["min_salary"] = min_salary

    results = recommend_jobs(
        db=db,
        user_id=current_user.id,
        limit=limit,
        filters=filters if filters else None,
    )
    return results


@router.post("/ingest/adzuna/demo")
async def ingest_adzuna_demo(
    db: Session = Depends(get_db),
    _auth: None = Depends(_require_ingest_auth),
):
    """
    Convenience endpoint for capstone demo: ingest jobs for ES and GB
    with queries "data analyst" and "software engineer", 2 pages each.
    Requires X-Admin-Token header when INGEST_ADMIN_TOKEN is set.
    """
    all_counts = {"by_run": [], "total": {"fetched": 0, "inserted": 0, "updated": 0, "skipped": 0}}
    for country in ("es", "gb"):
        for what in ("data analyst", "software engineer"):
            counts = ingest_adzuna_jobs(
                db=db,
                country=country,
                what=what,
                where=None,
                pages=2,
                results_per_page=50,
                app_id=settings.adzuna_app_id,
                app_key=settings.adzuna_app_key,
                base_url=settings.adzuna_base_url,
            )
            all_counts["by_run"].append({"country": country, "what": what, **counts})
            for k in ("fetched", "inserted", "updated", "skipped"):
                all_counts["total"][k] += counts[k]
    return all_counts
