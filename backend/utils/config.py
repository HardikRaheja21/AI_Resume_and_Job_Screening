import os
from pathlib import Path
# from pydantic import BaseSettings
from pydantic_settings import BaseSettings

from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./resumes.db"
    JWT_SECRET_KEY: str = "please_change_me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""

    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    SELECTION_THRESHOLD: float = 0.3

    # frontend during dev
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = str(ENV_PATH)
        env_file_encoding = "utf-8"

settings = Settings()
