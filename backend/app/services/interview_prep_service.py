"""
Interview Prep service: generate tailored prep (OpenAI + context from resume/JD),
evaluate typed or voice answers with rubric-based feedback.
Voice of the assistant: recruiter + career coach; grounded in provided context only.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Application, InterviewPrep, InterviewAnswer, ResumeVersion, User

logger = logging.getLogger(__name__)

# Max chars to send for resume and JD (kept low to reduce OpenAI cost)
MAX_RESUME_CHARS = 4_000
MAX_JD_CHARS = 4_000

# Prep package JSON schema (for prompt + validation)
PREP_SCHEMA = """
{
  "role_context": {
    "target_title": "string",
    "seniority": "entry|mid|senior",
    "company": "string|null",
    "key_requirements": ["string"]
  },
  "questions": [
    {
      "id": "q1",
      "type": "behavioral|technical|case|resume",
      "question": "string",
      "what_good_looks_like": ["bullet"],
      "common_mistakes": ["bullet"],
      "follow_ups": ["string"],
      "difficulty": "easy|medium|hard",
      "evidence_from_docs": ["short quote or paraphrase, max 1 sentence each"]
    }
  ],
  "skill_gaps": {
    "matched": ["string"],
    "missing": ["string"],
    "priority_to_learn": ["string"]
  },
  "study_plan": [
    {
      "day": 1,
      "focus": "string",
      "tasks": ["string"],
      "deliverable": "string"
    }
  ],
  "answer_rubric": {
    "scoring_scale": "0-5",
    "criteria": [
      {"name": "structure", "description": "string"},
      {"name": "relevance", "description": "string"},
      {"name": "evidence", "description": "string"},
      {"name": "clarity", "description": "string"},
      {"name": "impact", "description": "string"}
    ]
  }
}
"""

SYSTEM_PROMPT_GENERATE = """You are a recruiter and career coach. You produce structured interview preparation grounded only in the provided resume and job description context. If a detail is not in the context, say you cannot confirm it. Be concise and practical. Output only valid JSON matching the given schema. Do not include markdown code fences or any text outside the JSON."""

SYSTEM_PROMPT_EVAL = """You are a recruiter assessing interview answers. Score using the rubric and provide actionable coaching. Do not invent experience for the candidate. If the answer lacks evidence or is vague, say what to add. If the answer includes claims not supported by the resume, warn: "Only say this if it's true for you." Output only valid JSON with keys: score (0-5 integer), strengths (array of strings), missing_points (array of strings), improved_answer (string, concise, first person), next_drill (string). Do not include markdown or text outside the JSON."""


def _get_openai_client():
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    from openai import OpenAI
    return OpenAI(api_key=settings.openai_api_key)


def _openai_error_message(exc: Exception) -> str:
    """Return a user-friendly message for OpenAI API errors (e.g. billing, rate limit)."""
    err_str = str(exc).lower()
    if "billing" in err_str or "billing_not_active" in err_str or "account is not active" in err_str:
        return "OpenAI billing is not active. Please add a payment method at https://platform.openai.com/account/billing and try again."
    if "rate" in err_str or "429" in err_str:
        return "OpenAI rate limit reached. Please wait a moment and try again."
    if "invalid_api_key" in err_str or "authentication" in err_str:
        return "OpenAI API key is invalid or expired. Please check your OPENAI_API_KEY."
    return f"Interview prep generation failed: {exc}"


def _infer_seniority(years_experience: Optional[int]) -> str:
    if years_experience is None:
        return "mid"
    if years_experience < 2:
        return "entry"
    if years_experience >= 5:
        return "senior"
    return "mid"


def get_resume_text_for_application(db: Session, application_id: int, user_id: int) -> Optional[str]:
    """Return latest resume extracted text for this application, or None."""
    rv = (
        db.query(ResumeVersion)
        .filter(
            ResumeVersion.application_id == application_id,
            ResumeVersion.extracted_text.isnot(None),
        )
        .order_by(ResumeVersion.created_at.desc())
        .first()
    )
    if rv and rv.extracted_text and len((rv.extracted_text or "").strip()) >= 50:
        return (rv.extracted_text or "").strip()
    return None


def get_application_and_user_context(
    db: Session, application_id: int, user_id: int
) -> Tuple[Optional[Application], Optional[User], Optional[str]]:
    """Load application, user, and latest resume text. Application must belong to user."""
    app = (
        db.query(Application)
        .filter(Application.id == application_id, Application.user_id == user_id)
        .first()
    )
    if not app:
        return None, None, None
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return app, None, None
    resume_text = get_resume_text_for_application(db, application_id, user_id)
    return app, user, resume_text


def _truncate(text: str, max_chars: int) -> str:
    if not text or len(text) <= max_chars:
        return text or ""
    return text[: max_chars] + "\n\n[Truncated for length.]"


def _build_generation_user_prompt(
    job_title: str,
    company: str,
    seniority: str,
    days: int,
    focus: List[str],
    difficulty: str,
    resume_text: Optional[str],
    jd_text: Optional[str],
    user_prefs_summary: str,
) -> str:
    resume_block = _truncate(resume_text or "No resume text provided.", MAX_RESUME_CHARS)
    jd_block = _truncate(jd_text or "No job description provided.", MAX_JD_CHARS)
    return f"""Generate an interview preparation package for the following role and candidate context.

