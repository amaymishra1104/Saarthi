import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "SAARTHI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'saarthi.db'}")
    
    # Payments Core Integration
    PAYMENTS_API_KEY: str = os.getenv("PAYMENTS_API_KEY", "saarthi-mock-bank-key-secret-2026")
    AUTO_ACTION_LIMIT: float = float(os.getenv("AUTO_ACTION_LIMIT", "5000.00"))
    
    # LLM Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    MOCK_LLM: bool = os.getenv("MOCK_LLM", "true").lower() in ("true", "1", "yes")
    
    # Policy RAG
    POLICY_DIR: Path = BASE_DIR / "data" / "policies"
    
    # Chaos Switch flags (default disabled)
    CHAOS_LOOKUP_FAIL: bool = False
    CHAOS_TIMEOUT: bool = False
    CHAOS_AMBIGUOUS_STATUS: bool = False
    CHAOS_DUPLICATE_ATTEMPT: bool = False
    CHAOS_VERIFICATION_MISMATCH: bool = False

settings = Settings()
