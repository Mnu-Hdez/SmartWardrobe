import logging
from pathlib import Path
from contextlib import asynccontextmanager

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

    provider = AIProviderFactory.get_available_provider()
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

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.main:app", host=settings.host, port=settings.port, reload=settings.debug
    )


from pathlib import Path
