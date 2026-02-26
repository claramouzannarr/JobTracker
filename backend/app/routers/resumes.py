from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import os
import shutil
from pathlib import Path
from typing import Optional
from app.database import get_db
from app.models import User, Application, ResumeVersion
from app.schemas import ResumeUploadResponse, ResumeVersionResponse, EvaluationScores
from app.auth import get_current_user
from app.services.resume_extraction import extract_resume_text
from app.services.resume_analyzer import analyze_resume

router = APIRouter()

# Create uploads directory
UPLOAD_DIR = Path("uploads/resumes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload/{application_id}", response_model=ResumeUploadResponse)
async def upload_resume(
    application_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
    
    # Save file
    file_extension = Path(file.filename).suffix
    file_path = UPLOAD_DIR / f"{application_id}_{current_user.id}_{file.filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}"
        )
    
    # Extract text
    try:
        extracted_text, page_count = extract_resume_text(str(file_path), file_extension)
        
        # Quality check
        if len(extracted_text) < 100:
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resume text extraction quality too low. Please ensure the file is readable."
            )
    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error extracting text from resume: {str(e)}"
        )
    
    # Determine career level from user
    career_level = "experienced"
    if current_user.years_experience is not None:
        if current_user.years_experience <= 2:
            career_level = "grad"
    
    # Analyze resume with comprehensive pipeline
    try:
        job_description = application.job_description_text
        print(f"Starting resume analysis for application {application_id}, career_level: {career_level}, page_count: {page_count}")
        analysis_result = analyze_resume(
            extracted_text,
            job_description,
            career_level=career_level,
            page_count=page_count
        )
        print(f"Analysis complete. Overall score: {analysis_result.get('overall_score')}")
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        print(f"Error analyzing resume: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing resume: {str(e)}"
        )
    
    # Extract components
    evaluation_scores = {
        "format": analysis_result["format"],
        "grammar": analysis_result["grammar"],
        "job_compatibility": analysis_result["job_compatibility"],
        # Renamed from "ats" to "content_depth" to better reflect meaning
        "content_depth": analysis_result["content_depth"],
        "suggestions": analysis_result["suggestions"]
    }
    parsed_sections = analysis_result["parsed_sections"]
    overall_score = analysis_result["overall_score"]
    
    # Create resume version record
    resume_version = ResumeVersion(
        application_id=application_id,
        file_path=str(file_path),
        extracted_text=extracted_text,
        parsed_sections=parsed_sections,
        evaluation_scores=evaluation_scores,
        overall_score=overall_score,
    )
    db.add(resume_version)
    db.commit()
    db.refresh(resume_version)
    
    return ResumeUploadResponse(
        resume_version=ResumeVersionResponse(
            id=resume_version.id,
            application_id=resume_version.application_id,
            file_path=resume_version.file_path,
            extracted_text=resume_version.extracted_text,
            parsed_sections=resume_version.parsed_sections,
            evaluation_scores=resume_version.evaluation_scores,
            overall_score=resume_version.overall_score,
            created_at=resume_version.created_at,
        ),
        evaluation_scores=evaluation_scores,
        overall_score=overall_score,
        suggestions=analysis_result["suggestions"],
    )


@router.get("/{application_id}/versions", response_model=list[ResumeVersionResponse])
async def get_resume_versions(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
    
    versions = db.query(ResumeVersion).filter(
        ResumeVersion.application_id == application_id
    ).all()
    
    return versions


@router.get("/{resume_version_id}", response_model=ResumeVersionResponse)
async def get_resume_version(
    resume_version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resume_version = db.query(ResumeVersion).filter(
        ResumeVersion.id == resume_version_id
    ).first()
    
    if not resume_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume version not found"
        )
    
    # Verify it belongs to user's application
    application = db.query(Application).filter(
        Application.id == resume_version.application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resume"
        )
    
    return resume_version

