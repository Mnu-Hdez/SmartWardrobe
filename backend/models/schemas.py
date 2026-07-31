from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.domain.enums import (
    AIProviderType,
    FeedbackType,
    FormalityLevel,
    GarmentType,
    PatternType,
    Season,
    StyleRuleType,
)


# Base schemas
class GarmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    brand: str | None = Field(None, max_length=100)
    type: GarmentType
    color_name: str = Field(..., max_length=50)
    dominant_color_hex: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    pattern: PatternType = PatternType.SOLID
    formality: FormalityLevel = FormalityLevel.CASUAL
    season: Season = Season.ALL_SEASON
    material: str | None = Field(None, max_length=100)
    size: str | None = Field(None, max_length=20)
    price: float | None = Field(None, ge=0)
    purchase_date: datetime | None = None
    raw_image_path: str | None = None
    processed_image_path: str | None = None
    segmentation_mask_path: str | None = None
    notes: str | None = None


class GarmentCreate(GarmentBase):
    pass


class GarmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    brand: str | None = Field(None, max_length=100)
    type: GarmentType | None = None
    color_name: str | None = Field(None, max_length=50)
    dominant_color_hex: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    pattern: PatternType | None = None
    formality: FormalityLevel | None = None
    season: Season | None = None
    material: str | None = Field(None, max_length=100)
    size: str | None = Field(None, max_length=20)
    price: float | None = Field(None, ge=0)
    purchase_date: datetime | None = None
    raw_image_path: str | None = None
    processed_image_path: str | None = None
    segmentation_mask_path: str | None = None
    notes: str | None = None
    is_favorite: bool | None = None


class GarmentRead(GarmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_favorite: bool
    wear_count: int
    created_at: datetime
    updated_at: datetime


class GarmentWithScore(GarmentRead):
    score: float = 0.0
    bias_score: float = 0.0


# Outfit schemas
class OutfitGarmentLinkBase(BaseModel):
    garment_id: int
    position: int = 0


class OutfitBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    occasion: str = Field(..., max_length=100)
    season: Season = Season.ALL_SEASON
    formality: int = Field(default=1, ge=1, le=5)
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    is_packing: bool = False
    notes: str | None = None


class OutfitCreate(OutfitBase):
    garment_ids: list[int] = Field(..., min_length=1, max_length=10)


class OutfitUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    occasion: str | None = Field(None, max_length=100)
    season: Season | None = None
    score: float | None = Field(None, ge=0.0, le=100.0)
    is_packing: bool | None = None
    notes: str | None = None
    garment_ids: list[int] | None = None


class OutfitRead(OutfitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class OutfitWithGarments(OutfitRead):
    garments: list[GarmentRead] = []


# Style Rule schemas

class StyleRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    rule_type: StyleRuleType
    weight: float = Field(default=1.0, ge=0.0, le=10.0)
    parameters: dict = Field(default_factory=dict)
    is_active: bool = True


class StyleRuleCreate(StyleRuleBase):
    pass


class StyleRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    rule_type: StyleRuleType | None = None
    weight: float | None = Field(None, ge=0.0, le=10.0)
    parameters: dict | None = None
    is_active: bool | None = None


class StyleRuleRead(StyleRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

    # Parse JSON string back to dict when reading from DB
    @field_validator("parameters", mode="before")
    @classmethod
    def parse_parameters(cls, v):
        import json
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return {}
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v or {}


# Feedback schemas
class FeedbackBase(BaseModel):
    rating: int = Field(..., ge=-1, le=1)  # -1 dislike, 0 neutral, 1 like
    feedback_type: FeedbackType
    comment: str | None = None


class UserFeedbackCreate(FeedbackBase):
    garment_id: int | None = None
    outfit_id: int | None = None
    context: str | None = None


class UserFeedbackRead(FeedbackBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    garment_id: int | None = None
    outfit_id: int | None = None
    created_at: datetime


# AI Provider schemas
class AIProviderConfig(BaseModel):
    provider_type: AIProviderType
    api_key: str | None = None
    api_url: str | None = None
    model: str | None = None


class EnhanceRequest(BaseModel):
    outfit: OutfitRead
    context: str = ""
    user_preferences: dict = Field(default_factory=dict)


class EnhanceResponse(BaseModel):
    enhanced_description: str
    style_tips: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0)


# Recommendation schemas
class RecommendationRequest(BaseModel):
    occasion: str = Field(..., max_length=100)
    season: Season = Season.ALL_SEASON
    formality: FormalityLevel | None = None
    garment_ids: list[int] | None = None
    exclude_garment_ids: list[int] | None = None
    top_n: int = Field(default=5, ge=1, le=20)
    use_ai_enhancement: bool = False


class OutfitRecommendationRequest(BaseModel):
    occasion: str = Field(..., max_length=100)
    season: Season = Season.ALL_SEASON
    formality: FormalityLevel | None = None
    garment_ids: list[int] | None = None
    exclude_garment_ids: list[int] | None = None
    top_n: int = Field(default=5, ge=1, le=20)


class OutfitRecommendationResponse(BaseModel):
    outfits: list[OutfitWithGarments] = []
    total_found: int = 0


# Packing schemas
class PackingRequest(BaseModel):
    days: int = Field(..., ge=1, le=30)
    occasion: str = Field(..., max_length=100)
    season: Season = Season.ALL_SEASON
    garment_ids: list[int] | None = None
    max_items: int = Field(default=15, ge=5, le=30)


class PackingResponse(BaseModel):
    outfits: list[OutfitWithGarments] = []
    garment_ids_used: list[int] = []
    mix_and_match_ratio: float = 0.0
    total_items: int = 0


# Feedback schemas
class RateOutfitRequest(BaseModel):
    outfit_id: int
    rating: int = Field(..., ge=-1, le=1)
    comment: str | None = None


class RateGarmentRequest(BaseModel):
    garment_id: int
    rating: int = Field(..., ge=-1, le=1)
    comment: str | None = None


# Health check
class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    timestamp: datetime
    database: str = "connected"
    ai_provider: str


# Pagination
class PaginatedResponse(BaseModel):
    items: list[BaseModel] = []
    total: int
    page: int
    page_size: int
    total_pages: int
