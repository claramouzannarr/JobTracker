"""Tests for interview prep service and router (OpenAI mocked)."""
import json
import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import User, Application, InterviewPrep, ResumeVersion


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
            "what_good_looks_like": ["Structure", "Outcome"],
            "common_mistakes": ["Vague"],
            "follow_ups": [],
            "difficulty": "medium",
            "evidence_from_docs": [],
        },
    ],
    "skill_gaps": {"matched": ["Python"], "missing": ["Go"], "priority_to_learn": []},
    "study_plan": [{"day": 1, "focus": "Behavioral", "tasks": ["Practice STAR"], "deliverable": "3 stories"}],
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
    engine = create_engine("sqlite:///:memory:")
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
    token = create_access_token(data={"sub": user.id})
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
    assert "study_plan" in prep
    assert "answer_rubric" in prep
    assert prep["role_context"]["target_title"] == "Software Engineer"
    assert len(prep["questions"]) >= 1


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
