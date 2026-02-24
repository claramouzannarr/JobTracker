from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Application, InterviewPrep, ResumeVersion
from app.schemas import (
    InterviewPrepResponse,
    InterviewPrepGenerateRequest,
    InterviewPrepEvaluateRequest,
    InterviewPrepEvaluateResponse,
    InterviewPrepVoiceAnswerResponse,
)
from app.auth import get_current_user
from app.services.interview_prep_service import (
    generate_prep_package,
    evaluate_answer,
    get_prep_by_id_and_user,
    transcribe_audio,
    get_application_and_user_context,
)
from app.services.skill_extraction import extract_skills_from_job_description
from typing import List

router = APIRouter()

# Legacy: simple question list (used when app status is set to "Interview Prep" before full generate)
INTERVIEW_QUESTIONS_LEGACY = {
    "technical": [
        "Explain the difference between a stack and a queue.",
        "What is the time complexity of binary search?",
        "How would you implement a hash table?",
        "Explain REST API principles.",
        "Tell me about a challenging project you worked on.",
    ],
    "behavioral": [
        "Describe a time when you had to learn a new technology quickly.",
        "How do you handle disagreements with team members?",
        "Tell me about a time you had to debug a difficult issue.",
    ],
}


def _generate_interview_prep_internal(application_id: int, current_user: User, db: Session):
    """
    Create or update a minimal InterviewPrep when application status is set to 'Interview Prep'.
    Does not call OpenAI; full prep is generated via POST /generate.
    """
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id,
    ).first()
    if not application:
        return None
    existing = db.query(InterviewPrep).filter(InterviewPrep.application_id == application_id).first()
    role = (application.job_title or "").lower()
    questions = (
        INTERVIEW_QUESTIONS_LEGACY["technical"] + INTERVIEW_QUESTIONS_LEGACY["behavioral"]
    )
    topics_to_review = []
    if application.job_description_text:
        skills = extract_skills_from_job_description(application.job_description_text)
        topics_to_review = list(skills)[:10]
    resources_links = ["https://leetcode.com/", "https://www.glassdoor.com/Interview/index.htm"]
    if existing:
        existing.questions = existing.questions or questions
        existing.topics_to_review = existing.topics_to_review or topics_to_review
        existing.resources_links = existing.resources_links or resources_links
        db.commit()
        db.refresh(existing)
        return existing
    prep = InterviewPrep(
        application_id=application_id,
        questions=questions,
        topics_to_review=topics_to_review,
        resources_links=resources_links,
        generated_json=None,
    )
    db.add(prep)
    db.commit()
    db.refresh(prep)
    return prep


def _prep_to_response(prep: InterviewPrep) -> InterviewPrepResponse:
    """Build response from InterviewPrep; include generated_json when present."""
    return InterviewPrepResponse(
        id=prep.id,
        application_id=prep.application_id,
        questions=prep.questions or [],
        resources_links=prep.resources_links or [],
        topics_to_review=prep.topics_to_review or [],
        created_at=prep.created_at,
        generated_json=prep.generated_json,
    )


@router.post("/generate")
async def generate_interview_prep(
    body: InterviewPrepGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate tailored interview prep for an application using resume + job description.
    Returns the prep package (generated_json) and persists it to InterviewPrep.
    """
    try:
        prep_json = generate_prep_package(
            db=db,
            application_id=body.application_id,
            user_id=current_user.id,
            days=body.days,
            focus=body.focus,
            difficulty=body.difficulty,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    prep = (
        db.query(InterviewPrep)
        .filter(InterviewPrep.application_id == body.application_id)
        .first()
    )
    if not prep:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Prep record not found after save")
    return {"id": prep.id, "application_id": prep.application_id, "generated_json": prep_json, "created_at": prep.created_at}


@router.post("/evaluate", response_model=InterviewPrepEvaluateResponse)
async def evaluate_interview_answer(
    body: InterviewPrepEvaluateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluate a typed answer against the prep rubric; persist and return score + feedback."""
    try:
        feedback = evaluate_answer(
            db=db,
            interview_prep_id=body.interview_prep_id,
            user_id=current_user.id,
            question_id=body.question_id,
            answer_text=body.answer_text,
            transcript_text=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    return InterviewPrepEvaluateResponse(
        score=feedback.get("score", 0),
        strengths=feedback.get("strengths", []),
        missing_points=feedback.get("missing_points", []),
        improved_answer=feedback.get("improved_answer", ""),
        next_drill=feedback.get("next_drill", ""),
    )


@router.post("/voice-answer", response_model=InterviewPrepVoiceAnswerResponse)
async def voice_answer(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    audio_file: UploadFile = File(...),
    interview_prep_id: int = Form(...),
    question_id: str = Form(...),
):
    """Accept audio upload, transcribe with Whisper, then evaluate as typed answer."""
    content = await audio_file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No audio data received")
    try:
        transcript = transcribe_audio(content, filename=audio_file.filename or "audio.webm")
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    try:
        feedback = evaluate_answer(
            db=db,
            interview_prep_id=interview_prep_id,
            user_id=current_user.id,
            question_id=question_id,
            answer_text=transcript,
            transcript_text=transcript,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    return InterviewPrepVoiceAnswerResponse(
        transcript=transcript,
        score=feedback.get("score", 0),
        strengths=feedback.get("strengths", []),
        missing_points=feedback.get("missing_points", []),
        improved_answer=feedback.get("improved_answer", ""),
        next_drill=feedback.get("next_drill", ""),
    )


@router.get("/{application_id}", response_model=InterviewPrepResponse)
async def get_interview_prep(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get interview preparation for an application (includes generated_json if available)."""
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id,
    ).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    interview_prep = db.query(InterviewPrep).filter(
        InterviewPrep.application_id == application_id,
    ).first()

    if not interview_prep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview prep not found. Generate it first via POST /api/interview-prep/generate",
        )

    return _prep_to_response(interview_prep)
