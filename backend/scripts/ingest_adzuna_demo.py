#!/usr/bin/env python3
"""
Capstone demo: Ingest Adzuna jobs for ES and GB (data analyst, software engineer, 2 pages each).
Requires BACKEND_URL and INGEST_ADMIN_TOKEN env vars if calling the API.
Alternatively set ADZUNA_APP_ID and ADZUNA_APP_KEY to run ingestion directly against the DB.
"""
import os
import sys

# Add backend to path so app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def run_via_api():
    import urllib.request
    import json
    base_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    token = os.getenv("INGEST_ADMIN_TOKEN", "")
    if not token:
        print("Set INGEST_ADMIN_TOKEN to use the API ingest endpoint.")
        return False
    req = urllib.request.Request(
        f"{base_url}/api/jobs/ingest/adzuna/demo",
        data=b"",
        method="POST",
        headers={"Content-Type": "application/json", "X-Admin-Token": token},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    print("Demo ingest result:", json.dumps(data, indent=2))
    return True


def run_direct():
    from app.database import SessionLocal
    from app.config import settings
    from app.services.job_ingestion_service import ingest_adzuna_jobs

    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        print("Set ADZUNA_APP_ID and ADZUNA_APP_KEY in .env to run direct ingestion.")
        return False
    db = SessionLocal()
    try:
        total = {"fetched": 0, "inserted": 0, "updated": 0, "skipped": 0}
        for country in ("es", "gb"):
            for what in ("data analyst", "software engineer"):
                counts = ingest_adzuna_jobs(
                    db, country=country, what=what, where=None, pages=2, results_per_page=50,
                    app_id=settings.adzuna_app_id,
                    app_key=settings.adzuna_app_key,
                    base_url=settings.adzuna_base_url,
                )
                print(f"  {country} / {what}: fetched={counts['fetched']} inserted={counts['inserted']} updated={counts['updated']} skipped={counts['skipped']}")
                for k in total:
                    total[k] += counts[k]
        print("Total:", total)
    finally:
        db.close()
    return True


if __name__ == "__main__":
    if os.getenv("INGEST_ADMIN_TOKEN") and os.getenv("BACKEND_URL"):
        ok = run_via_api()
    else:
        ok = run_direct()
    sys.exit(0 if ok else 1)
