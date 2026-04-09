"""
Job recommendation service: user profile embedding, cosine similarity scoring,
preference-based penalties, and explainability (matched/missing skills, penalties).
"""
import logging
import time
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.models import JobPosting, User
from app.services.embedding_service import embed_text

logger = logging.getLogger(__name__)

# Max candidates to score (bounded compute). Keeping this modest helps
# keep recommendation latency low while still exploring a rich set of jobs.
MAX_CANDIDATES = 1200


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


def _embedding_similarity(a: List[float], b: List[float]) -> float:
    """Wrapper for cosine similarity (reuse the existing function)."""
    return _cosine_similarity(a, b)


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


def _norm_text(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _industry_keywords(preference: str) -> List[str]:
    """
    Map a user's industry preference to keywords we can match in job title/description.
    JobPosting doesn't store a normalized industry field, so this makes preferences
    deterministically affect ranking.
    """
    pref = _norm_text(preference)
    if not pref:
        return []

    keywords: Set[str] = set()

    if any(k in pref for k in ["private equity", "priv equity", "buyout"]):
        keywords.update(
            [
                "private equity",
                "buyout",
                "lbo",
                "leveraged buyout",
                "portfolio company",
                "deal team",
                "investment committee",
                "due diligence",
                "valuation",
                "m&a",
                "mergers",
                "acquisitions",
                "transaction",
                "investment banking",
            ]
        )

    if "finance" in pref or "financial" in pref:
        keywords.update(
            [
                "finance",
                "financial",
                "valuation",
                "modeling",
                "financial model",
                "fp&a",
                "corporate finance",
                "risk",
                "credit",
                "equity research",
                "investment",
                "capital markets",
            ]
        )

    if any(k in pref for k in ["technology", "software", "tech"]):
        keywords.update(
            [
                "software",
                "engineering",
                "developer",
                "cloud",
                "agile",
                "product",
                "backend",
                "frontend",
                "data",
                "api",
                "infrastructure",
                "saas",
            ]
        )

    if any(k in pref for k in ["consulting", "management consulting", "strategy"]):
        keywords.update(
            [
                "consulting",
                "strategy",
                "advisory",
                "transformation",
                "stakeholder",
                "project management",
                "management consulting",
                "strategic",
                "engagement",
            ]
        )

    if any(k in pref for k in ["healthcare", "health", "pharma", "medical"]):
        keywords.update(
            [
                "healthcare",
                "health",
                "pharma",
                "pharmaceutical",
                "clinical",
                "medical",
                "biotech",
                "life sciences",
                "patient",
                "regulatory",
            ]
        )

    if any(k in pref for k in ["marketing", "media", "advertising"]):
        keywords.update(
            [
                "marketing",
                "brand",
                "digital marketing",
                "campaign",
                "advertising",
                "media",
                "content",
                "seo",
                "growth",
                "analytics",
            ]
        )

    if not keywords:
        stop = {"and", "or", "the", "a", "an", "in", "of", "to", "for", "with"}
        tokens = [t for t in pref.replace("/", " ").replace(",", " ").split() if len(t) >= 2 and t not in stop]
        keywords.update(tokens[:8])

    return sorted(keywords)


def _role_keywords(preference: str) -> List[str]:
    pref = _norm_text(preference)
    if not pref:
        return []

    keywords: Set[str] = set()

    # UI option; not a real preference signal.
    if pref in {"other roles", "other"}:
        return []

    if "analyst" in pref:
        keywords.update(["analyst", "investment analyst", "financial analyst", "research analyst", "equity research"])
    if "associate" in pref:
        keywords.update(["associate", "investment associate", "private equity associate"])
    if "investment banking" in pref or pref in {"ib", "i-banking"}:
        keywords.update(["investment banking", "m&a", "mergers", "acquisitions"])
    if "private equity" in pref:
        keywords.update(["private equity", "buyout", "lbo"])

    if not keywords:
        stop = {"and", "or", "the", "a", "an", "in", "of", "to", "for", "with"}
        tokens = [t for t in pref.replace("/", " ").replace(",", " ").split() if len(t) >= 2 and t not in stop]
        keywords.update(tokens[:8])

    return sorted(keywords)


def _keyword_match_score(text: str, keywords: List[str]) -> float:
    """Lightweight match score in [0, 1] based on substring hits."""
    t = _norm_text(text)
    if not t or not keywords:
        return 0.0
    hits = 0.0
    for kw in keywords:
        k = _norm_text(kw)
        if not k:
            continue
        if " " in k:
            if k in t:
                hits += 1.5
        else:
            if k in t:
                hits += 1.0
    return min(1.0, hits / 3.0)


def _country_match_score(user: User, job: JobPosting) -> float:
    """
    Country preference score in [0, 1].
    Uses user.desired_countries if present, otherwise falls back to user.country.
    Matches against job.country and job.location_display (substring match).
    """
    def _norm_country_token(val: str) -> str:
        s = _norm_text(val)
        s = s.replace(".", " ").replace(",", " ").replace("-", " ").strip()
        s = " ".join(s.split())
        return s

    # Minimal normalization to handle common UX inputs vs Adzuna ISO-ish codes.
    # Adzuna ingestion stores country as upper-case two-letter input like "GB", "IE".
    COUNTRY_ALIASES = {
        # UK / GB
        "uk": "gb",
        "u k": "gb",
        "gb": "gb",
        "g b": "gb",
        "great britain": "gb",
        "britain": "gb",
        "united kingdom": "gb",
        "england": "gb",
        "scotland": "gb",
        "wales": "gb",
        "northern ireland": "gb",
        # Ireland / IE
        "ireland": "ie",
        "republic of ireland": "ie",
        "ie": "ie",
        "i e": "ie",
        "eire": "ie",
    }

    def _to_country_code(val: str) -> Optional[str]:
        tok = _norm_country_token(val)
        if not tok:
            return None
        if tok in COUNTRY_ALIASES:
            return COUNTRY_ALIASES[tok]
        # If it's already a 2-letter code-like token
        compact = tok.replace(" ", "")
        if len(compact) == 2 and compact.isalpha():
            return compact
        return None

    desired_raw: List[str] = []
    if isinstance(user.desired_countries, list) and user.desired_countries:
        desired_raw = [str(c) for c in user.desired_countries if str(c).strip()]
    elif user.country and str(user.country).strip():
        desired_raw = [str(user.country)]

    if not desired_raw:
        return 0.5  # neutral when user has no country preference

    desired_codes = {c for c in (_to_country_code(v) for v in desired_raw) if c}
    desired_tokens = {_norm_country_token(v) for v in desired_raw if _norm_country_token(v)}

    job_country_code = _to_country_code(str(job.country or ""))
    loc = _norm_text(job.location_display)

    # Exact code match first.
    if desired_codes and job_country_code and job_country_code in desired_codes:
        return 1.0

    # If we couldn't map to codes, fall back to substring matching in location/country fields.
    hay = " ".join(p for p in [str(job.country or ""), job.location_display or ""] if p and str(p).strip()).lower()
    if hay:
        for tok in desired_tokens:
            if tok and tok in hay:
                return 1.0

    # A final alias-aware fallback: if location contains "london", treat as GB.
    if desired_codes and "gb" in desired_codes and any(k in loc for k in ["london", "manchester", "edinburgh", "birmingham"]):
        return 1.0

    return 0.0


def _remote_match_score(user: User, job: JobPosting) -> float:
    """
    Remote preference score in [0, 1].
    - If user has no preference / 'any' => neutral 0.5
    - Exact match => 1.0
    - Hybrid preference gets partial credit for remote/onsite
    """
    pref = _norm_text(getattr(user, "remote_preference", None))
    pref = pref.replace("-", "").replace(" ", "")
    if not pref or pref == "any":
        return 0.5

    job_remote = _norm_text(job.remote_type) or ("remote" if job.remote_flag else "onsite")
    job_remote = job_remote.replace("-", "").replace(" ", "")

    if pref == job_remote:
        return 1.0
    if pref == "hybrid" and job_remote in {"remote", "onsite"}:
        return 0.5
    return 0.0


def _looks_like_software_role(title: Optional[str]) -> bool:
    t = _norm_text(title)
    if not t:
        return False
    return any(
        k in t
        for k in [
            "software engineer",
            "software developer",
            "engineer",
            "developer",
            "full stack",
            "frontend",
            "front end",
            "backend",
            "back end",
            "mobile engineer",
            "ios",
            "android",
            "devops",
            "site reliability",
            "sre",
            "platform engineer",
            "data engineer",
        ]
    )


def _prefers_finance(industry_pref: Optional[str]) -> bool:
    p = _norm_text(industry_pref)
    return any(k in p for k in ["finance", "financial", "private equity", "investment", "banking", "fintech"])


def _prefers_software(role_pref: Optional[str]) -> bool:
    p = _norm_text(role_pref)
    return any(k in p for k in ["engineer", "developer", "software", "devops", "sre"])


def build_user_profile_text(
    user: User,
    preferences: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build a single string representing the user profile for embedding,
    based only on stored profile preferences (not resume content).
    """
    parts = []
    if user.primary_role_preference:
        parts.append(f"Desired role: {user.primary_role_preference}")
    industries = []
    if getattr(user, "industry_preferences", None):
        industries = user.industry_preferences if isinstance(user.industry_preferences, list) else []
    if not industries and user.primary_industry_preference:
        industries = [user.primary_industry_preference]
    if industries:
        parts.append("Industries: " + ", ".join(str(i) for i in industries[:10]))
    if user.remote_preference and user.remote_preference != "any":
        parts.append(f"Work preference: {user.remote_preference}")
    if user.country:
        parts.append(f"Location/country: {user.country}")
    if user.desired_countries:
        countries = user.desired_countries if isinstance(user.desired_countries, list) else []
        if countries:
            parts.append("Desired countries: " + ", ".join(str(c) for c in countries[:10]))
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

    # Build user profile text from stored preferences (no resume content)
    user_text = build_user_profile_text(user)
    user_emb = embed_text(user_text)
    if not user_emb:
        logger.warning("Could not compute user profile embedding")
        return []

    industry_prefs: List[str] = []
    if getattr(user, "industry_preferences", None):
        industry_prefs = user.industry_preferences if isinstance(user.industry_preferences, list) else []
    if not industry_prefs and user.primary_industry_preference:
        industry_prefs = [user.primary_industry_preference]

    industry_pref_text = ", ".join(industry_prefs)
    industry_keywords = _industry_keywords(industry_pref_text or "")
    role_keywords = _role_keywords(user.primary_role_preference or "")

    industry_pref_emb = embed_text(industry_pref_text) if industry_pref_text else None

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

    results = []
    for job in candidates:
        job_emb = job.embedding_vector
        if not job_emb or not isinstance(job_emb, list):
            continue
        sim = _cosine_similarity(user_emb, job_emb)
        penalties_applied: List[str] = []
        combined_text = " ".join(
            p for p in [job.title, job.company, job.description_text, job.location_display] if p and str(p).strip()
        )

        # --- INDUSTRY SCORING (HYBRID: keywords + embeddings) ---
        # 1) Keyword score
        keyword_industry_score = (
            _keyword_match_score(combined_text, industry_keywords) if industry_keywords else 0.5
        )

        # 2) Embedding score (semantic)
        embedding_industry_score = 0.5  # neutral default
        if industry_pref_emb and job_emb:
            embedding_industry_score = _embedding_similarity(industry_pref_emb, job_emb)
            embedding_industry_score = max(0.0, min(1.0, (embedding_industry_score + 1.0) / 2.0))

        # 3) Combine both
        industry_score = 0.5 * keyword_industry_score + 0.5 * embedding_industry_score

        # Explainability: keyword match + semantic match
        if industry_keywords:
            penalties_applied.append(
                "Strong keyword industry match" if keyword_industry_score >= 0.6 else "Weak keyword industry match"
            )
        if industry_pref_emb:
            penalties_applied.append(
                "Strong semantic industry match"
                if embedding_industry_score >= 0.6
                else "Weak semantic industry match"
            )

        # Role keywords are treated as part of industry intent; we use them as a small adjustment
        # to the industry score (bounded) so a PE/finance "Analyst" preference matters without
        # changing the 40/40/20 contract.
        if role_keywords:
            role_score = _keyword_match_score(combined_text, role_keywords)
            industry_score = min(1.0, max(0.0, industry_score * 0.85 + role_score * 0.15))
            penalties_applied.append("Matches role preference" if role_score >= 0.34 else "Role preference mismatch")

        # Guardrail: if the user prefers finance but NOT software roles, downrank obvious software titles
        # even if the company/description mentions finance (many finance firms hire software engineers).
        primary_industry = (industry_prefs[0] if industry_prefs else (user.primary_industry_preference or ""))
        if _prefers_finance(primary_industry) and not _prefers_software(user.primary_role_preference):
            if _looks_like_software_role(job.title):
                industry_score *= 0.25
                penalties_applied.append("Downranked: software role under finance preference")

        country_score = _country_match_score(user, job)
        penalties_applied.append("Matches country preference" if country_score >= 0.8 else "Country preference mismatch")

        remote_score = _remote_match_score(user, job)
        if _norm_text(getattr(user, "remote_preference", None)) not in {"", "any"}:
            penalties_applied.append("Matches remote preference" if remote_score >= 0.8 else "Remote preference mismatch")

        # Seniority scoring
        user_seniority = _estimate_user_seniority(user.years_experience)
        job_seniority = _estimate_job_seniority(job.title, job.description_text)
        if user_seniority == job_seniority:
            seniority_score = 1.0
        elif abs(["entry", "mid", "senior"].index(user_seniority) - ["entry", "mid", "senior"].index(job_seniority)) == 1:
            seniority_score = 0.5
        else:
            seniority_score = 0.0
        penalties_applied.append(
            f"Seniority match ({user_seniority} → {job_seniority})"
            if seniority_score >= 0.8
            else f"Seniority mismatch ({user_seniority} vs {job_seniority})"
        )

        # Final score weights:
        # 0.25 semantic similarity + 0.25 country + 0.25 industry + 0.15 seniority + 0.10 remote
        sim_norm = max(0.0, min(1.0, (sim + 1.0) / 2.0))
        final_score = (
            0.25 * sim_norm
            + 0.25 * country_score
            + 0.25 * industry_score
            + 0.15 * seniority_score
            + 0.10 * remote_score
        )

        all_keywords = list(set(role_keywords + industry_keywords))
        matched_skills = [kw for kw in all_keywords if kw in combined_text.lower()][:5]

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
            "description_text": job.description_text,
            "score": round(final_score, 4),
            "matched_skills": matched_skills,
            "missing_skills": [],
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
