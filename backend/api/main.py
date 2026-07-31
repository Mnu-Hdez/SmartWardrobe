import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routers import wardrobe
from backend.core.config import get_settings
from backend.database.connection import create_db_and_tables, init_db

settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO if not settings.debug else logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Smart Wardrobe Outfit System...")

    # Initialize database
    create_db_and_tables()
    init_db()
    logger.info("Database initialized")

    # Initialize AI provider
    from backend.ai_providers.factory import AIProviderFactory

    provider = await AIProviderFactory.get_available_provider()
    logger.info(f"AI Provider: {provider.name}")

    yield

    # Cleanup
    logger.info("Shutting down...")
    AIProviderFactory.clear_cache()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered outfit recommendation system",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS middleware - Allow all origins for local network access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for kiosk access
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(wardrobe.router)

    # Mount static files for frontend
    static_dir = Path(settings.frontend_dir) / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Mount templates for SPA router (kiosk.html, settings.html)
    templates_dir = Path(settings.frontend_dir) / "templates"
    if templates_dir.exists():
        app.mount("/templates", StaticFiles(directory=str(templates_dir)), name="templates")

    # Mount images directories for serving garment images
    images_raw_dir = Path(settings.images_raw_dir)
    if images_raw_dir.exists():
        app.mount("/images/raw", StaticFiles(directory=str(images_raw_dir)), name="images_raw")

    images_processed_dir = Path(settings.images_processed_garments_dir)
    if images_processed_dir.exists():
        app.mount("/images/processed/garments", StaticFiles(directory=str(images_processed_dir)), name="images_processed_garments")

    # Serve frontend index.html for SPA
    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend():
        index_path = Path(settings.frontend_dir) / "index.html"
        if index_path.exists():
            return index_path.read_text()
        return "<h1>Smart Wardrobe Outfit System</h1><p>Frontend not built. Run <code>npm run build</code> in frontend directory.</p>"

    # Health check at root level too
    @app.get("/health")
    async def health():
        return {"status": "healthy", "version": settings.app_version}

    # SPA fallback - serve index.html for all non-API, non-static, non-template routes
    @app.get("/{full_path:path}", response_class=HTMLResponse)
    @app.head("/{full_path:path}", response_class=HTMLResponse)
    async def spa_fallback(full_path: str):
        # Skip API routes, static files, templates, and images
        if full_path.startswith("api/") or full_path.startswith("static/") or full_path.startswith("images/") or full_path.startswith("templates/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")

        index_path = Path(settings.frontend_dir) / "index.html"
        if index_path.exists():
            return index_path.read_text()
        return "<h1>Smart Wardrobe Outfit System</h1><p>Frontend not built.</p>"

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.main:app", host=settings.host, port=settings.port, reload=settings.debug
    )


