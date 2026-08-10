# Smart Wardrobe - Pydantic Schemas
# Request/Response models for API

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GarmentType(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"
    DRESS = "dress"
    OUTERWEAR = "outerwear"
    SHOES = "shoes"
    ACCESSORY = "accessory"


class Season(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"
    ALL_SEASON = "all_season"


class Pattern(str, Enum):
    SOLID = "solid"
    STRIPED = "striped"
    CHECKED = "checked"
    FLORAL = "floral"
    POLKA_DOT = "polka_dot"
    GEOMETRIC = "geometric"
    ABSTRACT = "abstract"
    ANIMAL_PRINT = "animal_print"
    PAISLEY = "paisley"
    HOUNDSTOOTH = "houndstooth"


class StyleRuleType(str, Enum):
    COLOR_HARMONY = "color_harmony"
    OCCASION_MATCH = "occasion_match"
    SEASON_MATCH = "season_match"
    FORMALITY_CAP = "formality_cap"


# ========== GARMENT SCHEMAS ==========


class GarmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    brand: str | None = Field(None, max_length=100)
    type: str = Field(..., description="Garment type")
    season: str = Field(default=Season.ALL_SEASON)
    size: str | None = Field(None, max_length=20)
    material: str | None = Field(None, max_length=100)
    color_name: str = Field(..., max_length=50)
    color_hex: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    dominant_color_hex: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    pattern: str = Field(default=Pattern.SOLID)
    formality: int = Field(default=1, ge=1, le=5)


class GarmentCreate(GarmentBase):
    """For creating a new garment (metadata only - image handled separately)"""

    pass


class GarmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    brand: str | None = Field(None, max_length=100)
    type: str | None = None
    season: str | None = None
    size: str | None = Field(None, max_length=20)
    material: str | None = Field(None, max_length=100)
    color_name: str | None = Field(None, max_length=50)
    color_hex: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    pattern: str | None = None
    formality: int | None = Field(None, ge=1, le=5)


class GarmentResponse(GarmentBase):
    id: int
    raw_image_path: str
    processed_image_path: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BulkDeleteRequest(BaseModel):
    ids: list[int]

    model_config = ConfigDict(from_attributes=True)


class GarmentListResponse(BaseModel):
    garments: list[GarmentResponse]
    total: int
    page: int
    page_size: int


# ========== OUTFIT SCHEMAS ==========


class OutfitItemResponse(BaseModel):
    id: int
    garment_id: int
    position: int
    garment: GarmentResponse

    model_config = ConfigDict(from_attributes=True)


class OutfitBase(BaseModel):
    name: str | None = Field(None, max_length=200)
    occasion: str
    season: str
    score: float | None = None
    score_breakdown: dict[str, float] | None = None
    ai_tips: list[str] | None = None


class OutfitCreate(OutfitBase):
    garment_ids: list[int] = Field(..., min_length=1)


class OutfitUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    occasion: str | None = None
    season: str | None = None
    score: float | None = None
    score_breakdown: dict[str, float] | None = None
    ai_tips: list[str] | None = None


class OutfitResponse(OutfitBase):
    id: int
    items: list[OutfitItemResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutfitListResponse(BaseModel):
    outfits: list[OutfitResponse]
    total: int
    page: int
    page_size: int


# ========== RECOMMENDATION SCHEMAS ==========


class OutfitRecommendationRequest(BaseModel):
    occasion: str
    season: str = Season.ALL_SEASON
    formality: int | None = Field(None, ge=1, le=5)
    top_n: int = Field(default=1, ge=1, le=10)
    exclude_garment_ids: list[int] | None = None


class OutfitRecommendationResponse(BaseModel):
    outfits: list[OutfitResponse]
    total_garments_analyzed: int
    processing_time_ms: float


# ========== FEEDBACK SCHEMAS ==========


class FeedbackRequest(BaseModel):
    outfit_id: int | None = None
    garment_id: int | None = None
    rating: int = Field(..., ge=-1, le=1)  # -1: dislike, 1: like
    feedback_type: str = Field(..., pattern=r"^(outfit|garment)$")


class FeedbackResponse(BaseModel):
    success: bool
    message: str


# ========== PACKING SCHEMAS ==========


class PackingPlanRequest(BaseModel):
    days: int = Field(..., ge=1, le=30)
    occasion: str = "travel"
    season: str = Season.ALL_SEASON
    max_items: int = Field(..., ge=5, le=30)


class PackingPlanItem(BaseModel):
    garment: GarmentResponse
    versatility_score: float
    days_covered: int


class PackingOutfit(OutfitResponse):
    """Reuse OutfitResponse shape so packing outfits serialize the same way."""
    pass


class PackingPlanResponse(BaseModel):
    outfits: list[OutfitResponse]
    packing_list: list[PackingPlanItem]
    total_items: int
    days_covered: int
    mix_and_match_ratio: float


# ========== STYLE RULE SCHEMAS ==========


class StyleRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    rule_type: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    weight: float = Field(default=1.0, gt=0)
    is_active: bool = True


class StyleRuleCreate(StyleRuleBase):
    pass


class StyleRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    rule_type: str | None = None
    parameters: dict[str, Any] | None = None
    weight: float | None = Field(None, gt=0)
    is_active: bool | None = None


class StyleRuleResponse(StyleRuleBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StyleRuleListResponse(BaseModel):
    rules: list[StyleRuleResponse]
    total: int


# ========== HEALTH SCHEMAS ==========


class HealthResponse(BaseModel):
    status: str
    database: str
    ai_provider: str
    version: str = "1.0.0"


# ========== AI PROVIDER SCHEMAS ==========


class AIProviderType(str, Enum):
    LOCAL = "local"
    NIM = "nim"


class FeedbackType(str, Enum):
    LIKE = "like"
    DISLIKE = "dislike"


class FormalityLevel(int, Enum):
    CASUAL = 1
    SMART_CASUAL = 2
    BUSINESS_CASUAL = 3
    FORMAL = 4
    BLACK_TIE = 5


class GarmentRead(GarmentResponse):
    pass


class OutfitRead(OutfitResponse):
    pass


class EnhanceRequest(BaseModel):
    outfit: OutfitRead
    context: str = ""
    user_preferences: dict[str, Any] | None = None


class EnhanceResponse(BaseModel):
    enhanced_description: str
    style_tips: list[str] = []
    confidence: float = Field(ge=0, le=1)


class UserFeedbackCreate(BaseModel):
    outfit_id: int | None = None
    garment_id: int | None = None
    rating: int = Field(..., ge=-1, le=1)
    feedback_type: FeedbackType
    context: str | None = None


class UserFeedbackRead(BaseModel):
    id: int
    outfit_id: int | None = None
    garment_id: int | None = None
    rating: int
    feedback_type: FeedbackType
    context: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Aliases for test compatibility
PackingRequest = PackingPlanRequest
PackingResponse = PackingPlanResponse
OutfitRecommendationRequest = OutfitRecommendationRequest
StyleRuleRead = StyleRuleResponse
PatternType = Pattern

# Backward compatibility aliases for tests
UserFeedback = UserFeedbackCreate
UserFeedbackRead = UserFeedbackRead
OutfitGarmentLink = OutfitItemResponse
