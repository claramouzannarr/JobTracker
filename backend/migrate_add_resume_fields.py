"""
Migration script to add parsed_sections and overall_score columns to resume_versions table
Run this with: python migrate_add_resume_fields.py
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.config import settings

def migrate():
    engine = create_engine(settings.database_url)
    
    with engine.begin() as conn:  # Use begin() for auto-commit
        # Check if columns exist, if not add them
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
            
            print("✅ Migration successful: Added parsed_sections and overall_score columns")
        except Exception as e:
            print(f"❌ Migration error: {e}")
            raise

if __name__ == "__main__":
    migrate()
