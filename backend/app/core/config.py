from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    project_name: str = "LoopEngineeringStudio"
    database_url: str = "sqlite:///./loop.db"


settings = Settings()
