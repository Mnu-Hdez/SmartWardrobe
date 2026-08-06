# Smart Wardrobe - FastAPI Main Application
# App entry point, lifespan, SPA fallback, static mounts

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, SQLModel, create_engine

from backend.api.routers import wardrobe
from backend.core.config import settings

# Database setup
engine = create_engine(settings.DATABASE_URL, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Smart Wardrobe API...")
    create_db_and_tables()
    print("Database tables created/verified")
    yield
    # Shutdown
    print("Shutting down Smart Wardrobe API...")


app = FastAPI(
    title="Smart Wardrobe API",
    description="AI-powered wardrobe management with SAM + CLIP",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
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

    uvicorn.run("api.main:app", host=settings.API_SERVER_IP, port=settings.API_PORT, reload=True)
