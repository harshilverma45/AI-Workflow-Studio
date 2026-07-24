from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    project_name: str = Field(default="LoopEngineeringStudio", validation_alias="LANGCHAIN_PROJECT")
    database_url: str = Field(default="sqlite:///./loop.db", validation_alias="DATABASE_URL")
    model_provider: str = Field(default="local", validation_alias="MODEL_PROVIDER")
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.6-flash", validation_alias="GEMINI_MODEL")
    max_iterations: int = Field(default=2, validation_alias="MAX_ITERATIONS")
    quality_threshold: float = Field(default=0.85, validation_alias="QUALITY_THRESHOLD")

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
