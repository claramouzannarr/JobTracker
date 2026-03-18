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
        primary_industry_preference="Finance",
        primary_role_preference="Analyst",
        desired_countries=["gb"],
        remote_preference="remote",
    )
    db_session.add(user)
    db_session.commit()
    user_id = user.id
    vec = [0.5] * 384
    # Job 0 matches finance + GB + remote
    job0 = JobPosting(
        source="adzuna",
        external_id="ext-0",
        title="Private Equity Analyst",
        company="FundCo",
        country="gb",
        remote_type="remote",
        description_text="Work on due diligence, valuation and LBO modeling.",
        embedding_vector=vec,
    )
    # Job 1 mismatches industry + country + remote
    job1 = JobPosting(
        source="adzuna",
        external_id="ext-1",
        title="Software Engineer",
        company="TechCo",
        country="us",
        remote_type="onsite",
        description_text="Build backend services in Python.",
        embedding_vector=vec,
    )
    db_session.add_all([job0, job1])
    db_session.commit()

    with patch.dict(sys.modules, {"app.services.skill_extraction": _mock_skill_module}), \
         patch("app.services.job_recommendation_service.embed_text") as mock_embed:
        mock_embed.return_value = [0.85] * 384
        results = recommend_jobs(db_session, user_id=user_id, limit=5)
    assert len(results) == 2
    assert results[0]["score"] >= results[1]["score"]
    assert results[0]["job_id"] == job0.id
    assert "score" in results[0]
    assert "matched_skills" in results[0]
    assert "missing_skills" in results[0]
    assert "penalties_applied" in results[0]


def test_recommendation_respects_industry_preference(db_session):
    """Industry preference should boost finance/PE jobs over unrelated software roles."""
    user = User(
        email="pe@test.com",
        password_hash="hash",
        primary_role_preference="Analyst",
        primary_industry_preference="Finance / Private Equity",
        remote_preference="any",
    )
    db_session.add(user)
    db_session.commit()

    # Same embedding vectors so ranking depends on preference logic.
    vec = [0.5] * 384
    pe_job = JobPosting(
        source="adzuna",
        external_id="pe-1",
        title="Private Equity Analyst",
        company="FundCo",
        description_text="Support due diligence, valuation, and LBO modeling for buyout transactions.",
        embedding_vector=vec,
    )
    swe_job = JobPosting(
        source="adzuna",
        external_id="swe-1",
        title="Software Engineer",
        company="TechCo",
        description_text="Build backend services in Python and deploy to AWS.",
        embedding_vector=vec,
    )
    db_session.add_all([pe_job, swe_job])
    db_session.commit()

    with patch.dict(sys.modules, {"app.services.skill_extraction": _mock_skill_module}), \
         patch("app.services.job_recommendation_service.embed_text") as mock_embed:
        mock_embed.return_value = [0.5] * 384
        results = recommend_jobs(db_session, user_id=user.id, limit=2)

    assert len(results) == 2
    assert results[0]["job_id"] == pe_job.id
    assert any("industry" in p.lower() for p in results[0]["penalties_applied"])


def test_country_preference_uk_matches_gb_code(db_session):
    """User selecting 'UK' should match jobs ingested with country='GB'."""
    user = User(
        email="uk@test.com",
        password_hash="hash",
        primary_industry_preference="Finance",
        desired_countries=["UK"],
        remote_preference="any",
    )
    db_session.add(user)
    db_session.commit()

    vec = [0.5] * 384
    gb_job = JobPosting(
        source="adzuna",
        external_id="gb-1",
        title="Finance Analyst",
        company="BankCo",
        country="GB",
        location_display="London, UK",
        remote_type="onsite",
        description_text="Finance role in London.",
        embedding_vector=vec,
    )
    ie_job = JobPosting(
        source="adzuna",
        external_id="ie-1",
        title="Finance Analyst",
        company="BankCo",
        country="IE",
        location_display="Dublin, Ireland",
        remote_type="onsite",
        description_text="Finance role in Dublin.",
        embedding_vector=vec,
    )
    db_session.add_all([ie_job, gb_job])
    db_session.commit()

    with patch.dict(sys.modules, {"app.services.skill_extraction": _mock_skill_module}), \
         patch("app.services.job_recommendation_service.embed_text") as mock_embed:
        mock_embed.return_value = [0.5] * 384
        results = recommend_jobs(db_session, user_id=user.id, limit=2)

    assert results[0]["job_id"] == gb_job.id


def test_finance_preference_downranks_software_titles(db_session):
    """If industry is finance but role isn't software, software titles should be downranked."""
    user = User(
        email="finance@test.com",
        password_hash="hash",
        primary_industry_preference="Financial Services",
        primary_role_preference="Other roles",
        desired_countries=["United Kingdom"],
        remote_preference="On-site",
    )
    db_session.add(user)
    db_session.commit()

    vec = [0.5] * 384
    finance_analyst = JobPosting(
        source="adzuna",
        external_id="fa-1",
        title="Finance Data Analyst",
        company="BankCo",
        country="GB",
        location_display="London, UK",
        remote_type="onsite",
        description_text="Work with finance and treasury stakeholders.",
        embedding_vector=vec,
    )
    software_at_bank = JobPosting(
        source="adzuna",
        external_id="se-1",
        title="Senior Software Engineer",
        company="BankCo",
        country="GB",
        location_display="London, UK",
        remote_type="onsite",
        description_text="Build trading systems for financial services.",
        embedding_vector=vec,
    )
    db_session.add_all([software_at_bank, finance_analyst])
    db_session.commit()

    with patch.dict(sys.modules, {"app.services.skill_extraction": _mock_skill_module}), \
         patch("app.services.job_recommendation_service.embed_text") as mock_embed:
        mock_embed.return_value = [0.5] * 384
        results = recommend_jobs(db_session, user_id=user.id, limit=2)

    assert results[0]["job_id"] == finance_analyst.id
