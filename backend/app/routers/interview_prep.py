from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Application, InterviewPrep, ResumeVersion
from app.schemas import InterviewPrepResponse
from app.auth import get_current_user
from app.services.skill_extraction import extract_skills_from_job_description
from typing import List

router = APIRouter()

# Sample interview questions database (in production, load from file/DB)
INTERVIEW_QUESTIONS = {
    "software_engineer": {
        "technical": [
            "Explain the difference between a stack and a queue.",
            "What is the time complexity of binary search?",
            "How would you implement a hash table?",
            "Explain REST API principles.",
            "What is the difference between SQL and NoSQL databases?",
            "How do you handle concurrency in your code?",
            "Explain the concept of dependency injection.",
            "What is the difference between authentication and authorization?",
        ],
        "behavioral": [
            "Tell me about a challenging project you worked on.",
            "Describe a time when you had to learn a new technology quickly.",
            "How do you handle disagreements with team members?",
            "Tell me about a time you had to debug a difficult issue.",
        ],
    },
    "data_scientist": {
        "technical": [
            "Explain the bias-variance tradeoff.",
            "What is cross-validation and why is it important?",
            "How would you handle missing data in a dataset?",
            "Explain the difference between supervised and unsupervised learning.",
            "What is overfitting and how do you prevent it?",
        ],
        "behavioral": [
            "Tell me about a data analysis project you're proud of.",
            "How do you communicate technical findings to non-technical stakeholders?",
        ],
    },
    "default": {
        "technical": [
            "What are your strengths and weaknesses?",
            "Why are you interested in this role?",
            "Where do you see yourself in 5 years?",
        ],
        "behavioral": [
            "Tell me about yourself.",
            "Describe a challenging situation you faced at work.",
            "How do you prioritize your work?",
        ],
    },
}


def get_questions_for_role(role: str, seniority: str = "entry") -> List[str]:
    """Get interview questions based on role."""
    role_lower = role.lower() if role else ""
    
    # Determine question set
    if "engineer" in role_lower or "developer" in role_lower or "programmer" in role_lower:
        questions = INTERVIEW_QUESTIONS["software_engineer"]
    elif "data" in role_lower or "analyst" in role_lower:
        questions = INTERVIEW_QUESTIONS["data_scientist"]
    else:
        questions = INTERVIEW_QUESTIONS["default"]
    
    # Combine technical and behavioral
    all_questions = questions.get("technical", []) + questions.get("behavioral", [])
    return all_questions


def _generate_interview_prep_internal(
    application_id: int,
    current_user: User,
    db: Session
):
    """Internal function to generate interview prep (can be called from other routers)."""
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    if not application:
        return None
    
    # Check if interview prep already exists
    existing_prep = db.query(InterviewPrep).filter(
        InterviewPrep.application_id == application_id
    ).first()
    
    # Get questions based on role
    role = application.job_title or current_user.primary_role_preference or ""
    years_exp = current_user.years_experience or 0
    seniority = "senior" if years_exp >= 5 else "mid" if years_exp >= 2 else "entry"
    
    questions = get_questions_for_role(role, seniority)
    
    # Extract topics/skills from job description
    topics_to_review = []
    if application.job_description_text:
        from app.services.skill_extraction import extract_skills_from_job_description
        skills = extract_skills_from_job_description(application.job_description_text)
        topics_to_review = list(skills)[:10]  # Top 10 skills
    
    # Resource links (can be enhanced later)
    resources_links = [
        "https://leetcode.com/",
        "https://www.glassdoor.com/Interview/index.htm",
    ]
    
    if existing_prep:
        # Update existing prep
        existing_prep.questions = questions
        existing_prep.topics_to_review = topics_to_review
        existing_prep.resources_links = resources_links
        db.commit()
        db.refresh(existing_prep)
        return existing_prep
    else:
        # Create new prep
        interview_prep = InterviewPrep(
            application_id=application_id,
            questions=questions,
            topics_to_review=topics_to_review,
            resources_links=resources_links,
        )
        db.add(interview_prep)
        db.commit()
        db.refresh(interview_prep)
        return interview_prep


@router.post("/generate/{application_id}", response_model=InterviewPrepResponse)
async def generate_interview_prep_endpoint(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate interview preparation material for an application."""
    result = _generate_interview_prep_internal(application_id, current_user, db)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    return result


@router.get("/{application_id}", response_model=InterviewPrepResponse)
async def get_interview_prep(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get interview preparation for an application."""
    # Verify application belongs to user
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    interview_prep = db.query(InterviewPrep).filter(
        InterviewPrep.application_id == application_id
    ).first()
    
    if not interview_prep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview prep not found. Generate it first."
        )
    
    return interview_prep

