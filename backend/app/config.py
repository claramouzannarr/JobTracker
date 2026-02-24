from pydantic_settings import BaseSettings
import os

# Backend port (frontend proxy must match). Default 8000.
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/jobtracker")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-" + "x" * 32)
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # Adzuna job source
    adzuna_app_id: str = os.getenv("ADZUNA_APP_ID", "")
    adzuna_app_key: str = os.getenv("ADZUNA_APP_KEY", "")
    adzuna_base_url: str = os.getenv("ADZUNA_BASE_URL", "https://api.adzuna.com/v1/api")

    # Optional: protect ingest endpoint (admin token)
    ingest_admin_token: str = os.getenv("INGEST_ADMIN_TOKEN", "")

    # OpenAI (interview prep: generation, evaluation, optional RAG)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model_generate: str = os.getenv("OPENAI_MODEL_GENERATE", "gpt-4o-mini")
    openai_model_eval: str = os.getenv("OPENAI_MODEL_EVAL", "gpt-4o-mini")
    openai_embed_model: str = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    openai_vector_store_id: str = os.getenv("OPENAI_VECTOR_STORE_ID", "")  # Optional: managed retrieval

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

