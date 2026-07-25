import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # App
    app_name: str = "Smart Wardrobe Outfit System"
    app_version: str = "0.1.0"
    debug: bool = Field(default=True, validation_alias="DEBUG")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    
    # Database
    database_url: str = Field(
        default="sqlite:///data/db/smart_wardrobe.db",
        validation_alias="DATABASE_URL"
    )
    
    # File Storage
    images_original_dir: str = Field(
        default="data/images/original",
        validation_alias="IMAGES_ORIGINAL_DIR"
    )
    images_processed_garments_dir: str = Field(
        default="data/images/processed/garments",
        validation_alias="IMAGES_PROCESSED_GARMENTS_DIR"
    )
    images_processed_outfits_dir: str = Field(
        default="data/images/processed/outfits",
        validation_alias="IMAGES_PROCESSED_OUTFITS_DIR"
    )
    models_cache_dir: str = Field(
        default="data/models_cache",
        validation_alias="MODELS_CACHE_DIR"
    )
    
    # AI Providers
    ai_provider: str = Field(
        default="local",
        validation_alias="AI_PROVIDER"
    )  # "local" or "nim"
    
    # NVIDIA NIM
    nim_api_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        validation_alias="NIM_API_URL"
    )
    nim_api_key: str = Field(
        default="",
        validation_alias="NIM_API_KEY"
    )
    nim_model: str = Field(
        default="nvidia/llama-3.1-nemotron-3-ultra",
        validation_alias="NIM_MODEL"
    )
    
    # Vision Models
    sam_model_type: str = Field(
        default="vit_h",
        validation_alias="SAM_MODEL_TYPE"
    )
    sam_checkpoint_url: str = Field(
        default="https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
        validation_alias="SAM_CHECKPOINT_URL"
    )
    clip_model: str = Field(
        default="ViT-B-32",
        validation_alias="CLIP_MODEL"
    )
    clip_pretrained: str = Field(
        default="openai",
        validation_alias="CLIP_PRETRAINED"
    )
    
    # Device
    device: str = Field(
        default="cuda",
        validation_alias="DEVICE"
    )
    
    # Frontend
    frontend_dir: str = Field(
        default="frontend",
        validation_alias="FRONTEND_DIR"
    )
    
    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:8000", "http://localhost:3000", "http://localhost:8080"],
        validation_alias="CORS_ORIGINS"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()