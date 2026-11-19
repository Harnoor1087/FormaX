import os
from pathlib import Path
from typing import List
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FormaX AI Backend"
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    
    # Validation constraints matching Member 1 frontend
    MAX_SOURCE_CHARS: int = 50000
    MIN_SOURCE_CHARS: int = 1
    
    # Model configuration
    # Using gemini-3.1-flash-lite for stability and availability
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEFAULT_MODEL: str = Field(
        default="gemini-3.1-flash-lite",
        validation_alias="MODEL_NAME",
    )
    
    # Security thresholds
    PROMPT_INJECTION_BLOCK_THRESHOLD: float = 0.8
    PROMPT_INJECTION_REVIEW_THRESHOLD: float = 0.4
    
    # Rate Limiting & Denial-of-Wallet settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 30
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Data Protection & Sensitive Information settings
    ENABLE_PII_REDACTION: bool = True
    AUDIT_LOG_FILE: str = "logs/security_audit.jsonl"
    DATABASE_PATH: str = Field(
        default=str(Path(__file__).resolve().parents[1] / "data" / "formax.sqlite3"),
        validation_alias="FORMAX_DATABASE_PATH",
    )
    VIDEO_OUTPUT_DIR: str = Field(
        default=str(Path(__file__).resolve().parents[1] / "data" / "videos"),
        validation_alias="FORMAX_VIDEO_DIR",
    )
    OPERATOR_API_TOKEN: str = ""
    REVIEWER_API_TOKEN: str = ""
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_api_tokens(self):
        tokens = {
            "OPERATOR_API_TOKEN": self.OPERATOR_API_TOKEN,
            "REVIEWER_API_TOKEN": self.REVIEWER_API_TOKEN,
        }
        configured_tokens = [token for token in tokens.values() if token]
        if len(configured_tokens) != len(set(configured_tokens)):
            raise ValueError("OPERATOR_API_TOKEN and REVIEWER_API_TOKEN must be different.")
        for name, token in tokens.items():
            if token and len(token) < 32:
                raise ValueError(f"{name} must contain at least 32 characters.")
        return self

settings = Settings()
