"""
Configuration module for CampusConnect AI Service.

Loads environment variables and provides configuration singletons.
Uses pydantic for validation.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Config(BaseSettings):
    """
    Application configuration loaded from environment variables.
    
    All values come from .env file or system environment.
    Type hints provide validation (pydantic converts types automatically).
    """
    
    # ============================================================
    # FIREBASE CONFIGURATION (REQUIRED)
    # ============================================================
    FIREBASE_PROJECT_ID: str
    """Firebase project ID. Find in Firebase Console → Project Settings."""
    
    GOOGLE_APPLICATION_CREDENTIALS: str = "/config/serviceAccountKey.json"
    """Path to Firebase service account JSON file."""
    
    # ============================================================
    # LLM CONFIGURATION (PERPLEXITY PRIMARY, OPENAI FALLBACK)
    # ============================================================
    PERPLEXITY_API_KEY: Optional[str] = None
    """Perplexity API key for Sonar LLM. Get from https://perplexity.ai/settings/api"""
    
    PERPLEXITY_MODEL: str = "sonar"
    """Perplexity model. Use 'sonar' (default) or 'sonar-pro'. See https://docs.perplexity.ai/docs/getting-started/models"""
    
    OPENAI_API_KEY: Optional[str] = None
    """OpenAI API key (fallback if Perplexity not available). Get from https://platform.openai.com/api-keys"""
    
    OPENAI_MODEL: Optional[str] = "gpt-3.5-turbo"
    """OpenAI model to use. gpt-3.5-turbo = cheapest, gpt-4 = best quality."""
    
    # ============================================================
    # LANGSMITH CONFIGURATION (OPTIONAL - FOR DEBUGGING)
    # ============================================================
    LANGSMITH_API_KEY: Optional[str] = None
    """LangSmith API key for tracing graphs. Leave empty if not using."""
    
    LANGSMITH_ENABLED: bool = False
    """Enable LangSmith tracing. Set to True only if LANGSMITH_API_KEY is set."""
    
    # ============================================================
    # GRAPH CONFIGURATION
    # ============================================================
    GRAPH_TIMEOUT: int = 30
    """Maximum seconds a graph can run before timeout. Default: 30 seconds."""
    
    MAX_CANDIDATES: int = 100
    """Maximum candidates to fetch from Firestore per query. Default: 100."""

    # ============================================================
    # SECURITY CONFIGURATION
    # ============================================================
    AI_SERVICE_TOKEN: str = os.getenv("AI_SERVICE_TOKEN", "")
    """Shared secret for authenticating requests from the JS backend."""
    
    # ============================================================
    # BACKEND API (FOR CHAT TOOLS)
    # ============================================================
    BACKEND_API_URL: str = os.getenv("BACKEND_API_URL", "http://localhost:5001")
    """CampusConnect backend API base URL. Used by chat tools to call REST endpoints."""

    # ============================================================
    # SERVER CONFIGURATION
    # ============================================================
    PORT: int = 8000
    """Port to run FastAPI server on. Default: 8000."""
    
    HOST: str = "0.0.0.0"
    """Host to bind to. 0.0.0.0 = accessible from network."""
    
    DEBUG: bool = False
    """Enable debug logging. Set True for development, False for production."""
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"  # Read from .env file
        case_sensitive = True  # Variable names are case-sensitive
        extra = "ignore"  # Ignore extra env vars not defined above


# ============================================================
# SINGLETON INSTANCE
# ============================================================
# Load config once at startup, reuse throughout app
config = Config()


# ============================================================
# VALIDATION AT STARTUP
# ============================================================
def validate_config() -> dict:
    """
    Validate that required config values are set.
    
    Called at app startup to fail fast if config is incomplete.
    
    Returns:
        dict: Status of each required field
        
    Raises:
        ValueError: If required config is missing
    """
    errors = []
    
    # Firebase is always required
    if not config.FIREBASE_PROJECT_ID:
        errors.append("FIREBASE_PROJECT_ID is required")
    
    # At least one LLM must be configured
    if not config.PERPLEXITY_API_KEY and not config.OPENAI_API_KEY:
        errors.append("Either PERPLEXITY_API_KEY or OPENAI_API_KEY must be set")
    
    # If LangSmith enabled, must have API key
    if config.LANGSMITH_ENABLED and not config.LANGSMITH_API_KEY:
        errors.append("LANGSMITH_ENABLED=True but LANGSMITH_API_KEY not set")
    
    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join([f"  - {e}" for e in errors]))
    
    return {
        "firebase": "✓ Configured" if config.FIREBASE_PROJECT_ID else "✗ Missing",
        "perplexity": "✓ Configured" if config.PERPLEXITY_API_KEY else "✗ Not set",
        "openai": "✓ Configured" if config.OPENAI_API_KEY else "✗ Not set",
        "langsmith": "✓ Configured" if config.LANGSMITH_ENABLED else "✗ Disabled",
    }


if __name__ == "__main__":
    """Allow testing config by running: python -m src.config"""
    try:
        status = validate_config()
        print("✅ Configuration is valid!")
        print("\nConfiguration Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
    except ValueError as e:
        print(f"❌ Configuration error:\n{e}")
        exit(1)
