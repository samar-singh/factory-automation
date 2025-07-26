"""Application configuration settings."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # OpenAI Configuration
    openai_api_key: str
    
    # Gmail API Configuration
    gmail_client_id: Optional[str] = None
    gmail_client_secret: Optional[str] = None
    gmail_redirect_uri: str = "http://localhost:8080"
    gmail_token_file: str = "token.json"
    
    # Database Configuration
    database_url: str = "postgresql://factory_user:password@localhost:5432/factory_automation"
    redis_url: str = "redis://localhost:6379"
    
    # ChromaDB Configuration
    chroma_persist_directory: str = "./chroma_data"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    
    # Application Settings
    app_env: str = "development"
    app_port: int = 8001
    gradio_port: int = 7860
    
    # Email Polling Settings
    email_poll_interval: int = 300  # 5 minutes
    email_folder: str = "INBOX"
    
    # Together AI (for vision models)
    together_api_key: Optional[str] = None
    
    # Security
    secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Create global settings instance
settings = Settings()