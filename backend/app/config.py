from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/jobtracker")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-" + "x" * 32)
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

