# Smart Wardrobe - API Router
# Wardrobe CRUD endpoints

import logging
import shutil
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from backend.core.auth import require_api_key
from backend.core.config import read_daily_config, settings
from backend.ai_providers import AIProviderProtocol
from backend.ai_providers.factory import get_ai_provider
from backend.database.connection import get_session
from backend.models.garment import Garment, Outfit, OutfitItem, StyleRule
from backend.models.schemas import (
    AIConfigResponse,
    AIConfigUpdate,
    DailyOutfitConfig,
    DailyOutfitConfigResponse,
    FeedbackRequest,
    FeedbackResponse,
    GarmentCreate,
    GarmentListResponse,
    GarmentResponse,
    GarmentSwapRequest,
    GarmentUpdate,
    HealthResponse,
    ImageAnalysisResponse,
    OutfitCreate,
    OutfitListResponse,
    OutfitRecommendationRequest,
    OutfitRecommendationResponse,
    OutfitResponse,
    OutfitUpdate,
    PackingPlanRequest,
    PackingPlanResponse,
    StyleRuleCreate,
    StyleRuleListResponse,
    StyleRuleResponse,
    StyleRuleUpdate,
    TagSuggestionRequest,
    TagSuggestionResponse,
)
from backend.repositories.garment_repo import (
    GarmentRepository,
    OutfitItemRepository,
    OutfitRepository,
    StyleRuleRepository,
)
from backend.services.outfit_service import OutfitService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/garments", tags=["Garments"])


# ========== GARMENT ENDPOINTS ==========


