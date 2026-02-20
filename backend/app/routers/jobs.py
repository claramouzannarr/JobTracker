from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User, JobPosting
from app.schemas import JobRecommendation
from app.auth import get_current_user
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

router = APIRouter()

# Load embedding model
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    embedding_model = None
    print(f"Warning: Could not load embedding model: {e}")


def get_user_profile_embedding(user: User, latest_resume_text: Optional[str] = None) -> Optional[np.ndarray]:
    """
    Build user profile embedding from resume and questionnaire preferences.
    The questionnaire data (role and industry preferences) is incorporated into the embedding
    to ensure semantic similarity captures user's desired job characteristics.
    """
    if embedding_model is None:
        return None
    
    # Combine resume text with questionnaire preferences
    profile_text_parts = []
    
    if latest_resume_text:
        profile_text_parts.append(latest_resume_text)
    
    # Incorporate questionnaire data into embedding
    if user.primary_role_preference:
        profile_text_parts.append(f"Looking for {user.primary_role_preference} roles")
    
    if user.primary_industry_preference:
        profile_text_parts.append(f"Interested in {user.primary_industry_preference} industry")
    
    if not profile_text_parts:
        return None
    
    profile_text = " ".join(profile_text_parts)
    embedding = embedding_model.encode([profile_text])[0]
    return embedding


def estimate_job_seniority(job_title: str, description: Optional[str] = None) -> str:
    """
    Estimate job seniority level from title and description.
    Returns: 'entry', 'mid', or 'senior'
    """
    title_lower = job_title.lower()
    desc_lower = (description or "").lower()
    combined = f"{title_lower} {desc_lower}"
    
    # Senior level indicators
    if any(keyword in combined for keyword in ['senior', 'lead', 'principal', 'staff', 'architect', 'director', 'head']):
        return 'senior'
    
    # Entry level indicators
    if any(keyword in combined for keyword in ['junior', 'entry', 'associate', 'intern', 'graduate', 'new grad']):
        return 'entry'
    
    # Default to mid-level
    return 'mid'


def extract_job_type(description: Optional[str] = None) -> Optional[str]:
    """
    Extract job type from description.
    Returns: 'full-time', 'part-time', 'internship', or None
    """
    if not description:
        return None
    
    desc_lower = description.lower()
    
    if 'intern' in desc_lower or 'internship' in desc_lower:
        return 'internship'
    if 'part-time' in desc_lower or 'part time' in desc_lower:
        return 'part-time'
    if 'full-time' in desc_lower or 'full time' in desc_lower:
        return 'full-time'
    
    return None


def estimate_user_seniority(years_experience: Optional[int]) -> str:
    """
    Estimate user's seniority level from years of experience.
    Returns: 'entry', 'mid', or 'senior'
    """
    if years_experience is None:
        return 'mid'  # Default assumption
    
    if years_experience < 2:
        return 'entry'
    elif years_experience >= 5:
        return 'senior'
    else:
        return 'mid'


