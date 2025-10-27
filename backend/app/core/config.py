"""
Configuration settings for AI Bug Analyzer Backend
================================================

This module contains all configuration settings for the FastAPI backend.
Settings are loaded from environment variables with sensible defaults.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application settings
    app_name: str = "AI Bug Analyzer"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API settings
    api_v1_prefix: str = "/api/v1"
    host: str = "localhost"
    port: int = 8000
    
    # Database settings
    database_url: str = "sqlite:///./ai_bug_analyzer.db"
    
    # Azure DevOps settings (no hardcoding - must be provided)
    ado_org_url: Optional[str] = None
    ado_project: Optional[str] = None
    ado_pat: Optional[str] = None
    
    # MCP Server settings
    mcp_server_name: str = "ado-bug-analyzer"
    
    # AI settings
    ai_similarity_threshold: float = 0.85
    ai_model_name: str = "all-MiniLM-L6-v2"  # Sentence transformer model
    max_similarity_results: int = 10
    
    # Thomson Reuters OpenArena Internal AI Configuration
    use_internal_ai: bool = False
    esso_token: Optional[str] = None
    open_arena_base_url: Optional[str] = None
    open_arena_workflow_id: Optional[str] = None
    ai_service_timeout: int = 30
    ai_max_retries: int = 3
    
    # Cache settings
    cache_timeout: int = 300  # 5 minutes
    
    # CORS settings
    allowed_origins: list = [
        "http://localhost:3000",  # React dev server
        "http://localhost:8080",  # Alternative frontend port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "file://",  # Local file serving for development
        "*"  # Allow all origins for development (restrict in production)
    ]
    
    # Security settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings"""
    return settings
