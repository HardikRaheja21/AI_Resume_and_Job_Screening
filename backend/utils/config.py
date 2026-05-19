from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./resumes.db"
    JWT_SECRET_KEY: str = "please_change_me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    LOG_FILE: str = "app.log"
    AUTO_DB_BOOTSTRAP: bool = False
    MAX_UPLOAD_FILE_SIZE_MB: int = 10
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300
    WEBHOOK_TIMEOUT_SECONDS: float = 8.0
    WEBHOOK_RETRY_ATTEMPTS: int = 3
    WEBHOOK_RETRY_BACKOFF_SECONDS: float = 0.8
    EMAIL_RETRY_ATTEMPTS: int = 3
    EMAIL_RETRY_BACKOFF_SECONDS: float = 1.0
    DEAD_LETTER_DIR: str = "./dead_letters"
    SLACK_WEBHOOK_URL: str = ""
    TEAMS_WEBHOOK_URL: str = ""
    ATS_SYNC_URL: str = ""
    ATS_SYNC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_SECONDS: float = 15.0
    MATCHER_DISABLE_EMBEDDINGS: bool = False
    MATCHER_REQUIRED_SKILL_WEIGHT: float = 0.45
    MATCHER_OPTIONAL_SKILL_WEIGHT: float = 0.15
    MATCHER_SEMANTIC_WEIGHT: float = 0.25
    MATCHER_EXPERIENCE_WEIGHT: float = 0.15
    VECTOR_DB_DIR: str = "./vector_store"
    VECTOR_COLLECTION_NAME: str = "resume_vectors"
    VECTOR_CHROMA_IMPL: str = "duckdb+parquet"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    CELERY_TASK_ALWAYS_EAGER: bool = False
    PROCESSING_JOB_MAX_RETRIES: int = 3
    PROCESSING_JOB_RETRY_BACKOFF_SECONDS: int = 30
    AI_TASK_TIME_LIMIT_SECONDS: int = 300
    OCR_TASK_TIME_LIMIT_SECONDS: int = 600
    EMBEDDING_TASK_TIME_LIMIT_SECONDS: int = 300
    BULK_UPLOAD_MAX_FILES: int = 50
    PROCESSING_EVENT_REDIS_ENABLED: bool = True
    PROCESSING_EVENT_CHANNEL_PREFIX: str = "ats:processing"
    PROCESSING_STREAM_HEARTBEAT_SECONDS: int = 15
    EMBEDDING_CACHE_ENABLE: bool = True
    EMBEDDING_CACHE_MODEL_NAME: str = "all-MiniLM-L6-v2"
    AI_PROMPT_VERSION: str = "candidate-summary-v1"
    MATCH_EXPLANATION_VERSION: str = "match-explain-v1"
    WORKFLOW_ORCHESTRATION_MODE: str = "parallel"
    WORKFLOW_SLA_SECONDS: int = 300
    VECTOR_SCHEMA_VERSION: str = "resume-vector-v1"
    OTEL_ENABLE: bool = False
    OTEL_SERVICE_NAME: str = "resume-parser-api"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    QUEUE_GOVERNANCE_ENABLE: bool = True
    QUEUE_MAX_DEPTH_DEFAULT: int = 1000
    QUEUE_OVERLOAD_REJECT: bool = False
    TENANT_QUEUE_ISOLATION_ENABLE: bool = False
    AI_INPUT_TOKEN_COST_PER_1K: float = 0.0
    AI_OUTPUT_TOKEN_COST_PER_1K: float = 0.0
    ADAPTIVE_RUNTIME_ENABLE: bool = True
    DEFAULT_WORKFLOW_NAME: str = "resume_intelligence"
    DEFAULT_WORKFLOW_VERSION: str = "resume-dag-v1"
    POLICY_ENGINE_ENABLE: bool = True
    MAX_HALLUCINATION_RISK_SCORE: float = 0.35
    MIN_EVIDENCE_SUFFICIENCY_SCORE: float = 0.65
    TENANT_FAIRNESS_ENABLE: bool = True
    PREDICTIVE_RUNTIME_ENABLE: bool = True
    PREDICTION_HORIZON_SECONDS: int = 300
    SLA_BREACH_RISK_THRESHOLD: float = 0.7
    QUEUE_CONGESTION_RISK_THRESHOLD: float = 0.75
    CHAOS_EXPERIMENTS_ENABLE: bool = False
    SIMULATION_DEFAULT_WORKLOAD_SIZE: int = 100
    AUTONOMOUS_RUNTIME_ENABLE: bool = False
    AUTONOMOUS_ACTION_MIN_CONFIDENCE: float = 0.8
    AUTONOMOUS_REQUIRE_GUARDRAILS: bool = True
    MAX_AUTONOMOUS_CONCURRENCY_DELTA: int = 2
    WORKER_QUARANTINE_FAILURE_RATE_THRESHOLD: float = 0.5
    STRATEGY_LEARNING_RATE: float = 0.15
    MULTI_AGENT_RUNTIME_ENABLE: bool = True
    AGENT_CONSENSUS_MIN_SCORE: float = 0.66
    SAFETY_VERIFICATION_MAX_RISK: float = 0.35
    EXPERIMENT_DEFAULT_TRAFFIC_PERCENT: float = 10.0

    NLP_ENABLE: bool = True
    NLP_MODEL_NAME: str = "en_core_web_sm"

    OCR_ENABLE: bool = True
    OCR_TESSERACT_CMD: Optional[str] = None
    OCR_LANG: str = "eng"
    OCR_DPI: int = 300
    OCR_PAGE_LIMIT: int = 10
    OCR_IMAGE_PREPROCESS: bool = True
    OCR_TESSERACT_CONFIG: str = "--psm 3 --oem 1"

    # Preferred SMTP/email configuration
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_HOST_USER: str = ""
    EMAIL_HOST_PASSWORD: str = ""
    EMAIL_USE_TLS: bool = True
    EMAIL_FROM: str = ""

    # Backward-compatible aliases (optional legacy env names)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 0
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""

    UPLOAD_DIR: str = "./uploads"
    CORS_ORIGINS: List[str] = []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def smtp_host(self) -> str:
        return self.EMAIL_HOST or self.SMTP_HOST

    @property
    def smtp_port(self) -> int:
        return self.EMAIL_PORT or self.SMTP_PORT or 587

    @property
    def smtp_user(self) -> str:
        return self.EMAIL_HOST_USER or self.SMTP_USERNAME

    @property
    def smtp_password(self) -> str:
        return self.EMAIL_HOST_PASSWORD or self.SMTP_PASSWORD

settings = Settings()
