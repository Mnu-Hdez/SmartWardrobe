import shutil
import uuid
import numpy as np
from datetime import datetime
from pathlib import Path
from PIL import Image

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlmodel import Session

from backend.ai_providers.factory import AIProviderFactory
from backend.core.config import get_settings
from backend.database.connection import get_session
from backend.models.schemas import (
    EnhanceRequest,
    EnhanceResponse,
    GarmentCreate,
    GarmentRead,
    GarmentUpdate,
    HealthResponse,
    OutfitCreate,
    OutfitRead,
    OutfitRecommendationRequest,
    OutfitRecommendationResponse,
    OutfitUpdate,
    PackingRequest,
    PackingResponse,
    StyleRuleCreate,
    StyleRuleRead,
    StyleRuleUpdate,
    UserFeedbackCreate,
    UserFeedbackRead,
)
from backend.repositories import (
    GarmentRepository,
    OutfitRepository,
    StyleRuleRepository,
)
from backend.services import FeedbackService, OutfitComposer, PackingService
from backend.vision.classifier import CLIPClassifier
from backend.vision.color_extractor import extract_colors_from_image
from backend.vision.segmenter import SAMSegmenter

router = APIRouter(prefix="/api/v1", tags=["wardrobe"])


# Health check
@router.get("/health", response_model=HealthResponse)
async def health_check():
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow(),
        database="connected",
        ai_provider=settings.ai_provider,
    )