Target role: {job_title}
Company: {company or "Not specified"}
Inferred seniority: {seniority}
Preparation period: {days} days
Focus areas: {", ".join(focus) if focus else "technical, behavioral"}
Difficulty: {difficulty}

User preferences summary: {user_prefs_summary or "Not specified"}

--- RESUME (use only this content; do not invent details) ---
{resume_block}

--- JOB DESCRIPTION (use only this content; do not claim to have reviewed company website) ---
{jd_block}

Rules:
- If a detail is not in the resume or job description above, do not confirm it; use "Not enough information in the provided resume/job description to confirm" where appropriate and give general best-practice advice.
- Do not invent company-specific facts. Ground all role_context and questions in the retrieved context.
- Include at least 6 technical questions, 6 behavioral questions, 2 resume-specific questions. Add case questions if the role suggests it.
- evidence_from_docs: short quotes or one-sentence paraphrases only.
- Study plan must have exactly {days} days.
- Output ONLY valid JSON matching this schema (no markdown, no code fences):
{PREP_SCHEMA}
"""


def generate_prep_package(
    db: Session,
    application_id: int,
    user_id: int,
    days: int = 7,
    focus: Optional[List[str]] = None,
    difficulty: str = "mixed",
) -> Dict[str, Any]:
    """
    Build context from DB (resume + JD + user), call OpenAI, return and persist prep JSON.
    Raises ValueError if OPENAI_API_KEY missing or application/user invalid.
    """
    focus = focus or ["technical", "behavioral"]
    app, user, resume_text = get_application_and_user_context(db, application_id, user_id)
    if not app:
        raise ValueError("Application not found or access denied")
    if not user:
        raise ValueError("User not found")

    seniority = _infer_seniority(user.years_experience)
    prefs = []
    if user.primary_role_preference:
        prefs.append(f"Role: {user.primary_role_preference}")
    if user.primary_industry_preference:
        prefs.append(f"Industry: {user.primary_industry_preference}")
    if user.remote_preference:
        prefs.append(f"Remote: {user.remote_preference}")
    if user.desired_countries:
        prefs.append(f"Locations: {user.desired_countries}")
    user_prefs_summary = "; ".join(prefs) if prefs else "Not specified"

    jd_text = (app.job_description_text or "").strip() or None
    if not resume_text and not jd_text:
        raise ValueError("No resume text or job description available for this application.")

    user_prompt = _build_generation_user_prompt(
        job_title=app.job_title or "Unknown",
        company=app.company_name or "",
        seniority=seniority,
        days=days,
        focus=focus,
        difficulty=difficulty,
        resume_text=resume_text,
        jd_text=jd_text,
        user_prefs_summary=user_prefs_summary,
    )

    client = _get_openai_client()
    try:
        response = client.chat.completions.create(
            model=settings.openai_model_generate,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_GENERATE},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=3500,
            temperature=0.3,
        )
    except Exception as e:
        logger.exception("OpenAI generate call failed")
        raise RuntimeError(_openai_error_message(e)) from e

    content = (response.choices[0].message.content or "").strip()
    # Strip markdown code block if present
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```\s*$", "", content)
    try:
        prep_json = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("OpenAI returned invalid JSON: %s", content[:500])
        raise RuntimeError("Generated prep was not valid JSON") from e

    # Validate required top-level keys
    required = ["role_context", "questions", "skill_gaps", "study_plan", "answer_rubric"]
    for key in required:
        if key not in prep_json:
            prep_json[key] = {} if key in ("role_context", "skill_gaps", "answer_rubric") else [] if key in ("questions", "study_plan") else {}

    # Persist
    existing = (
        db.query(InterviewPrep)
        .filter(InterviewPrep.application_id == application_id)
        .first()
    )
    if existing:
        existing.generated_json = prep_json
        db.commit()
        db.refresh(existing)
        return prep_json
    prep = InterviewPrep(
        application_id=application_id,
        generated_json=prep_json,
        questions=[],  # legacy
        resources_links=[],
        topics_to_review=[],
    )
    db.add(prep)
    db.commit()
    db.refresh(prep)
    return prep_json


def get_prep_by_id_and_user(db: Session, interview_prep_id: int, user_id: int) -> Optional[InterviewPrep]:
    """Return InterviewPrep if it belongs to an application owned by user."""
    prep = db.query(InterviewPrep).filter(InterviewPrep.id == interview_prep_id).first()
    if not prep:
        return None
    app = db.query(Application).filter(
        Application.id == prep.application_id,
        Application.user_id == user_id,
    ).first()
    return prep if app else None


def _find_question(prep_json: Dict[str, Any], question_id: str) -> Optional[Dict[str, Any]]:
    for q in prep_json.get("questions") or []:
        if q.get("id") == question_id:
            return q
    return None


def _build_eval_user_prompt(
    question_obj: Dict[str, Any],
    rubric: Dict[str, Any],
    answer_text: str,
) -> str:
    good_bullets = question_obj.get("what_good_looks_like") or []
    criteria = (rubric.get("criteria") or [])
    criteria_text = "\n".join(
        f"- {c.get('name', '')}: {c.get('description', '')}" for c in criteria
    )
    return f"""Question (type: {question_obj.get('type', 'unknown')}): {question_obj.get('question', '')}