@router.get("", response_model=GarmentListResponse)
async def list_garments(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    search: str | None = None,
    type: str | None = None,
    season: str | None = None,
    session: Session = Depends(get_session),
):
    """List garments with pagination and filters"""
    repo = GarmentRepository(session)
    offset = (page - 1) * page_size

    filters = {}
    if search:
        filters["search"] = search
    if type:
        filters["type"] = type
    if season:
        filters["season"] = season

    garments = repo.get_all(limit=page_size, offset=offset, filters=filters)
    total = repo.count(filters=filters)

    return GarmentListResponse(
        garments=[GarmentResponse.model_validate(g) for g in garments],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=GarmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
async def create_garment(
    name: str = Form(...),
    brand: str | None = Form(None),
    type: str = Form(...),
    season: str = Form(...),
    size: str | None = Form(None),
    material: str | None = Form(None),
    color_name: str = Form(...),
    color_hex: str = Form(...),
    pattern: str = Form(...),
    formality: int = Form(...),
    tags: str | None = Form(None),
    garmentImage: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Create a new garment with image upload"""
    # Content-Type header is client-supplied and trivially spoofable, so it's
    # only a fast pre-check; the real check is decoding the bytes below.
    if not garmentImage.content_type or not garmentImage.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    raw_bytes = await garmentImage.read(max_bytes + 1)
    if len(raw_bytes) > max_bytes:
        raise HTTPException(
            status_code=413, detail=f"Image exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit"
        )

    from io import BytesIO

    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(BytesIO(raw_bytes)) as img:
            img.verify()
            detected_format = (img.format or "JPEG").lower()
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="File is not a valid image") from None

    ext_by_format = {"jpeg": ".jpg", "png": ".png", "webp": ".webp"}
    ext = ext_by_format.get(detected_format, ".jpg")

    raw_filename = f"{uuid.uuid4()}{ext}"
    raw_path = settings.IMAGES_RAW_DIR / raw_filename

    # Save raw image (already validated & read into memory above)
    with open(raw_path, "wb") as f:
        f.write(raw_bytes)

    # Background-removed "processed" image via the local SAM segmentation
    # pipeline. Best-effort: segmentation is expensive and its weights may
    # not be downloaded yet, so any failure falls back to the raw photo
    # (previous behavior) instead of blocking the upload.
    try:
        from backend.vision.ingestion_pipeline import IngestionPipeline

        with Image.open(BytesIO(raw_bytes)) as pil_image:
            processed_filename = IngestionPipeline().segment_and_save(pil_image.convert("RGB"))
    except Exception as e:
        logger.warning(
            f"Segmentation unavailable ({e}), using raw image as processed image"
        )
        processed_filename = f"{uuid.uuid4()}.png"
        processed_path = settings.IMAGES_PROCESSED_GARMENTS_DIR / processed_filename
        shutil.copy2(raw_path, processed_path)

    # Tags arrive as a JSON-encoded array string via multipart form (arrays
    # aren't natively supported in multipart/form-data), e.g. '["denim","casual"]'
    parsed_tags: list[str] = []
    if tags:
        import json

        try:
            loaded = json.loads(tags)
            if isinstance(loaded, list):
                parsed_tags = [str(t).strip().lower() for t in loaded if str(t).strip()]
        except json.JSONDecodeError:
            parsed_tags = [t.strip().lower() for t in tags.split(",") if t.strip()]

    # Create garment record
    garment_data = GarmentCreate(
        name=name,
        brand=brand,
        type=type,
        season=season,
        size=size,
        material=material,
        color_name=color_name,
        color_hex=color_hex,
        pattern=pattern,
        formality=formality,
        tags=parsed_tags,
    )

    garment = Garment(
        **garment_data.model_dump(),
        raw_image_path=raw_filename,
        processed_image_path=processed_filename,
    )

    repo = GarmentRepository(session)
    created = repo.create(garment)

    return GarmentResponse.model_validate(created)


@router.post("/suggest-tags", response_model=TagSuggestionResponse)
async def suggest_garment_tags(
    request: TagSuggestionRequest,
    provider: AIProviderProtocol = Depends(get_ai_provider),
):
    """Ask the configured AI provider (NIM, falling back to local) for tag
    suggestions. Read-only / side-effect-free - the user must still accept,
    edit, or reject each suggestion before it's saved on the garment."""
    suggested = provider.suggest_tags(
        name=request.name,
        garment_type=request.type,
        color_name=request.color_name,
        material=request.material,
        pattern=request.pattern,
        brand=request.brand,
        season=request.season,
        existing_tags=request.existing_tags,
    )
    return TagSuggestionResponse(suggested_tags=suggested, provider=provider.name)


@router.post("/analyze-image", response_model=ImageAnalysisResponse)
async def analyze_garment_image(
    image: UploadFile = File(...),
    provider: AIProviderProtocol = Depends(get_ai_provider),
):
    """Best-effort field guesses from a garment photo (name/type/color/
    material/pattern/formality/tags), used to auto-fill the add-garment form.
    Read-only / side-effect-free — nothing is saved, and every field the user
    sees remains editable before they submit, same review-before-accept
    pattern as tag suggestions."""
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    raw_bytes = await image.read(max_bytes + 1)
    if len(raw_bytes) > max_bytes:
        raise HTTPException(
            status_code=413, detail=f"Image exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit"
        )

    result = provider.analyze_image(raw_bytes, image.content_type)
    return ImageAnalysisResponse(**result, provider=provider.name)


@router.get("/export")
async def export_garments(session: Session = Depends(get_session)):
    """Download the whole wardrobe as a .zip: wardrobe.json (every
    garment's metadata) plus each garment's raw photo under images/, so the
    export round-trips through POST /garments/import with photos intact.
    Server-side file paths aren't included in the manifest since they won't
    exist on the machine importing it - each entry instead points at its
    image's archive path via `image_file`.
    """
    import io
    import json
    import zipfile
    from datetime import datetime

    repo = GarmentRepository(session)
    garments = repo.get_all(limit=100000)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = []
        for g in garments:
            entry = json.loads(GarmentResponse.model_validate(g).model_dump_json())
            raw_path = settings.IMAGES_RAW_DIR / g.raw_image_path
            if raw_path.exists():
                archive_name = f"images/{g.raw_image_path}"
                zf.write(raw_path, archive_name)
                entry["image_file"] = archive_name
            else:
                entry["image_file"] = None
            manifest.append(entry)

        zf.writestr(
            "wardrobe.json",
            json.dumps(
                {"version": 1, "exported_at": datetime.utcnow().isoformat(), "garments": manifest},
                indent=2,
            ),
        )

    buffer.seek(0)
    filename = f"smart-wardrobe-export-{datetime.utcnow().strftime('%Y-%m-%d')}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", dependencies=[Depends(require_api_key)])
async def import_garments(
    file: UploadFile = File(...), session: Session = Depends(get_session)
):
    """Import garments from a .zip previously produced by GET /garments/export.
    Additive merge, not an overwrite - every entry becomes a brand-new
    garment with a fresh id and its own copied image files, regardless of
    what was already in the wardrobe. Entries whose image is missing from
    the archive, or whose metadata fails validation, are skipped rather
    than aborting the whole import.
    """
    import io
    import json
    import zipfile
    from pathlib import Path

    from pydantic import ValidationError

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip export")

    max_bytes = 500 * 1024 * 1024  # generous cap for a whole-wardrobe archive
    raw_bytes = await file.read(max_bytes + 1)
    if len(raw_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail="Export file is too large")

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw_bytes))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="File is not a valid .zip export") from None

    try:
        manifest = json.loads(zf.read("wardrobe.json"))
    except KeyError:
        raise HTTPException(status_code=400, detail="Zip is missing wardrobe.json") from None
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="wardrobe.json is not valid JSON") from None

    archive_names = set(zf.namelist())
    repo = GarmentRepository(session)
    imported = 0
    skipped = 0

    for entry in manifest.get("garments", []):
        image_file = entry.get("image_file")
        if not image_file or image_file not in archive_names:
            skipped += 1
            continue

        try:
            garment_data = GarmentCreate(
                name=entry.get("name", "Imported garment"),
                brand=entry.get("brand"),
                type=entry.get("type", "top"),
                season=entry.get("season", "all_season"),
                size=entry.get("size"),
                material=entry.get("material"),
                color_name=entry.get("color_name", "Unknown"),
                color_hex=entry.get("color_hex", "#4a4a4a"),
                pattern=entry.get("pattern", "solid"),
                formality=entry.get("formality", 1),
                tags=entry.get("tags", []),
            )
        except ValidationError:
            skipped += 1
            continue

        image_bytes = zf.read(image_file)
        ext = Path(image_file).suffix or ".jpg"
        raw_filename = f"{uuid.uuid4()}{ext}"
        raw_path = settings.IMAGES_RAW_DIR / raw_filename
        with open(raw_path, "wb") as f:
            f.write(image_bytes)

        processed_filename = f"{uuid.uuid4()}.png"
        processed_path = settings.IMAGES_PROCESSED_GARMENTS_DIR / processed_filename
        shutil.copy2(raw_path, processed_path)

        garment = Garment(
            **garment_data.model_dump(),
            raw_image_path=raw_filename,
            processed_image_path=processed_filename,
        )
        repo.create(garment)
        imported += 1

    return {"imported": imported, "skipped": skipped}


