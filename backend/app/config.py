import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FormaX AI Backend"
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # Validation constraints matching Member 1 frontend
    MAX_SOURCE_CHARS: int = 50000
    MIN_SOURCE_CHARS: int = 1
    
    # Model configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEFAULT_MODEL: str = os.getenv("MODEL_NAME", "gemini-2.5-flash")
    
    # Security thresholds
    PROMPT_INJECTION_BLOCK_THRESHOLD: float = 0.8
    PROMPT_INJECTION_REVIEW_THRESHOLD: float = 0.4
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
