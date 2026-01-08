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
    """Build user profile embedding from resume and preferences."""
    if embedding_model is None:
        return None
    
    # Combine resume text with preferences
    profile_text_parts = []
    
    if latest_resume_text:
        profile_text_parts.append(latest_resume_text)
    
    if user.primary_role_preference:
        profile_text_parts.append(f"Looking for {user.primary_role_preference} roles")
    
    if user.primary_industry_preference:
        profile_text_parts.append(f"Interested in {user.primary_industry_preference} industry")
    
    if not profile_text_parts:
        return None
    
    profile_text = " ".join(profile_text_parts)
    embedding = embedding_model.encode([profile_text])[0]
    return embedding


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
    
    # Compute similarities
    recommendations = []
    for job in jobs:
        if job.embedding_vector:
            job_embedding = np.array(job.embedding_vector)
            similarity = float(cosine_similarity([user_embedding], [job_embedding])[0][0])
            
            # Apply filters based on user preferences
            if current_user.country and job.country:
                if current_user.country.lower() != job.country.lower():
                    similarity *= 0.8  # Penalize different countries
            
            if current_user.remote_preference:
                if current_user.remote_preference == "remote" and not job.remote_flag:
                    similarity *= 0.7
                elif current_user.remote_preference == "onsite" and job.remote_flag:
                    similarity *= 0.7
            
            recommendations.append(
                JobRecommendation(
                    id=job.id,
                    title=job.title,
                    company=job.company,
                    description_text=job.description_text,
                    country=job.country,
                    remote_flag=job.remote_flag,
                    job_url=job.job_url,
                    similarity_score=similarity,
                )
            )
    
    # Sort by similarity and return top N
    recommendations.sort(key=lambda x: x.similarity_score, reverse=True)
    return recommendations[:limit]

