from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Smart Wardrobe Outfit System"
    app_version: str = "0.1.0"
    debug: bool = Field(default=True, validation_alias="DEBUG")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")

    # Server Configuration (for kiosk to connect)
    api_server_ip: str = Field(default="http://localhost:8000", validation_alias="API_SERVER_IP")

    # Database
    database_url: str = Field(
        default="sqlite:///data/db/smart_wardrobe.db", validation_alias="DATABASE_URL"
    )

    # File Storage - Dual path structure for raw and processed images
    images_raw_dir: str = Field(default="data/images/raw", validation_alias="IMAGES_RAW_DIR")
    images_processed_dir: str = Field(
        default="data/images/processed", validation_alias="IMAGES_PROCESSED_DIR"
    )
    images_processed_garments_dir: str = Field(
        default="data/images/processed/garments", validation_alias="IMAGES_PROCESSED_GARMENTS_DIR"
    )
    images_processed_outfits_dir: str = Field(
        default="data/images/processed/outfits", validation_alias="IMAGES_PROCESSED_OUTFITS_DIR"
    )
    models_cache_dir: str = Field(default="data/models_cache", validation_alias="MODELS_CACHE_DIR")

    # AI Providers
    ai_provider: str = Field(default="local", validation_alias="AI_PROVIDER")  # "local" or "nim"

    # NVIDIA NIM
    nim_api_url: str = Field(
        default="https://integrate.api.nvidia.com/v1", validation_alias="NIM_API_URL"
    )
    nim_api_key: str = Field(default="", validation_alias="NIM_API_KEY")
    nim_model: str = Field(
        default="nvidia/llama-3.1-nemotron-3-ultra", validation_alias="NIM_MODEL"
    )

    # Vision Models
    sam_model_type: str = Field(default="vit_h", validation_alias="SAM_MODEL_TYPE")
    sam_checkpoint_url: str = Field(
        default="https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
        validation_alias="SAM_CHECKPOINT_URL",
    )
    clip_model: str = Field(default="ViT-B-32", validation_alias="CLIP_MODEL")
    clip_pretrained: str = Field(default="openai", validation_alias="CLIP_PRETRAINED")
    clip_model_name: str = Field(default="ViT-B/32", validation_alias="CLIP_MODEL_NAME")

    # Device
    device: str = Field(default="cuda", validation_alias="DEVICE")

    # Frontend
    frontend_dir: str = Field(default="frontend", validation_alias="FRONTEND_DIR")

    # CORS - Allow all origins for local network access
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8000", "http://localhost:3000", "http://localhost:8080", "*"],
        validation_alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            v = v.strip()
            if not v:
                return ["*"]
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return [parsed]
            except json.JSONDecodeError:
                return [item.strip() for item in v.split(",") if item.strip()]
        return v

    # Optional: Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_file: str = Field(default="/app/data/logs/app.log", validation_alias="LOG_FILE")

    # Optional: Backup
    backup_enabled: bool = Field(default=True, validation_alias="BACKUP_ENABLED")
    backup_retention_days: int = Field(default=7, validation_alias="BACKUP_RETENTION_DAYS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
