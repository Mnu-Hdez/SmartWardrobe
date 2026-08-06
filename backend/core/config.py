# Smart Wardrobe - Core Configuration
# Pydantic Settings for environment-based config

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    API_SERVER_IP: str = "0.0.0.0"
    API_PORT: int = 7000

    # Device & Models
    DEVICE: str = "cpu"
    SAM_MODEL_TYPE: str = "vit_b"
    CLIP_MODEL: str = "ViT-B-32"
    CLIP_PRETRAINED: str = "openai"

    # Storage (dual paths)
    IMAGES_RAW_DIR: Path = Path("/app/data/images/raw")
    IMAGES_PROCESSED_GARMENTS_DIR: Path = Path("/app/data/images/processed/garments")
    MODELS_CACHE_DIR: Path = Path("/app/data/models_cache")

    # Database
    DATABASE_URL: str = "sqlite:////app/data/db/smart_wardrobe.db"

    # CORS
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])

    # AI Provider
    AI_PROVIDER: str = "local"
    NIM_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()

# Note: Directory creation is handled lazily by the application startup
# to avoid issues in test environments


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