@router.get("/{garment_id}", response_model=GarmentResponse)
async def get_garment(garment_id: int, session: Session = Depends(get_session)):
    """Get a single garment by ID"""
    repo = GarmentRepository(session)
    garment = repo.get_by_id(garment_id)
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")
    return GarmentResponse.model_validate(garment)


@router.patch("/{garment_id}", response_model=GarmentResponse, dependencies=[Depends(require_api_key)])
async def update_garment(
    garment_id: int, garment_update: GarmentUpdate, session: Session = Depends(get_session)
):
    """Update garment metadata (not image)"""
    repo = GarmentRepository(session)
    garment = repo.update(garment_id, garment_update)
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")
    return GarmentResponse.model_validate(garment)


@router.delete("/{garment_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_api_key)])
async def delete_garment(garment_id: int, session: Session = Depends(get_session)):
    """Delete a garment"""
    repo = GarmentRepository(session)
    success = repo.delete(garment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Garment not found")


@router.post("/bulk-delete", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_api_key)])
async def bulk_delete_garments(ids: list[int], session: Session = Depends(get_session)):
    """Bulk delete garments by IDs"""
    if len(ids) > 500:
        raise HTTPException(status_code=400, detail="Cannot delete more than 500 garments at once")
    repo = GarmentRepository(session)
    # A 204 response must not carry a body (RFC 7231 6.3.5) - returning the
    # {"deleted": ...} dict here made Starlette/uvicorn emit a malformed
    # response that the browser's fetch() rejects, so bulk delete always
    # failed client-side even though the DB rows were actually removed.
    repo.bulk_delete(ids)


