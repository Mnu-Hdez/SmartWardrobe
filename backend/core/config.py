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

    # Auth - shared secret required on write endpoints (POST/PATCH/DELETE).
    # Empty by default so local dev keeps working; set a real value in .env for
    # any deployment reachable outside localhost (kiosk on LAN still fine).
    API_KEY: str = ""

    # Uploads
    MAX_UPLOAD_SIZE_MB: int = 10

    # AI Provider
    AI_PROVIDER: str = "local"
    NIM_API_KEY: str = ""
    NIM_VISION_MODEL: str = "meta/llama-3.2-11b-vision-instruct"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Where the runtime-configured AI provider/keys are persisted (survives
    # both `--reload` restarts and container restarts, since it lives in the
    # same durable volume as the DB and images - unlike settings.AI_PROVIDER
    # mutated in-memory by PATCH /config/ai, which a `--reload` restart wipes).
    AI_CONFIG_PATH: Path = Path("/app/data/ai_config.json")

    # Where the daily-outfit auto-generation defaults (occasion/season/
    # formality/enabled) are persisted - same durable-volume pattern as
    # AI_CONFIG_PATH, read by both the nightly scheduler and GET/PATCH
    # /config/daily.
    DAILY_CONFIG_PATH: Path = Path("/app/data/daily_config.json")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()

# Apply any runtime AI config saved by a previous PATCH /config/ai call -
# .env/docker-compose set the *defaults*, this overrides them with whatever
# was last saved from the Settings UI, so a `--reload` restart (which happens
# on every file save during dev) doesn't silently drop the configured provider.
def _load_persisted_ai_config() -> None:
    import json

    if not settings.AI_CONFIG_PATH.exists():
        return
    try:
        data = json.loads(settings.AI_CONFIG_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return
    if data.get("provider"):
        settings.AI_PROVIDER = data["provider"]
    if data.get("nim_api_key"):
        settings.NIM_API_KEY = data["nim_api_key"]
    if data.get("gemini_api_key"):
        settings.GEMINI_API_KEY = data["gemini_api_key"]


_load_persisted_ai_config()

# Note: directory creation used to be a lazy no-op (the promise was in
# this comment, not in code) - a Docker volume created before a path was
# added to the Dockerfile, or a local `make dev` without Docker, would hit
# a bare FileNotFoundError deep in POST /garments the first time someone
# tried to save a photo (DB writes were unaffected, so the rest of the app
# looked fine). Actually create everything up front instead.
def _ensure_data_dirs() -> None:
    for directory in (
        settings.IMAGES_RAW_DIR,
        settings.IMAGES_PROCESSED_GARMENTS_DIR,
        settings.MODELS_CACHE_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    for config_path in (settings.AI_CONFIG_PATH, settings.DAILY_CONFIG_PATH):
        config_path.parent.mkdir(parents=True, exist_ok=True)

    # SQLite needs its parent directory to exist before the engine can open
    # it - only sqlite:///relative/path and sqlite:////absolute/path are
    # used in this project, so a simple prefix check covers both forms.
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:////"):
        Path("/" + db_url.removeprefix("sqlite:////")).parent.mkdir(parents=True, exist_ok=True)
    elif db_url.startswith("sqlite:///"):
        Path(db_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)


_ensure_data_dirs()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


DEFAULT_DAILY_CONFIG = {"occasion": "casual", "season": "all_season", "formality": None, "enabled": True}


def read_daily_config() -> dict:
    """Read the persisted daily-outfit generation defaults, falling back to
    DEFAULT_DAILY_CONFIG if nothing was saved yet (first run) or the file is
    unreadable/corrupt."""
    import json

    if not settings.DAILY_CONFIG_PATH.exists():
        return dict(DEFAULT_DAILY_CONFIG)
    try:
        data = json.loads(settings.DAILY_CONFIG_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_DAILY_CONFIG)
    return {**DEFAULT_DAILY_CONFIG, **data}
