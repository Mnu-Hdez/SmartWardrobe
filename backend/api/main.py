# Smart Wardrobe - FastAPI Main Application
# App entry point, lifespan, SPA fallback, static mounts

from contextlib import asynccontextmanager
from pathlib import Path

import asyncio
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routers import wardrobe
from backend.core.config import read_daily_config, settings
from backend.database.connection import create_db_and_tables, get_db_session
from backend.services.outfit_service import OutfitService


async def _daily_outfit_scheduler() -> None:
    """Background loop: generates today's outfit shortly after local
    midnight, so it's ready before the kiosk is used, honoring
    the anti-repeat rules (no top repeated in 7 days, no bottom/outerwear on
    2 consecutive days). Just a pre-warm - GET /recommend/daily also
    generates on demand if this hasn't run yet, so a missed tick (e.g. the
    container was down at midnight) is never a hard failure."""
    while True:
        now = datetime.now()
        next_run = (now + timedelta(days=1)).replace(hour=0, minute=1, second=0, microsecond=0)
        await asyncio.sleep(max(1.0, (next_run - now).total_seconds()))
        try:
            config = read_daily_config()
            if not config.get("enabled", True):
                continue
            with get_db_session() as session:
                service = OutfitService(session)
                service.get_or_create_daily_outfit(
                    config["occasion"], config["season"], config.get("formality")
                )
            print("Daily outfit generated")
        except Exception as e:
            print(f"Daily outfit generation failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Smart Wardrobe API...")
    create_db_and_tables()
    print("Database tables created/verified")
    scheduler_task = asyncio.create_task(_daily_outfit_scheduler())
    yield
    # Shutdown
    scheduler_task.cancel()
    print("Shutting down Smart Wardrobe API...")


app = FastAPI(
    title="Smart Wardrobe API",
    description="AI-powered wardrobe management with SAM + CLIP",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - wildcard origins can't legally carry credentials (browsers reject
# it anyway), so only allow credentials when origins are explicitly listed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for frontend
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir / "static"), name="static")
    app.mount("/templates", StaticFiles(directory=frontend_dir / "templates"), name="templates")

# Image serving
if settings.IMAGES_RAW_DIR.exists():
    app.mount("/images/raw", StaticFiles(directory=settings.IMAGES_RAW_DIR), name="images_raw")
if settings.IMAGES_PROCESSED_GARMENTS_DIR.exists():
    app.mount(
        "/images/processed/garments",
        StaticFiles(directory=settings.IMAGES_PROCESSED_GARMENTS_DIR),
        name="images_processed",
    )

# Include routers
app.include_router(wardrobe.router)
app.include_router(wardrobe.outfit_router)
app.include_router(wardrobe.recommend_router)
app.include_router(wardrobe.feedback_router)
app.include_router(wardrobe.rules_router)
app.include_router(wardrobe.health_router)


# SPA Fallback - serve index.html for all non-API routes
@app.get("/{path:path}")
async def spa_fallback(path: str):
    """Serve SPA for all non-API routes"""
    # Skip API routes
    if (
        path.startswith("api/")
        or path.startswith("images/")
        or path.startswith("static/")
        or path.startswith("templates/")
    ):
        raise HTTPException(status_code=404, detail="Not found")

    # Serve index.html
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend not built")


if __name__ == "__main__":
    import uvicorn

    # Module path must match how this file is actually invoked (see Dockerfile
    # CMD: `uvicorn backend.api.main:app`) or reload/import resolution breaks.
    uvicorn.run(
        "backend.api.main:app", host=settings.API_SERVER_IP, port=settings.API_PORT, reload=True
    )
