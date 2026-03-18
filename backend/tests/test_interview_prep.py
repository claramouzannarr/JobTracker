"""Tests for interview prep service and router (OpenAI mocked)."""
import json
import sys
import pytest
from unittest.mock import patch, MagicMock

from fastapi import FastAPI
import types
import importlib.machinery

# Avoid importing heavyweight ML/native deps during test collection.
# `app.routers.interview_prep` imports `app.services.skill_extraction` at import-time.
if "app.services.skill_extraction" not in sys.modules:
    _skill_stub = types.ModuleType("app.services.skill_extraction")
    _skill_stub.__spec__ = importlib.machinery.ModuleSpec("app.services.skill_extraction", loader=None)
    _skill_stub.extract_skills_from_job_description = MagicMock(return_value=set())
    sys.modules["app.services.skill_extraction"] = _skill_stub

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.routers import interview_prep
from app.models import User, Application, InterviewPrep, ResumeVersion

# Minimal app for these tests: only include the interview prep router.
app = FastAPI()
app.include_router(interview_prep.router, prefix="/api/interview-prep", tags=["interview-prep"])


# Valid prep package JSON (minimal required keys)
SAMPLE_PREP_JSON = {
    "role_context": {
        "target_title": "Software Engineer",
        "seniority": "mid",
        "company": "Acme",
        "key_requirements": ["Python", "API design"],
    },
    "questions": [
        {
            "id": "q1",
            "type": "behavioral",
            "question": "Tell me about a challenge.",
            "what_good_looks_like": ["Structure", "Outcome", "Impact"],
            "evidence_from_docs": ["Resume mentions Python APIs."],
        },
    ],
    "skill_gaps": {"matched": ["Python"], "missing": ["Go"], "priority_to_learn": []},
    "answer_rubric": {
        "scoring_scale": "0-5",
        "criteria": [
            {"name": "structure", "description": "Clear structure"},
            {"name": "relevance", "description": "Relevant to question"},
        ],
    },
}

SAMPLE_EVAL_JSON = {
    "score": 3,
    "strengths": ["Clear structure"],
    "missing_points": ["Add a specific metric"],
    "improved_answer": "In my previous role I led a project that increased throughput by 20%.",
    "next_drill": "Practice quantifying impact.",
}