What good looks like:
{chr(10).join('- ' + b for b in good_bullets)}

Scoring criteria (0-5):
{criteria_text}

Candidate's answer:
---
{answer_text}
---

Score the answer 0-5 and provide JSON with: score (integer 0-5), strengths (array of strings), missing_points (array of strings), improved_answer (string, concise, in first person), next_drill (string). Do not invent experience. If they claim something not in their resume, add a strength or missing_point: "Only say this if it's true for you." Output only valid JSON, no markdown."""


def evaluate_answer(
    db: Session,
    interview_prep_id: int,
    user_id: int,
    question_id: str,
    answer_text: str,
    transcript_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load prep, find question, call OpenAI for score + feedback, persist InterviewAnswer, return feedback dict.
    """
    prep = get_prep_by_id_and_user(db, interview_prep_id, user_id)
    if not prep or not prep.generated_json:
        raise ValueError("Interview prep not found or has no generated package")
    prep_json = prep.generated_json
    question_obj = _find_question(prep_json, question_id)
    if not question_obj:
        raise ValueError(f"Question id '{question_id}' not found in this prep")
    rubric = prep_json.get("answer_rubric") or {}
    text_to_eval = (answer_text or "").strip()
    if not text_to_eval:
        raise ValueError("Answer text is required")

    user_prompt = _build_eval_user_prompt(question_obj, rubric, text_to_eval)
    client = _get_openai_client()
    try:
        response = client.chat.completions.create(
            model=settings.openai_model_eval,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_EVAL},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=512,
            temperature=0.2,
        )
    except Exception as e:
        logger.exception("OpenAI eval call failed")
        raise RuntimeError(_openai_error_message(e)) from e

    content = (response.choices[0].message.content or "").strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```\s*$", "", content)
    try:
        feedback = json.loads(content)
    except json.JSONDecodeError:
        feedback = {"score": 0, "strengths": [], "missing_points": ["Evaluation could not be parsed."], "improved_answer": "", "next_drill": ""}

    score = feedback.get("score")
    if score is not None and not isinstance(score, int):
        try:
            score = int(score)
        except (TypeError, ValueError):
            score = 0
    if score is None:
        score = 0
    score = max(0, min(5, score))

    feedback["score"] = score
    for key in ("strengths", "missing_points"):
        if key not in feedback or not isinstance(feedback[key], list):
            feedback[key] = []
    for key in ("improved_answer", "next_drill"):
        if key not in feedback:
            feedback[key] = ""

    # Persist
    answer = InterviewAnswer(
        interview_prep_id=interview_prep_id,
        question_id=question_id,
        answer_text=text_to_eval,
        transcript_text=transcript_text,
        score=score,
        feedback_json=feedback,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)

    return feedback


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribe using OpenAI Whisper. Returns transcript text."""
    client = _get_openai_client()
    import io
    file_like = io.BytesIO(audio_bytes)
    file_like.name = filename
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=file_like,
        )
        return (transcript.text or "").strip()
    except Exception as e:
        logger.exception("Whisper transcription failed")
        raise RuntimeError(_openai_error_message(e)) from e
