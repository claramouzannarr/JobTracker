from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, Application, ResumeVersion
from app.schemas import ApplicationCreate, ApplicationResponse
from app.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=ApplicationResponse)
async def create_application(
    application: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_application = Application(
        **application.dict(),
        user_id=current_user.id
    )
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application


@router.get("/", response_model=List[ApplicationResponse])
async def get_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    applications = db.query(Application).filter(Application.user_id == current_user.id).all()
    
    # Add resume scores to each application
    result = []
    for app in applications:
        app_dict = {
            "id": app.id,
            "user_id": app.user_id,
            "company_name": app.company_name,
            "job_title": app.job_title,
            "job_url": app.job_url,
            "job_description_text": app.job_description_text,
            "industry": app.industry,
            "country": app.country,
            "status": app.status,
            "notes": app.notes,
            "stage_updated_at": app.stage_updated_at,
            "created_at": app.created_at,
            "updated_at": app.updated_at,
            "resume_score": None
        }
        
        # Get latest resume version and its score
        latest_resume = db.query(ResumeVersion).filter(
            ResumeVersion.application_id == app.id
        ).order_by(ResumeVersion.created_at.desc()).first()
        
        if latest_resume and latest_resume.evaluation_scores:
            app_dict["resume_score"] = latest_resume.evaluation_scores.get("overall_score")
        
        result.append(ApplicationResponse(**app_dict))
    
    return result


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    return application


@router.put("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: int,
    application_update: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Check if status is changing to "Interview"
    old_status = application.status
    new_status = application_update.status
    
    for key, value in application_update.dict().items():
        setattr(application, key, value)
    
    db.commit()
    db.refresh(application)
    
    # Auto-generate interview prep if status changed to "Interview Prep"
    if old_status != "Interview Prep" and new_status == "Interview Prep":
        from app.routers.interview_prep import _generate_interview_prep_internal
        try:
            _generate_interview_prep_internal(application_id, current_user, db)
        except Exception as e:
            # Log error but don't fail the update
            print(f"Error generating interview prep: {e}")
    
    return application


@router.delete("/{application_id}")
async def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    db.delete(application)
    db.commit()
    return {"message": "Application deleted successfully"}

