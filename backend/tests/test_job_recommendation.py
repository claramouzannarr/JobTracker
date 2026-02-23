"""Tests for job recommendation service (scoring and sorting)."""
import sys
import pytest
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import JobPosting, User
from app.services.job_recommendation_service import recommend_jobs, _cosine_similarity

# Mock skill_extraction so we don't load pandas/numpy (can crash on some envs)
_mock_skill_module = MagicMock()
_mock_skill_module.extract_skills = MagicMock(return_value=set())
_mock_skill_module.extract_skills_from_job_description = MagicMock(return_value=set())


def test_cosine_similarity():
    """Cosine similarity is 1 for identical vectors, 0 for orthogonal."""
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert abs(_cosine_similarity(a, b) - 1.0) < 1e-9
    c = [0.0, 1.0, 0.0]
    assert abs(_cosine_similarity(a, c)) < 1e-9


@pytest.fixture
def db_session():
    """In-memory SQLite session with User and JobPosting (minimal columns)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_recommendation_returns_sorted_scores(db_session):
    """Recommendation list is sorted by score descending."""
    user = User(
        email="test@test.com",
        password_hash="hash",
        primary_role_preference="Engineer",
        remote_preference="any",
    )
    db_session.add(user)
    db_session.commit()
    user_id = user.id
    vec_low = [0.01] * 384
    vec_high = [0.9] * 384
    for i, vec in enumerate([vec_low, vec_high]):
        job = JobPosting(
            source="adzuna",
            external_id=f"ext-{i}",
            title=f"Job {i}",
            company="Co",
            description_text="Desc",
            embedding_vector=vec,
        )
        db_session.add(job)
    db_session.commit()

    with patch.dict(sys.modules, {"app.services.skill_extraction": _mock_skill_module}), \
         patch("app.services.job_recommendation_service.embed_text") as mock_embed:
        mock_embed.return_value = [0.85] * 384
        results = recommend_jobs(db_session, user_id=user_id, limit=5)
    assert len(results) == 2
    assert results[0]["score"] >= results[1]["score"]
    assert "score" in results[0]
    assert "matched_skills" in results[0]
    assert "missing_skills" in results[0]
    assert "penalties_applied" in results[0]
