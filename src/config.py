import os
from datetime import date
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    CORPUS_DIR: str = os.getenv("CORPUS_DIR", "./data/corpus")
    MANIFEST_PATH: str = os.getenv("MANIFEST_PATH", "./data/manifest.json")
    DB_PATH: str = os.getenv("DB_PATH", "./data/veltrix.db")
    APP_TODAY: str = os.getenv("APP_TODAY", "2026-09-15")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    def get_today(self) -> str:
        if self.APP_TODAY:
            return self.APP_TODAY
        return date.today().isoformat()

settings = Settings()