def apply_preference_filters(
    similarity: float,
    user: User,
    job: JobPosting
) -> float:
    """
    Apply preference-based filters from questionnaire data to adjust similarity score.
    This is where the sign-in questionnaire data is primarily used for job recommendations.
    
    Returns: Adjusted similarity score (0.0 to 1.0)
    """
    adjusted_similarity = similarity
    
    # A. Country/Location Filtering
    if user.country and job.country:
        user_country_lower = user.country.lower()
        job_country_lower = job.country.lower()
        
        if user_country_lower == job_country_lower:
            # Exact match - no penalty
            pass
        elif user.desired_countries:
            # Check if job country is in desired countries list
            desired_lower = [c.lower() if isinstance(c, str) else str(c).lower() for c in user.desired_countries]
            if job_country_lower in desired_lower:
                # Job is in desired country - no penalty
                pass
            else:
                # Different country, not in desired list - 20% penalty
                adjusted_similarity *= 0.8
        else:
            # Different country, no desired countries specified - 20% penalty
            adjusted_similarity *= 0.8
    
    # B. Remote Preference Filtering
    if user.remote_preference:
        if user.remote_preference == "remote" and not job.remote_flag:
            # User wants remote, job is onsite - 30% penalty
            adjusted_similarity *= 0.7
        elif user.remote_preference == "onsite" and job.remote_flag:
            # User wants onsite, job is remote - 30% penalty
            adjusted_similarity *= 0.7
        elif user.remote_preference == "hybrid":
            # User wants hybrid - slight preference for hybrid jobs
            # (No penalty, but could add bonus for hybrid jobs if we had that field)
            pass
        # "any" preference - no penalty
    
    # C. Job Type Filtering
    if user.job_type_preference and user.job_type_preference != "any":
        job_type = extract_job_type(job.description_text)
        if job_type and job_type != user.job_type_preference:
            # Job type doesn't match preference - 40% penalty
            adjusted_similarity *= 0.6
    
    # D. Experience Level/Seniority Filtering
    if user.years_experience is not None:
        user_seniority = estimate_user_seniority(user.years_experience)
        job_seniority = estimate_job_seniority(job.title, job.description_text)
        
        if user_seniority == 'senior' and job_seniority == 'entry':
            # Experienced user, entry-level job - 50% penalty (major mismatch)
            adjusted_similarity *= 0.5
        elif user_seniority == 'entry' and job_seniority == 'senior':
            # Entry-level user, senior job - 50% penalty (major mismatch)
            adjusted_similarity *= 0.5
        elif user_seniority != job_seniority:
            # Slight mismatch (e.g., mid vs senior) - 15% penalty
            adjusted_similarity *= 0.85
    
    # E. Industry Preference Filtering
    # Note: Industry is also captured in embedding, but explicit filter ensures preference is respected
    # Since JobPosting doesn't have industry field, we rely on embedding similarity
    # which already incorporates industry preference. Could add industry field to JobPosting model in future.
    
    # F. Work Authorization Filtering
    # Note: Would require job to specify required authorization
    # For now, we can't filter on this without additional job metadata
    # Could be added if JobPosting model includes work_authorization_required field
    
    return max(0.0, min(1.0, adjusted_similarity))  # Clamp between 0 and 1


@router.get("/recommendations", response_model=List[JobRecommendation])
async def get_job_recommendations(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job recommendations based on user profile."""
    # Get user's latest resume text (from most recent application)
    from app.models import Application, ResumeVersion
    
    latest_application = db.query(Application).filter(
        Application.user_id == current_user.id
    ).order_by(Application.created_at.desc()).first()
    
    latest_resume_text = None
    if latest_application:
        latest_resume = db.query(ResumeVersion).filter(
            ResumeVersion.application_id == latest_application.id
        ).order_by(ResumeVersion.created_at.desc()).first()
        if latest_resume:
            latest_resume_text = latest_resume.extracted_text
    
    # Get user profile embedding
    user_embedding = get_user_profile_embedding(current_user, latest_resume_text)
    
    if user_embedding is None or embedding_model is None:
        # Return empty or basic recommendations
        jobs = db.query(JobPosting).limit(limit).all()
        return [
            JobRecommendation(
                id=job.id,
                title=job.title,
                company=job.company,
                description_text=job.description_text,
                country=job.country,
                remote_flag=job.remote_flag,
                job_url=job.job_url,
                similarity_score=0.5,
            )
            for job in jobs
        ]
    
    # Get all job postings with embeddings
    jobs = db.query(JobPosting).filter(
        JobPosting.embedding_vector.isnot(None)
    ).all()
    
    if not jobs:
        return []
    
    # Compute similarities and apply preference filters
    recommendations = []
    for job in jobs:
        if job.embedding_vector:
            job_embedding = np.array(job.embedding_vector)
            
            # Step 1: Compute base semantic similarity
            base_similarity = float(cosine_similarity([user_embedding], [job_embedding])[0][0])
            
            # Step 2: Apply preference-based filters from questionnaire
            # This is where all questionnaire data is used to personalize recommendations
            final_similarity = apply_preference_filters(
                similarity=base_similarity,
                user=current_user,
                job=job
            )
            
            recommendations.append(
                JobRecommendation(
                    id=job.id,
                    title=job.title,
                    company=job.company,
                    description_text=job.description_text,
                    country=job.country,
                    remote_flag=job.remote_flag,
                    job_url=job.job_url,
                    similarity_score=final_similarity,
                )
            )
    
    # Sort by final similarity score (after all filters) and return top N
    recommendations.sort(key=lambda x: x.similarity_score, reverse=True)
    return recommendations[:limit]

