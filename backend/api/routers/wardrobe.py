# Smart Wardrobe - API Router
# Wardrobe CRUD endpoints

import os
import shutil
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlmodel import Session

from backend.core.config import settings
from backend.database.connection import get_session
from backend.models.garment import Garment, Outfit, OutfitItem, StyleRule
from backend.models.schemas import (
    BulkDeleteRequest,
    FeedbackRequest,
    FeedbackResponse,
    GarmentCreate,
    GarmentListResponse,
    GarmentResponse,
    GarmentUpdate,
    HealthResponse,
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
)
from backend.repositories.garment_repo import (
    GarmentRepository,
    OutfitItemRepository,
    OutfitRepository,
    StyleRuleRepository,
)
from backend.services.outfit_service import OutfitService

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


@router.post("", response_model=GarmentResponse, status_code=status.HTTP_201_CREATED)
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
    garmentImage: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Create a new garment with image upload"""
    # Validate image
    if not garmentImage.content_type or not garmentImage.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Generate unique filenames
    ext = os.path.splitext(garmentImage.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".jpg"

    raw_filename = f"{uuid.uuid4()}{ext}"
    raw_path = settings.IMAGES_RAW_DIR / raw_filename

    # Save raw image
    with open(raw_path, "wb") as f:
        shutil.copyfileobj(garmentImage.file, f)

    # TODO: Process with SAM to create mask (processed image)
    # For now, copy raw as processed
    processed_filename = f"{uuid.uuid4()}.png"
    processed_path = settings.IMAGES_PROCESSED_GARMENTS_DIR / processed_filename
    shutil.copy2(raw_path, processed_path)

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
    )

    garment = Garment(
        **garment_data.model_dump(),
        raw_image_path=raw_filename,
        processed_image_path=processed_filename,
    )

    repo = GarmentRepository(session)
    created = repo.create(garment)

    return GarmentResponse.model_validate(created)


@router.get("/{garment_id}", response_model=GarmentResponse)
async def get_garment(garment_id: int, session: Session = Depends(get_session)):
    """Get a single garment by ID"""
    repo = GarmentRepository(session)
    garment = repo.get_by_id(garment_id)
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")
    return GarmentResponse.model_validate(garment)


@router.patch("/{garment_id}", response_model=GarmentResponse)
async def update_garment(
    garment_id: int, garment_update: GarmentUpdate, session: Session = Depends(get_session)
):
    """Update garment metadata (not image)"""
    repo = GarmentRepository(session)
    garment = repo.update(garment_id, garment_update)
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")
    return GarmentResponse.model_validate(garment)


@router.delete("/{garment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_garment(garment_id: int, session: Session = Depends(get_session)):
    """Delete a garment"""
    repo = GarmentRepository(session)
    success = repo.delete(garment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Garment not found")


@router.post("/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_garments(request: BulkDeleteRequest, session: Session = Depends(get_session)):
    """Bulk delete garments by IDs"""
    repo = GarmentRepository(session)
    deleted = repo.bulk_delete(request.ids)
    return {"deleted": deleted}


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


@outfit_router.post("", response_model=OutfitResponse, status_code=status.HTTP_201_CREATED)
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


@outfit_router.patch("/{outfit_id}", response_model=OutfitResponse)
async def update_outfit(
    outfit_id: int, outfit_update: OutfitUpdate, session: Session = Depends(get_session)
):
    """Update outfit"""
    repo = OutfitRepository(session)
    outfit = repo.update(outfit_id, outfit_update)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return OutfitResponse.model_validate(outfit)


@outfit_router.delete("/{outfit_id}", status_code=status.HTTP_204_NO_CONTENT)
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


# ========== FEEDBACK ENDPOINTS ==========

feedback_router = APIRouter(prefix="/feedback", tags=["Feedback"])


@feedback_router.post("/outfit", response_model=FeedbackResponse)
async def rate_outfit(request: FeedbackRequest, session: Session = Depends(get_session)):
    """Rate an outfit"""
    service = OutfitService(session)
    success = service.rate_outfit(request.outfit_id, request.rating, request.feedback_type)
    return FeedbackResponse(success=success, message="Feedback recorded")


@feedback_router.post("/garment", response_model=FeedbackResponse)
async def rate_garment(request: FeedbackRequest, session: Session = Depends(get_session)):
    """Rate a garment"""
    service = OutfitService(session)
    success = service.rate_garment(request.garment_id, request.rating, request.feedback_type)
    return FeedbackResponse(success=success, message="Feedback recorded")


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


@rules_router.post("", response_model=StyleRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(rule_data: StyleRuleCreate, session: Session = Depends(get_session)):
    """Create a style rule"""
    repo = StyleRuleRepository(session)
    rule = StyleRule(
        name=rule_data.name,
        rule_type=rule_data.rule_type,
        parameters=rule_data.parameters,
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


@rules_router.patch("/{rule_id}", response_model=StyleRuleResponse)
async def update_rule(
    rule_id: int, rule_update: StyleRuleUpdate, session: Session = Depends(get_session)
):
    """Update a style rule"""
    repo = StyleRuleRepository(session)

    update_data = rule_update.model_dump(exclude_unset=True)

    # Convert to StyleRuleUpdate for repo
    rule = repo.update(rule_id, StyleRuleUpdate(**update_data))
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return StyleRuleResponse.model_validate(rule)


@rules_router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
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
