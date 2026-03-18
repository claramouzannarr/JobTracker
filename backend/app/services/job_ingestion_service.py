"""
Job ingestion from Adzuna: fetch jobs, upsert into JobPosting, compute and store embeddings.
"""
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import JobPosting
from app.services.embedding_service import embed_text
from app.services.providers.adzuna_client import AdzunaClient, AdzunaAPIError

logger = logging.getLogger(__name__)

SOURCE_ADZUNA = "adzuna"

# Keywords to infer remote_type from title + description
REMOTE_KEYWORDS = ["remote", "work from home", "wfh", "work from home", "distributed"]
HYBRID_KEYWORDS = ["hybrid"]
ONSITE_KEYWORDS = ["on-site", "onsite", "in office", "in-office"]


def _infer_remote_type(title: str, description: str) -> Tuple[Optional[str], bool]:
    """Infer remote_type and remote_flag from title and description. Returns (remote_type, remote_flag)."""
    combined = f"{(title or '').lower()} {(description or '').lower()}"
    if any(kw in combined for kw in HYBRID_KEYWORDS):
        return "hybrid", True
    if any(kw in combined for kw in REMOTE_KEYWORDS):
        return "remote", True
    if any(kw in combined for kw in ONSITE_KEYWORDS):
        return "onsite", False
    return "onsite", False


def _description_hash(text: str) -> str:
    """SHA256 hash of description for change detection."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _normalize_job_text_for_embedding(title: str, company: str, location_display: str, description: str) -> str:
    """Build normalized text for job embedding."""
    parts = [title or "", company or "", location_display or "", description or ""]
    return "\n".join(p.strip() for p in parts if p and p.strip())


def _parse_created(created_val: Any) -> Optional[datetime]:
    """Parse Adzuna created timestamp (ISO string)."""
    if created_val is None:
        return None
    if isinstance(created_val, datetime):
        return created_val
    s = str(created_val).strip()
    if not s:
        return None
    try:
        # Adzuna uses "2013-11-08T18:07:39Z"
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def ingest_adzuna_jobs(
    db: Session,
    country: str,
    what: Optional[str] = None,
    where: Optional[str] = None,
    pages: int = 3,
    results_per_page: int = 50,
    app_id: str = "",
    app_key: str = "",
    base_url: str = "https://api.adzuna.com/v1/api",
) -> Dict[str, int]:
    """
    Ingest jobs from Adzuna into JobPosting. Upserts by (source, external_id).
    Computes embedding only for new jobs or when description changed.
    Returns counts: {fetched, inserted, updated, skipped}.
    """
    if not app_id or not app_key:
        logger.warning("Adzuna credentials missing; skipping ingestion")
        return {"fetched": 0, "inserted": 0, "updated": 0, "skipped": 0}

    client = AdzunaClient(app_id=app_id, app_key=app_key, base_url=base_url)
    counts = {"fetched": 0, "inserted": 0, "updated": 0, "skipped": 0}

    for page in range(1, pages + 1):
        try:
            data = client.search_jobs(
                country=country,
                page=page,
                what=what,
                where=where,
                results_per_page=results_per_page,
            )
        except AdzunaAPIError as e:
            logger.warning("Adzuna API error on page %s: %s", page, e)
            break

        results = data.get("results") or []
        counts["fetched"] += len(results)

        for job in results:
            external_id = str(job.get("id", ""))
            if not external_id:
                continue

            title = (job.get("title") or "").strip() or "Untitled"
            company_obj = job.get("company") or {}
            company = (company_obj.get("display_name") or "").strip() or "Unknown"
            # Adzuna's 'description' field can be a shortened preview. Prefer
            # 'full_description' when available so we store the complete JD,
            # including all skills/requirements text.
            description = (
                (job.get("full_description") or job.get("description") or "").strip()
            )
            loc_obj = job.get("location") or {}
            location_display = (loc_obj.get("display_name") or "").strip()
            url = (job.get("redirect_url") or job.get("adref") or "").strip()
            contract_type = (job.get("contract_time") or job.get("contract_type") or "").strip() or None
            salary_min = job.get("salary_min")
            salary_max = job.get("salary_max")
            if salary_min is not None and not isinstance(salary_min, (int, float)):
                salary_min = None
            if salary_max is not None and not isinstance(salary_max, (int, float)):
                salary_max = None
            latitude = job.get("latitude")
            longitude = job.get("longitude")
            if latitude is not None and not isinstance(latitude, (int, float)):
                latitude = None
            if longitude is not None and not isinstance(longitude, (int, float)):
                longitude = None
            created_at = _parse_created(job.get("created"))

            remote_type, remote_flag = _infer_remote_type(title, description)
            desc_hash = _description_hash(description)

            existing = (
                db.query(JobPosting)
                .filter(JobPosting.source == SOURCE_ADZUNA, JobPosting.external_id == external_id)
                .first()
            )

            if existing:
                # Check if we need to update (title, company, description, location, salary changed)
                fields_changed = (
                    existing.title != title
                    or (existing.company or "") != company
                    or (existing.description_text or "") != description
                    or (existing.location_display or "") != location_display
                    or existing.salary_min != salary_min
                    or existing.salary_max != salary_max
                )
                desc_changed = (existing.description_hash or "") != desc_hash

                if not fields_changed and not desc_changed:
                    counts["skipped"] += 1
                    continue

                existing.title = title
                existing.company = company
                existing.description_text = description
                existing.job_url = url or existing.job_url
                existing.location_display = location_display
                existing.contract_type = contract_type
                existing.salary_min = salary_min
                existing.salary_max = salary_max
                existing.latitude = latitude
                existing.longitude = longitude
                existing.remote_flag = remote_flag
                existing.remote_type = remote_type
                existing.description_hash = desc_hash
                if created_at:
                    existing.created_at = created_at

                if desc_changed:
                    text_for_embed = _normalize_job_text_for_embedding(
                        title, company, location_display, description
                    )
                    emb = embed_text(text_for_embed)
                    if emb:
                        existing.embedding_vector = emb

                db.commit()
                counts["updated"] += 1
                logger.debug("Updated job %s %s", SOURCE_ADZUNA, external_id)
            else:
                text_for_embed = _normalize_job_text_for_embedding(
                    title, company, location_display, description
                )
                embedding_vector = embed_text(text_for_embed)

                new_job = JobPosting(
                    source=SOURCE_ADZUNA,
                    external_id=external_id,
                    title=title,
                    company=company,
                    description_text=description,
                    job_url=url or None,
                    country=country.upper() if country else None,
                    location_display=location_display or None,
                    contract_type=contract_type,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    latitude=latitude,
                    longitude=longitude,
                    remote_flag=remote_flag,
                    remote_type=remote_type,
                    description_hash=desc_hash,
                    embedding_vector=embedding_vector,
                    is_active=True,
                )
                if created_at:
                    new_job.created_at = created_at
                db.add(new_job)
                db.commit()
                counts["inserted"] += 1
                logger.debug("Inserted job %s %s", SOURCE_ADZUNA, external_id)

    logger.info(
        "Adzuna ingestion finished: fetched=%s inserted=%s updated=%s skipped=%s",
        counts["fetched"],
        counts["inserted"],
        counts["updated"],
        counts["skipped"],
    )
    return counts
