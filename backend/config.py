"""
Configuration module for the Agent.
Centralizes all configuration in one place.
"""

from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings  # type: ignore[no-redef]  # pydantic v1 fallback


class Settings(BaseSettings):
    """Application settings."""
    
    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False
    
    # LLM Configuration
    LLM_BASE_URL: str = "http://localhost:1234/v1"
    LLM_MODEL: str = "mistral-7b-instruct"
    LLM_TIMEOUT: int = 60
    LLM_TEMPERATURE: float = 0.7
    
    # Browser Configuration
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT_MS: int = 30000
    BROWSER_AUTO_RETRY: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    
    # Session
    SESSION_TIMEOUT_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
