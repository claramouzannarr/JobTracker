from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Fail fast if DB is unreachable (e.g. PostgreSQL not running)
_connect_args = {}
if settings.database_url.startswith("postgresql"):
    _connect_args["connect_timeout"] = 10
engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_resume_versions_table():
    """Add missing columns to resume_versions table if they don't exist"""
    with engine.begin() as conn:
        try:
            # Add parsed_sections column if it doesn't exist
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='resume_versions' AND column_name='parsed_sections'
                    ) THEN
                        ALTER TABLE resume_versions ADD COLUMN parsed_sections JSON;
                    END IF;
                END $$;
            """))
            
            # Add overall_score column if it doesn't exist
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='resume_versions' AND column_name='overall_score'
                    ) THEN
                        ALTER TABLE resume_versions ADD COLUMN overall_score FLOAT;
                    END IF;
                END $$;
            """))
            print("✅ Database migration: Added parsed_sections and overall_score columns")
        except Exception as e:
            print(f"⚠️  Migration note: {e}")
            # Don't raise - columns might already exist


def migrate_interview_prep_tables():
    """Add generated_json to interview_prep and create interview_answers table if needed. PostgreSQL only."""
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        try:
            # Add generated_json to interview_prep if missing
            conn.execute(text("""
                DO $$ BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'interview_prep' AND column_name = 'generated_json'
                    ) THEN
                        ALTER TABLE interview_prep ADD COLUMN generated_json JSON;
                    END IF;
                END $$;
            """))
            # Create interview_answers if not exists (SQLAlchemy create_all will add it; this handles existing DBs)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS interview_answers (
                    id SERIAL PRIMARY KEY,
                    interview_prep_id INTEGER NOT NULL REFERENCES interview_prep(id) ON DELETE CASCADE,
                    question_id VARCHAR(64) NOT NULL,
                    answer_text TEXT,
                    transcript_text TEXT,
                    score INTEGER,
                    feedback_json JSON,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))
            print("✅ Database migration: interview_prep.generated_json and interview_answers checked")
        except Exception as e:
            print(f"⚠️  Migration interview_prep: {e}")


def migrate_job_postings_table():
    """Add Adzuna/recommendation columns to job_postings if they don't exist. PostgreSQL only."""
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        try:
            def add_col_if_not_exists(col_name: str, col_def: str):
                conn.execute(text(f"""
                    DO $$ BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'job_postings' AND column_name = '{col_name}'
                        ) THEN
                            ALTER TABLE job_postings ADD COLUMN {col_name} {col_def};
                        END IF;
                    END $$;
                """))
            add_col_if_not_exists("external_id", "VARCHAR(255)")
            add_col_if_not_exists("location_display", "TEXT")
            add_col_if_not_exists("contract_type", "VARCHAR(100)")
            add_col_if_not_exists("salary_min", "DOUBLE PRECISION")
            add_col_if_not_exists("salary_max", "DOUBLE PRECISION")
            add_col_if_not_exists("latitude", "DOUBLE PRECISION")
            add_col_if_not_exists("longitude", "DOUBLE PRECISION")
            add_col_if_not_exists("remote_type", "VARCHAR(50)")
            add_col_if_not_exists("description_hash", "VARCHAR(64)")
            add_col_if_not_exists("is_active", "BOOLEAN DEFAULT TRUE")
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'uq_job_posting_source_external_id'
                    ) AND EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'job_postings' AND column_name = 'external_id'
                    ) THEN
                        ALTER TABLE job_postings ADD CONSTRAINT uq_job_posting_source_external_id
                        UNIQUE (source, external_id);
                    END IF;
                EXCEPTION WHEN OTHERS THEN NULL;
                END $$;
            """))
            print("✅ Database migration: job_postings columns/constraint checked")
        except Exception as e:
            print(f"⚠️  Migration job_postings: {e}")


def migrate_users_table():
    """Add missing columns to users table if they don't exist. PostgreSQL only."""
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        try:
            def add_col_if_not_exists(col_name: str, col_def: str):
                conn.execute(text(f"""
                    DO $$ BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'users' AND column_name = '{col_name}'
                        ) THEN
                            ALTER TABLE users ADD COLUMN {col_name} {col_def};
                        END IF;
                    END $$;
                """))

            add_col_if_not_exists("industry_preferences", "JSON")
            print("✅ Database migration: users.industry_preferences checked")
        except Exception as e:
            print(f"⚠️  Migration users: {e}")