@pytest.fixture
def db_session():
    """In-memory SQLite session with User, Application, ResumeVersion, InterviewPrep."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        user = User(
            email="prep@test.com",
            password_hash="hash",
            years_experience=3,
            primary_role_preference="Engineer",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        app_model = Application(
            user_id=user.id,
            company_name="Acme",
            job_title="Software Engineer",
            job_description_text="We need Python and APIs.",
        )
        session.add(app_model)
        session.commit()
        session.refresh(app_model)
        rv = ResumeVersion(
            application_id=app_model.id,
            file_path="/tmp/resume.pdf",
            extracted_text="I have 3 years of Python and API experience.",
        )
        session.add(rv)
        session.commit()
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(db_session):
    """Create a user and return headers with a valid token (sub = user id for get_current_user)."""
    from app.auth import create_access_token
    user = db_session.query(User).first()
    # JWT `sub` should be a string.
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_generate_returns_valid_json_with_required_keys(client, db_session, auth_headers):
    """Generate endpoint returns valid JSON with required keys."""
    with patch("app.services.interview_prep_service._get_openai_client") as mock_client:
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(SAMPLE_PREP_JSON),
                    )
                )
            ]
        )
        mock_client.return_value = mock_openai

        response = client.post(
            "/api/interview-prep/generate",
            json={
                "application_id": db_session.query(Application).first().id,
                "days": 7,
                "focus": ["technical", "behavioral"],
                "difficulty": "mixed",
            },
            headers=auth_headers,
            timeout=10,
        )

    assert response.status_code == 200
    data = response.json()
    assert "generated_json" in data
    prep = data["generated_json"]
    assert "role_context" in prep
    assert "questions" in prep
    assert "skill_gaps" in prep
    assert "answer_rubric" in prep
    assert prep["role_context"]["target_title"] == "Software Engineer"
    assert len(prep["questions"]) >= 1


def test_generate_uses_cache_for_same_inputs(client, db_session, auth_headers):
    """Generating twice with same resume/JD should only call OpenAI once (cache hit)."""
    app_model = db_session.query(Application).first()

    with patch("app.services.interview_prep_service._get_openai_client") as mock_client:
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(SAMPLE_PREP_JSON),
                    )
                )
            ]
        )
        mock_client.return_value = mock_openai

        # First generate
        resp1 = client.post(
            "/api/interview-prep/generate",
            json={
                "application_id": app_model.id,
                "days": 7,
                "focus": ["technical", "behavioral"],
                "difficulty": "mixed",
            },
            headers=auth_headers,
            timeout=10,
        )
        assert resp1.status_code == 200

        # Second generate with same inputs should hit cache and not call OpenAI again
        resp2 = client.post(
            "/api/interview-prep/generate",
            json={
                "application_id": app_model.id,
                "days": 7,
                "focus": ["technical", "behavioral"],
                "difficulty": "mixed",
            },
            headers=auth_headers,
            timeout=10,
        )
        assert resp2.status_code == 200
        # Only one OpenAI call for both requests
        assert mock_openai.chat.completions.create.call_count == 1


def test_generate_recomputes_when_resume_changes(client, db_session, auth_headers):
    """Changing resume text should trigger a new OpenAI generation."""
    app_model = db_session.query(Application).first()

    with patch("app.services.interview_prep_service._get_openai_client") as mock_client:
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(SAMPLE_PREP_JSON),
                    )
                )
            ]
        )
        mock_client.return_value = mock_openai

        # First generate with initial resume
        resp1 = client.post(
            "/api/interview-prep/generate",
            json={
                "application_id": app_model.id,
                "days": 7,
                "focus": ["technical", "behavioral"],
                "difficulty": "mixed",
            },
            headers=auth_headers,
            timeout=10,
        )
        assert resp1.status_code == 200

        # Change resume text for same application
        rv = db_session.query(ResumeVersion).filter(ResumeVersion.application_id == app_model.id).first()
        rv.extracted_text = (rv.extracted_text or "") + " Extra detail about Kubernetes."
        db_session.commit()

        # Second generate should detect hash change and call OpenAI again
        resp2 = client.post(
            "/api/interview-prep/generate",
            json={
                "application_id": app_model.id,
                "days": 7,
                "focus": ["technical", "behavioral"],
                "difficulty": "mixed",
            },
            headers=auth_headers,
            timeout=10,
        )
        assert resp2.status_code == 200
        assert mock_openai.chat.completions.create.call_count == 2


def test_evaluate_returns_score_and_improved_answer(client, db_session, auth_headers):
    """Evaluate endpoint returns score 0-5 and improved_answer."""
    app_model = db_session.query(Application).first()
    prep = InterviewPrep(
        application_id=app_model.id,
        generated_json=SAMPLE_PREP_JSON,
        questions=[],
        resources_links=[],
        topics_to_review=[],
    )
    db_session.add(prep)
    db_session.commit()
    db_session.refresh(prep)

    with patch("app.services.interview_prep_service._get_openai_client") as mock_client:
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(SAMPLE_EVAL_JSON),
                    )
                )
            ]
        )
        mock_client.return_value = mock_openai

        response = client.post(
            "/api/interview-prep/evaluate",
            json={
                "interview_prep_id": prep.id,
                "question_id": "q1",
                "answer_text": "I once led a project and it went well.",
            },
            headers=auth_headers,
            timeout=10,
        )

    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert 0 <= data["score"] <= 5
    assert "improved_answer" in data
    assert "strengths" in data
    assert "missing_points" in data
    assert "next_drill" in data


def test_daily_generate_limit_blocks_after_threshold(client, db_session, auth_headers):
    """Per-user daily limit should block after 3 generate calls."""
    user = db_session.query(User).first()

    with patch("app.services.interview_prep_service._get_openai_client") as mock_client:
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(SAMPLE_PREP_JSON),
                    )
                )
            ]
        )
        mock_client.return_value = mock_openai

        payload_base = {
            "days": 7,
            "focus": ["technical", "behavioral"],
            "difficulty": "mixed",
        }

        # First three should pass (use three distinct applications -> three InterviewPrep rows)
        for i in range(3):
            app_model = Application(
                user_id=user.id,
                company_name=f"Acme {i}",
                job_title="Software Engineer",
                job_description_text=f"We need Python and APIs. Variant {i}",
            )
            db_session.add(app_model)
            db_session.commit()
            db_session.refresh(app_model)
            r = client.post(
                "/api/interview-prep/generate",
                json={"application_id": app_model.id, **payload_base},
                headers=auth_headers,
                timeout=10,
            )
            assert r.status_code == 200

        # Fourth should hit rate limit and return 429-like error
        app4 = Application(
            user_id=user.id,
            company_name="Acme 4",
            job_title="Software Engineer",
            job_description_text="We need Python and APIs. Variant 4",
        )
        db_session.add(app4)
        db_session.commit()
        db_session.refresh(app4)
        r4 = client.post(
            "/api/interview-prep/generate",
            json={"application_id": app4.id, **payload_base},
            headers=auth_headers,
            timeout=10,
        )
        assert r4.status_code in (429,)


def test_daily_evaluate_limit_blocks_after_threshold(client, db_session, auth_headers):
    """Per-user daily limit should block after 30 evaluate calls."""
    app_model = db_session.query(Application).first()
    prep = InterviewPrep(
        application_id=app_model.id,
        generated_json=SAMPLE_PREP_JSON,
        questions=[],
        resources_links=[],
        topics_to_review=[],
    )
    db_session.add(prep)
    db_session.commit()
    db_session.refresh(prep)

    with patch("app.services.interview_prep_service._get_openai_client") as mock_client:
        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(SAMPLE_EVAL_JSON),
                    )
                )
            ]
        )
        mock_client.return_value = mock_openai

        payload = {
            "interview_prep_id": prep.id,
            "question_id": "q1",
            "answer_text": "I once led a project and it went well.",
        }

        # First 30 evals should pass
        for _ in range(30):
            r = client.post(
                "/api/interview-prep/evaluate",
                json=payload,
                headers=auth_headers,
                timeout=10,
            )
            assert r.status_code == 200

        # 31st should be blocked
        r31 = client.post(
            "/api/interview-prep/evaluate",
            json=payload,
            headers=auth_headers,
            timeout=10,
        )
    assert r31.status_code == 429


def test_voice_answer_returns_transcript_and_evaluation(client, db_session, auth_headers):
    """Voice-answer endpoint returns transcript and evaluation (Whisper + eval mocked)."""
    app_model = db_session.query(Application).first()
    prep = InterviewPrep(
        application_id=app_model.id,
        generated_json=SAMPLE_PREP_JSON,
        questions=[],
        resources_links=[],
        topics_to_review=[],
    )
    db_session.add(prep)
    db_session.commit()
    db_session.refresh(prep)

    with patch("app.services.interview_prep_service._get_openai_client") as mock_client:
        mock_openai = MagicMock()
        # Whisper transcription
        mock_openai.audio.transcriptions.create.return_value = MagicMock(
            text="I led a team project last year and we delivered on time."
        )
        # Chat completion for evaluation
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(SAMPLE_EVAL_JSON),
                    )
                )
            ]
        )
        mock_client.return_value = mock_openai

        # Minimal audio bytes (not valid webm; Whisper mock doesn't care)
        audio_bytes = b"\x00\x00\x00\x00"
        files = {"audio_file": ("audio.webm", audio_bytes, "audio/webm")}
        data_form = {"interview_prep_id": str(prep.id), "question_id": "q1"}

        response = client.post(
            "/api/interview-prep/voice-answer",
            data=data_form,
            files=files,
            headers=auth_headers,
            timeout=10,
        )

    assert response.status_code == 200
    body = response.json()
    assert "transcript" in body
    assert body["transcript"] == "I led a team project last year and we delivered on time."
    assert "score" in body
    assert 0 <= body["score"] <= 5
    assert "improved_answer" in body
    assert "strengths" in body
    assert "missing_points" in body
