"""Tests for job ingestion (Adzuna upsert and dedupe)."""
import pytest
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import JobPosting
from app.services.job_ingestion_service import ingest_adzuna_jobs, SOURCE_ADZUNA


@pytest.fixture
def db_session():
    """In-memory SQLite session for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_ingestion_upsert_dedupes_by_source_external_id(db_session):
    """Ingestion upserts by (source, external_id); second run with same data updates/skips."""
    mock_response = {
        "results": [
            {
                "id": "123",
                "title": "Software Engineer",
                "company": {"display_name": "Acme"},
                "description": "Python and AWS.",
                "location": {"display_name": "London"},
                "redirect_url": "https://example.com/job/123",
                "contract_type": "permanent",
                "salary_min": 50000,
                "salary_max": 60000,
                "created": "2024-01-15T10:00:00Z",
            }
        ]
    }
    with patch("app.services.job_ingestion_service.AdzunaClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.search_jobs.return_value = mock_response
        MockClient.return_value = mock_instance
        with patch("app.services.job_ingestion_service.embed_text") as mock_embed:
            mock_embed.return_value = [0.1] * 384
            counts1 = ingest_adzuna_jobs(
                db_session, "gb", what="engineer", pages=1, app_id="id", app_key="key"
            )
    assert counts1["fetched"] == 1
    assert counts1["inserted"] == 1
    assert db_session.query(JobPosting).filter(
        JobPosting.source == SOURCE_ADZUNA, JobPosting.external_id == "123"
    ).count() == 1

    # Same response again: should skip (no change) or update
    with patch("app.services.job_ingestion_service.AdzunaClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.search_jobs.return_value = mock_response
        MockClient.return_value = mock_instance
        with patch("app.services.job_ingestion_service.embed_text"):
            counts2 = ingest_adzuna_jobs(
                db_session, "gb", what="engineer", pages=1, app_id="id", app_key="key"
            )
    # Either skipped (no change) or updated; only one row
    assert db_session.query(JobPosting).filter(
        JobPosting.source == SOURCE_ADZUNA, JobPosting.external_id == "123"
    ).count() == 1
    assert counts2["fetched"] == 1
    assert counts2["inserted"] == 0