# ========== OUTFIT ENDPOINTS ==========

outfit_router = APIRouter(prefix="/outfits", tags=["Outfits"])


@outfit_router.get("", response_model=OutfitListResponse)
async def list_outfits(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """List outfits with pagination"""
    repo = OutfitRepository(session)
    offset = (page - 1) * page_size
    outfits = repo.get_all(limit=page_size, offset=offset)
    total = repo.count()
    return OutfitListResponse(
        outfits=[OutfitResponse.model_validate(o) for o in outfits],
        total=total,
        page=page,
        page_size=page_size,
    )


@outfit_router.post("", response_model=OutfitResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
async def create_outfit(outfit_data: OutfitCreate, session: Session = Depends(get_session)):
    """Create a new outfit from garment IDs"""
    garment_repo = GarmentRepository(session)
    outfit_repo = OutfitRepository(session)
    item_repo = OutfitItemRepository(session)

    # Verify all garments exist
    for gid in outfit_data.garment_ids:
        if not garment_repo.get_by_id(gid):
            raise HTTPException(status_code=404, detail=f"Garment {gid} not found")

    # Create outfit
    outfit = Outfit(
        name=outfit_data.name,
        occasion=outfit_data.occasion,
        season=outfit_data.season,
        score=outfit_data.score,
        score_breakdown=outfit_data.score_breakdown,
        ai_tips=outfit_data.ai_tips,
    )
    saved = outfit_repo.create(outfit)

    # Create outfit items
    items = [
        OutfitItem(outfit_id=saved.id, garment_id=gid, position=i)
        for i, gid in enumerate(outfit_data.garment_ids)
    ]
    item_repo.bulk_create(items)

    # Reload with items
    saved.items = item_repo.get_by_outfit(saved.id)
    return OutfitResponse.model_validate(saved)


@outfit_router.get("/{outfit_id}", response_model=OutfitResponse)
async def get_outfit(outfit_id: int, session: Session = Depends(get_session)):
    """Get a single outfit by ID"""
    repo = OutfitRepository(session)
    item_repo = OutfitItemRepository(session)
    outfit = repo.get_by_id(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    outfit.items = item_repo.get_by_outfit(outfit_id)
    return OutfitResponse.model_validate(outfit)


@outfit_router.patch("/{outfit_id}", response_model=OutfitResponse, dependencies=[Depends(require_api_key)])
async def update_outfit(
    outfit_id: int, outfit_update: OutfitUpdate, session: Session = Depends(get_session)
):
    """Update outfit"""
    repo = OutfitRepository(session)
    outfit = repo.update(outfit_id, outfit_update)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return OutfitResponse.model_validate(outfit)


@outfit_router.delete("/{outfit_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_api_key)])
async def delete_outfit(outfit_id: int, session: Session = Depends(get_session)):
    """Delete an outfit"""
    repo = OutfitRepository(session)
    item_repo = OutfitItemRepository(session)

    item_repo.delete_by_outfit(outfit_id)
    success = repo.delete(outfit_id)
    if not success:
        raise HTTPException(status_code=404, detail="Outfit not found")


# ========== RECOMMENDATION ENDPOINTS ==========

recommend_router = APIRouter(prefix="/recommend", tags=["Recommendations"])


@recommend_router.post("/outfits", response_model=OutfitRecommendationResponse)
async def recommend_outfits(
    request: OutfitRecommendationRequest, session: Session = Depends(get_session)
):
    """Generate outfit recommendations"""
    service = OutfitService(session)
    result = service.recommend_outfits(request)
    return OutfitRecommendationResponse(**result)


@recommend_router.post("/packing", response_model=PackingPlanResponse)
async def create_packing_plan(request: PackingPlanRequest, session: Session = Depends(get_session)):
    """Create a packing plan for a trip"""
    service = OutfitService(session)
    result = service.create_packing_plan(request)
    return PackingPlanResponse(**result)


@recommend_router.post("/swap-garment", response_model=OutfitResponse)
async def swap_garment(request: GarmentSwapRequest, session: Session = Depends(get_session)):
    """Swap one garment of the current look for the next/previous of the
    same type (kiosk per-garment swipe gesture); rebalances the rest of
    the look against the active style rules."""
    service = OutfitService(session)
    try:
        result = service.swap_garment(request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return OutfitResponse.model_validate(result)


@recommend_router.get("/daily", response_model=OutfitResponse)
async def get_daily_outfit(session: Session = Depends(get_session)):
    """Today's automatically generated look (no top repeated in 7 days, no
    bottom/outerwear repeated on 2 consecutive days). Generates it on this
    call if the nightly scheduler hasn't run yet today - idempotent, so
    reloading the kiosk never regenerates a fresh one."""
    config = read_daily_config()
    service = OutfitService(session)
    try:
        result = service.get_or_create_daily_outfit(
            config["occasion"], config["season"], config.get("formality")
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return OutfitResponse.model_validate(result)


# ========== FEEDBACK ENDPOINTS ==========

feedback_router = APIRouter(prefix="/feedback", tags=["Feedback"])


@feedback_router.post("/outfit", response_model=FeedbackResponse)
async def rate_outfit(request: FeedbackRequest, session: Session = Depends(get_session)):
    """Rate an outfit"""
    service = OutfitService(session)
    success = service.rate_outfit(request.outfit_id, request.rating)
    if not success:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return FeedbackResponse(success=True, message="Feedback recorded")


@feedback_router.post("/garment", response_model=FeedbackResponse)
async def rate_garment(request: FeedbackRequest, session: Session = Depends(get_session)):
    """Rate a garment"""
    service = OutfitService(session)
    success = service.rate_garment(request.garment_id, request.rating)
    if not success:
        raise HTTPException(status_code=404, detail="Garment not found")
    return FeedbackResponse(success=True, message="Feedback recorded")


# ========== STYLE RULE ENDPOINTS ==========

rules_router = APIRouter(prefix="/rules", tags=["Style Rules"])


@rules_router.get("", response_model=StyleRuleListResponse)
async def list_rules(active_only: bool = Query(True), session: Session = Depends(get_session)):
    """List style rules"""
    repo = StyleRuleRepository(session)
    rules = repo.get_all(active_only=active_only)
    total = repo.count(active_only=active_only)
    return StyleRuleListResponse(
        rules=[StyleRuleResponse.model_validate(r) for r in rules], total=total
    )


@rules_router.post("", response_model=StyleRuleResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
async def create_rule(rule_data: StyleRuleCreate, session: Session = Depends(get_session)):
    """Create a style rule"""
    import json

    repo = StyleRuleRepository(session)
    rule = StyleRule(
        name=rule_data.name,
        rule_type=rule_data.rule_type,
        parameters=json.dumps(rule_data.parameters),
        weight=rule_data.weight,
        is_active=rule_data.is_active,
    )
    created = repo.create(rule)
    return StyleRuleResponse.model_validate(created)


@rules_router.get("/{rule_id}", response_model=StyleRuleResponse)
async def get_rule(rule_id: int, session: Session = Depends(get_session)):
    """Get a style rule by ID"""
    repo = StyleRuleRepository(session)
    rule = repo.get_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return StyleRuleResponse.model_validate(rule)


@rules_router.patch("/{rule_id}", response_model=StyleRuleResponse, dependencies=[Depends(require_api_key)])
async def update_rule(
    rule_id: int, rule_update: StyleRuleUpdate, session: Session = Depends(get_session)
):
    """Update a style rule"""
    import json

    repo = StyleRuleRepository(session)

    update_data = rule_update.model_dump(exclude_unset=True)
    if "parameters" in update_data:
        update_data["parameters"] = json.dumps(update_data["parameters"])

    # Convert to StyleRuleUpdate for repo
    rule = repo.update(rule_id, StyleRuleUpdate(**update_data))
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return StyleRuleResponse.model_validate(rule)


@rules_router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_api_key)])
async def delete_rule(rule_id: int, session: Session = Depends(get_session)):
    """Delete a style rule"""
    repo = StyleRuleRepository(session)
    success = repo.delete(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")


# ========== HEALTH ENDPOINT ==========

health_router = APIRouter(prefix="", tags=["Health"])


@health_router.get("/health", response_model=HealthResponse)
async def health_check(session: Session = Depends(get_session)):
    """Health check endpoint"""
    from sqlmodel import select

    try:
        session.exec(select(1))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(status="ok", database=db_status, ai_provider=settings.AI_PROVIDER)


@health_router.get("/config/ai", response_model=AIConfigResponse)
async def get_ai_config():
    """Current AI provider + which keys are configured (never returns the
    keys themselves, only whether they're set)."""
    return AIConfigResponse(
        provider=settings.AI_PROVIDER,
        nim_configured=bool(settings.NIM_API_KEY),
        gemini_configured=bool(settings.GEMINI_API_KEY),
    )


@health_router.patch("/config/ai", response_model=AIConfigResponse, dependencies=[Depends(require_api_key)])
async def update_ai_config(config: AIConfigUpdate):
    """Switch AI provider / set API keys on the running process, AND persist
    them to settings.AI_CONFIG_PATH (in the durable data volume) so a
    `--reload` restart during dev - or a real container restart - doesn't
    silently revert to the .env/docker-compose defaults."""
    settings.AI_PROVIDER = config.provider
    if config.nim_api_key is not None:
        settings.NIM_API_KEY = config.nim_api_key
    if config.gemini_api_key is not None:
        settings.GEMINI_API_KEY = config.gemini_api_key

    import json

    settings.AI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    settings.AI_CONFIG_PATH.write_text(
        json.dumps(
            {
                "provider": settings.AI_PROVIDER,
                "nim_api_key": settings.NIM_API_KEY,
                "gemini_api_key": settings.GEMINI_API_KEY,
            }
        )
    )

    return AIConfigResponse(
        provider=settings.AI_PROVIDER,
        nim_configured=bool(settings.NIM_API_KEY),
        gemini_configured=bool(settings.GEMINI_API_KEY),
        persisted=True,
    )


@health_router.get("/config/daily", response_model=DailyOutfitConfigResponse)
async def get_daily_config():
    """Current defaults (occasion/season/formality/enabled) used by the
    nightly outfit-generation job."""
    return DailyOutfitConfigResponse(**read_daily_config())


@health_router.patch("/config/daily", response_model=DailyOutfitConfigResponse, dependencies=[Depends(require_api_key)])
async def update_daily_config(config: DailyOutfitConfig):
    """Persist the daily-generation defaults to settings.DAILY_CONFIG_PATH
    (durable data volume), read by both GET /recommend/daily and the
    scheduler on its next run."""
    import json

    settings.DAILY_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    settings.DAILY_CONFIG_PATH.write_text(json.dumps(config.model_dump()))
    return DailyOutfitConfigResponse(**config.model_dump())
