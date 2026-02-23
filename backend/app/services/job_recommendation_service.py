"""
Job recommendation service: user profile embedding, cosine similarity scoring,
preference-based penalties, and explainability (matched/missing skills, penalties).
"""
import logging
import time
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.models import JobPosting, User, Application, ResumeVersion
from app.services.embedding_service import embed_text

logger = logging.getLogger(__name__)

# Max candidates to score (bounded compute)
MAX_CANDIDATES = 3000


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Safe cosine similarity in pure Python. Returns 0 if norm is zero."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


def _estimate_job_seniority(title: str, description: Optional[str] = None) -> str:
    """Estimate job seniority from title/description. Returns 'entry', 'mid', or 'senior'."""
    combined = f"{(title or '').lower()} {(description or '').lower()}"
    if any(k in combined for k in ["senior", "lead", "principal", "staff", "architect", "director", "head"]):
        return "senior"
    if any(k in combined for k in ["junior", "entry", "associate", "intern", "graduate", "new grad"]):
        return "entry"
    return "mid"


def _estimate_user_seniority(years_experience: Optional[int]) -> str:
    if years_experience is None:
        return "mid"
    if years_experience < 2:
        return "entry"
    if years_experience >= 5:
        return "senior"
    return "mid"


def build_user_profile_text(
    user: User,
    resume_text: Optional[str] = None,
    preferences: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build a single string representing the user profile for embedding.
    Includes resume (or summary if very long), desired roles, industry, skills, location, remote preference.
    """
    parts = []
    max_resume_chars = 8000
    if resume_text and resume_text.strip():
        text = resume_text.strip()
        if len(text) > max_resume_chars:
            text = text[:max_resume_chars] + " [truncated]"
        parts.append(text)
    if user.primary_role_preference:
        parts.append(f"Desired role: {user.primary_role_preference}")
    if user.primary_industry_preference:
        parts.append(f"Industry: {user.primary_industry_preference}")
    if user.remote_preference and user.remote_preference != "any":
        parts.append(f"Work preference: {user.remote_preference}")
    if user.country:
        parts.append(f"Location/country: {user.country}")
    if user.desired_countries:
        countries = user.desired_countries if isinstance(user.desired_countries, list) else []
        if countries:
            parts.append("Desired countries: " + ", ".join(str(c) for c in countries[:10]))
    # Include top skills from resume if we have them
    if resume_text and resume_text.strip():
        try:
            from app.services.skill_extraction import extract_skills
            skills = extract_skills(resume_text)
            if skills:
                top_skills = list(skills)[:20]
                parts.append("Skills: " + ", ".join(top_skills))
        except Exception:
            pass
    if preferences:
        if preferences.get("desired_roles"):
            parts.append("Roles: " + ", ".join(preferences["desired_roles"][:10]))
        if preferences.get("location_preference"):
            parts.append(f"Location preference: {preferences['location_preference']}")
    return "\n".join(p for p in parts if p and str(p).strip())


def recommend_jobs(
    db: Session,
    user_id: int,
    limit: int = 20,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Return top N jobs for the user ranked by cosine similarity (user profile vs job embedding)
    with preference-based penalties and explainability.
    """
    filters = filters or {}
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []

    # Latest resume text
    latest_app = (
        db.query(Application)
        .filter(Application.user_id == user_id)
        .order_by(Application.created_at.desc())
        .first()
    )
    latest_resume_text = None
    if latest_app:
        rv = (
            db.query(ResumeVersion)
            .filter(ResumeVersion.application_id == latest_app.id)
            .order_by(ResumeVersion.created_at.desc())
            .first()
        )
        if rv and rv.extracted_text:
            latest_resume_text = rv.extracted_text

    user_text = build_user_profile_text(user, latest_resume_text)
    user_emb = embed_text(user_text)
    if not user_emb:
        logger.warning("Could not compute user profile embedding")
        return []

    # Candidate selection: is_active (or NULL for legacy rows), with embedding, apply hard filters, cap at MAX_CANDIDATES
    from sqlalchemy import or_
    q = (
        db.query(JobPosting)
        .filter(
            or_(JobPosting.is_active == True, JobPosting.is_active.is_(None)),
            JobPosting.embedding_vector.isnot(None),
        )
    )
    if filters.get("country"):
        q = q.filter(JobPosting.country.ilike(f"%{filters['country']}%"))
    if filters.get("remote_type"):
        q = q.filter(JobPosting.remote_type == filters["remote_type"])
    if filters.get("contract_type"):
        q = q.filter(JobPosting.contract_type.ilike(f"%{filters['contract_type']}%"))
    if filters.get("min_salary") is not None:
        q = q.filter(JobPosting.salary_max >= float(filters["min_salary"]))
    if filters.get("where"):
        where = str(filters["where"]).lower()
        q = q.filter(
            (JobPosting.location_display.ilike(f"%{where}%")) | (JobPosting.title.ilike(f"%{where}%"))
        )

    candidates = q.order_by(JobPosting.created_at.desc()).limit(MAX_CANDIDATES).all()
    candidates_count = len(candidates)
    t0 = time.perf_counter()

    # Resume skills for explainability
    resume_skills: Set[str] = set()
    if latest_resume_text:
        try:
            from app.services.skill_extraction import extract_skills
            resume_skills = extract_skills(latest_resume_text)
        except Exception:
            pass

    results = []
    for job in candidates:
        job_emb = job.embedding_vector
        if not job_emb or not isinstance(job_emb, list):
            continue
        sim = _cosine_similarity(user_emb, job_emb)
        penalty_multiplier = 1.0
        penalties_applied: List[str] = []

        # Soft penalties
        if user.remote_preference and user.remote_preference != "any":
            job_remote = (job.remote_type or "").lower() or ("remote" if job.remote_flag else "onsite")
            if user.remote_preference.lower() == "remote" and job_remote == "onsite":
                penalty_multiplier *= 0.75
                penalties_applied.append("Prefers remote; job is onsite")
            elif user.remote_preference.lower() == "onsite" and job_remote == "remote":
                penalty_multiplier *= 0.8
                penalties_applied.append("Prefers onsite; job is remote")
        if user.country and job.location_display:
            loc = (job.location_display or "").lower()
            user_country = (user.country or "").lower()
            if user_country not in loc and (not user.desired_countries or not any(
                str(c).lower() in loc for c in (user.desired_countries or [])
            )):
                penalty_multiplier *= 0.85
                penalties_applied.append("Location preference mismatch")
        user_seniority = _estimate_user_seniority(user.years_experience)
        job_seniority = _estimate_job_seniority(job.title, job.description_text)
        if user_seniority != job_seniority:
            penalty_multiplier *= 0.9
            penalties_applied.append(f"Seniority: user {user_seniority}, job {job_seniority}")

        final_score = sim * penalty_multiplier

        # Job skills for explainability
        job_skills: Set[str] = set()
        if job.description_text:
            try:
                from app.services.skill_extraction import extract_skills_from_job_description
                job_skills = extract_skills_from_job_description(job.description_text)
            except Exception:
                pass
        matched_skills = list(resume_skills & job_skills)[:15]
        missing_skills = list(job_skills - resume_skills)[:10]

        results.append({
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "location_display": job.location_display,
            "url": job.job_url,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "remote_type": job.remote_type,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "description_text": job.description_text[:500] + "..." if job.description_text and len(job.description_text) > 500 else job.description_text,
            "score": round(final_score, 4),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "penalties_applied": penalties_applied,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    elapsed = time.perf_counter() - t0
    logger.info(
        "Recommendation: user_id=%s candidates_count=%s limit=%s time_sec=%.3f",
        user_id,
        candidates_count,
        limit,
        elapsed,
    )
    return results[:limit]