# Garment endpoints
@router.post("/garments", response_model=GarmentRead, status_code=201)
async def create_garment(
    name: str = Form(...),
    type: str = Form(...),
    color_name: str = Form(...),
    color_hex: str = Form(...),
    pattern: str = Form("solid"),
    formality: int = Form(1),
    season: str = Form("all_season"),
    brand: str | None = Form(None),
    size: str | None = Form(None),
    material: str | None = Form(None),
    price: float | None = Form(None),
    image: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Create a new garment with image upload and AI analysis using dual storage."""
    repo = GarmentRepository(session)
    settings = get_settings()

    # Save RAW image (original for high-quality display)
    raw_dir = Path(settings.images_raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(image.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".jpg"

    filename = f"{uuid.uuid4()}{ext}"
    raw_path = raw_dir / filename

    with open(raw_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    # Process with vision pipeline
    # 1. Segment garment
    segmenter = SAMSegmenter()
    mask, masked_img, seg_conf = segmenter.segment_auto(Image.open(raw_path))

    # Save processed image to PROCESSED storage
    processed_dir = Path(settings.images_processed_garments_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    processed_filename = f"{uuid.uuid4()}{ext}"
    processed_path = processed_dir / processed_filename
    masked_img.save(processed_path)

    # Save mask
    mask_filename = f"{uuid.uuid4()}_mask.png"
    mask_path = processed_dir / mask_filename
    Image.fromarray((mask * 255).astype(np.uint8)).save(mask_path)

    # 2. Classify garment
    classifier = CLIPClassifier()
    classification = classifier.classify(Image.open(raw_path))

    # 3. Extract colors
    color_info = extract_colors_from_image(str(processed_path), str(mask_path))

    # Create garment record with DUAL image paths
    garment_data = GarmentCreate(
        name=name,
        type=classification["type"] if classification["type_confidence"] > 0.5 else type,
        color_name=color_info["dominant_color_name"],
        dominant_color_hex=color_info["dominant_color_hex"],
        pattern=classification["pattern"],
        formality=classification["formality"],
        season=classification["season"],
        brand=brand,
        size=size,
        material=material,
        price=price,
        raw_image_path=str(raw_path),  # RAW: original for display
        processed_image_path=str(processed_path),  # PROCESSED: segmented for AI
        segmentation_mask_path=str(mask_path),
    )

    garment = repo.create(garment_data)
    return garment


@router.get("/garments", response_model=list[GarmentRead])
async def list_garments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    type: str | None = Query(None),
    season: str | None = Query(None),
    session: Session = Depends(get_session),
):
    """List all garments with optional filters."""
    repo = GarmentRepository(session)

    if type:
        return repo.get_by_type(type, skip, limit)
    elif season:
        return repo.get_by_season(season, skip, limit)
    else:
        return repo.get_all(skip, limit)


@router.get("/garments/{garment_id}", response_model=GarmentRead)
async def get_garment(garment_id: int, session: Session = Depends(get_session)):
    """Get a specific garment by ID."""
    repo = GarmentRepository(session)
    garment = repo.get_by_id(garment_id)
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")
    return garment


@router.patch("/garments/{garment_id}", response_model=GarmentRead)
async def update_garment(
    garment_id: int, update: GarmentUpdate, session: Session = Depends(get_session)
):
    """Update garment metadata."""
    repo = GarmentRepository(session)
    garment = repo.update(garment_id, update)
    if not garment:
        raise HTTPException(status_code=404, detail="Garment not found")
    return garment


@router.delete("/garments/bulk", status_code=204)
async def delete_garments_bulk(garment_ids: list[int], session: Session = Depends(get_session)):
    """Delete multiple garments in a single transaction."""
    repo = GarmentRepository(session)
    deleted_count = 0
    for garment_id in garment_ids:
        if repo.delete(garment_id):
            deleted_count += 1

    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="No garments found to delete")

    return {"deleted": deleted_count}


@router.delete("/garments/{garment_id}", status_code=204)
async def delete_garment(garment_id: int, session: Session = Depends(get_session)):
    """Delete a garment."""
    repo = GarmentRepository(session)
    if not repo.delete(garment_id):
        raise HTTPException(status_code=404, detail="Garment not found")


# Outfit endpoints
@router.post("/outfits", response_model=OutfitRead, status_code=201)
async def create_outfit(outfit: OutfitCreate, session: Session = Depends(get_session)):
    """Create a new outfit from garment IDs."""
    repo = OutfitRepository(session)
    created = repo.create(outfit)
    return created


@router.get("/outfits", response_model=list[OutfitRead])
async def list_outfits(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    occasion: str | None = Query(None),
    season: str | None = Query(None),
    is_packing: bool | None = Query(None),
    session: Session = Depends(get_session),
):
    """List outfits with optional filters."""
    repo = OutfitRepository(session)

    if occasion:
        outfits = repo.get_by_occasion(occasion, skip, limit)
    elif season:
        outfits = repo.get_by_season(season, skip, limit)
    elif is_packing:
        outfits = repo.get_packing_outfits()
    else:
        outfits = repo.get_all(skip, limit)

    return outfits


@router.get("/outfits/{outfit_id}", response_model=OutfitRead)
async def get_outfit(outfit_id: int, session: Session = Depends(get_session)):
    """Get outfit with garment details."""
    repo = OutfitRepository(session)
    outfit = repo.get_with_garments(outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return outfit


@router.patch("/outfits/{outfit_id}", response_model=OutfitRead)
async def update_outfit(
    outfit_id: int, update: OutfitUpdate, session: Session = Depends(get_session)
):
    """Update an outfit."""
    repo = OutfitRepository(session)
    outfit = repo.update(outfit_id, update)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return outfit


@router.delete("/outfits/{outfit_id}", status_code=204)
async def delete_outfit(outfit_id: int, session: Session = Depends(get_session)):
    """Delete an outfit."""
    repo = OutfitRepository(session)
    if not repo.delete(outfit_id):
        raise HTTPException(status_code=404, detail="Outfit not found")


# Recommendation endpoint
@router.post("/recommend", response_model=OutfitRecommendationResponse)
async def recommend_outfits(
    request: OutfitRecommendationRequest, session: Session = Depends(get_session)
):
    """Get top-N outfit recommendations for an occasion."""
    composer = OutfitComposer(session)

    results = composer.recommend(
        occasion=request.occasion,
        season=request.season,
        formality=request.formality,
        garment_ids=request.garment_ids,
        exclude_garment_ids=request.exclude_garment_ids,
        top_n=request.top_n,
    )

    outfits = []
    for outfit, score in results:
        # Get full outfit with garments
        full_outfit = composer.get_outfit_with_details(outfit.id)
        if full_outfit:
            outfits.append(full_outfit)

    return OutfitRecommendationResponse(outfits=outfits, total_found=len(results))


# AI Enhancement endpoint
@router.post("/enhance", response_model=EnhanceResponse)
async def enhance_recommendation(request: EnhanceRequest, session: Session = Depends(get_session)):
    """Enhance an outfit recommendation with AI styling advice."""
    provider = AIProviderFactory.get_available_provider()
    result = await provider.enhance_recommendation(
        outfit=request.outfit, context=request.context, user_preferences=request.user_preferences
    )
    return result


# Feedback endpoints
@router.post("/feedback/outfit", response_model=UserFeedbackRead)
async def rate_outfit(feedback: UserFeedbackCreate, session: Session = Depends(get_session)):
    """Rate an outfit (like/dislike)."""
    if not feedback.outfit_id:
        raise HTTPException(status_code=400, detail="outfit_id required")

    service = FeedbackService(session)
    result = service.rate_outfit(
        outfit_id=feedback.outfit_id,
        rating=feedback.rating,
        comment=feedback.comment,
        context=feedback.context,
    )
    return result


@router.post("/feedback/garment", response_model=UserFeedbackRead)
async def rate_garment(feedback: UserFeedbackCreate, session: Session = Depends(get_session)):
    """Rate a garment (like/dislike)."""
    if not feedback.garment_id:
        raise HTTPException(status_code=400, detail="garment_id required")

    service = FeedbackService(session)
    result = service.rate_garment(
        garment_id=feedback.garment_id,
        rating=feedback.rating,
        comment=feedback.comment,
        context=feedback.context,
    )
    return result


@router.get("/feedback/outfit/{outfit_id}", response_model=list[UserFeedbackRead])
async def get_outfit_feedback(outfit_id: int, session: Session = Depends(get_session)):
    """Get all feedback for an outfit."""
    service = FeedbackService(session)
    return service.get_outfit_feedback(outfit_id)


@router.get("/feedback/garment/{garment_id}", response_model=list[UserFeedbackRead])
async def get_garment_feedback(garment_id: int, session: Session = Depends(get_session)):
    """Get all feedback for a garment."""
    service = FeedbackService(session)
    return service.get_garment_feedback(garment_id)


# Packing endpoint
@router.post("/packing", response_model=PackingResponse)
async def create_packing_plan(request: PackingRequest, session: Session = Depends(get_session)):
    """Generate optimized packing list for N days."""
    service = PackingService(session)

    try:
        result = service.plan_packing(
            days=request.days,
            occasion=request.occasion,
            season=request.season,
            max_items=request.max_items,
            garment_ids=request.garment_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PackingResponse(
        outfits=result.outfits,
        garment_count=result.total_items,
        days_covered=result.days_covered,
        mix_and_match_ratio=result.mix_and_match_ratio,
        message=f"Packed {result.total_items} items for {result.days_covered} days",
    )


# Style Rules endpoints
@router.post("/rules", response_model=StyleRuleRead, status_code=201)
async def create_rule(rule: StyleRuleCreate, session: Session = Depends(get_session)):
    """Create a new style rule."""
    repo = StyleRuleRepository(session)
    created = repo.create(rule)
    return created


@router.get("/rules", response_model=list[StyleRuleRead])
async def list_rules(active_only: bool = Query(True), session: Session = Depends(get_session)):
    """List style rules."""
    repo = StyleRuleRepository(session)
    return repo.get_all(active_only=active_only)


@router.get("/rules/{rule_id}", response_model=StyleRuleRead)
async def get_rule(rule_id: int, session: Session = Depends(get_session)):
    """Get a style rule."""
    repo = StyleRuleRepository(session)
    rule = repo.get_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.patch("/rules/{rule_id}", response_model=StyleRuleRead)
async def update_rule(
    rule_id: int, update: StyleRuleUpdate, session: Session = Depends(get_session)
):
    """Update a style rule."""
    repo = StyleRuleRepository(session)
    rule = repo.update(rule_id, update)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: int, session: Session = Depends(get_session)):
    """Delete a style rule."""
    repo = StyleRuleRepository(session)
    if not repo.delete(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
