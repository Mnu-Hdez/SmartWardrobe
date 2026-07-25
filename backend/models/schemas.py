from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


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


class FormalityLevel(int, Enum):
    CASUAL = 1
    SMART_CASUAL = 2
    BUSINESS_CASUAL = 3
    FORMAL = 4
    BLACK_TIE = 5


class PatternType(str, Enum):
    SOLID = "solid"
    STRIPED = "striped"
    CHECKERED = "checkered"
    FLORAL = "floral"
    POLKA_DOT = "polka_dot"
    GEOMETRIC = "geometric"
    ABSTRACT = "abstract"


class FeedbackType(str, Enum):
    LIKE = "like"
    DISLIKE = "dislike"
    NEUTRAL = "neutral"


class AIProviderType(str, Enum):
    LOCAL = "local"
    NIM = "nim"


# Base schemas
class GarmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    type: GarmentType
    color_name: str = Field(..., max_length=50)
    dominant_color_hex: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    pattern: PatternType = PatternType.SOLID
    formality: FormalityLevel = FormalityLevel.CASUAL
    season: Season = Season.ALL_SEASON
    material: Optional[str] = Field(None, max_length=100)
    size: Optional[str] = Field(None, max_length=20)
    price: Optional[float] = Field(None, ge=0)
    purchase_date: Optional[datetime] = None
    image_path: Optional[str] = None
    segmentation_mask_path: Optional[str] = None
    notes: Optional[str] = None


class GarmentCreate(GarmentBase):
    pass


class GarmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    type: Optional[GarmentType] = None
    color_name: Optional[str] = Field(None, max_length=50)
    dominant_color_hex: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    pattern: Optional[PatternType] = None
    formality: Optional[FormalityLevel] = None
    season: Optional[Season] = None
    material: Optional[str] = Field(None, max_length=100)
    size: Optional[str] = Field(None, max_length=20)
    price: Optional[float] = Field(None, ge=0)
    purchase_date: Optional[datetime] = None
    image_path: Optional[str] = None
    segmentation_mask_path: Optional[str] = None
    notes: Optional[str] = None
    is_favorite: Optional[bool] = None


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
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    is_packing: bool = False
    notes: Optional[str] = None


class OutfitCreate(OutfitBase):
    garment_ids: List[int] = Field(..., min_length=1, max_length=10)


class OutfitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    occasion: Optional[str] = Field(None, max_length=100)
    season: Optional[Season] = None
    score: Optional[float] = Field(None, ge=0.0, le=100.0)
    is_packing: Optional[bool] = None
    notes: Optional[str] = None
    garment_ids: Optional[List[int]] = None


class OutfitRead(OutfitBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime


class OutfitWithGarments(OutfitRead):
    garments: List[GarmentRead] = []


# Style Rule schemas
class StyleRuleType(str, Enum):
    COLOR_HARMONY = "color_harmony"
    FORMALITY_MATCH = "formality_match"
    PATTERN_BALANCE = "pattern_balance"
    SEASON_MATCH = "season_match"
    OCCASION_MATCH = "occasion_match"


class StyleRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    rule_type: StyleRuleType
    weight: float = Field(default=1.0, ge=0.0, le=10.0)
    parameters: dict = Field(default_factory=dict)
    is_active: bool = True


class StyleRuleCreate(StyleRuleBase):
    pass


class StyleRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    rule_type: Optional[StyleRuleType] = None
    weight: Optional[float] = Field(None, ge=0.0, le=10.0)
    parameters: Optional[dict] = None
    is_active: Optional[bool] = None


class StyleRuleRead(StyleRuleBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime


# Feedback schemas
class FeedbackBase(BaseModel):
    rating: int = Field(..., ge=-1, le=1)  # -1 dislike, 0 neutral, 1 like
    feedback_type: FeedbackType
    comment: Optional[str] = None


class UserFeedbackCreate(FeedbackBase):
    garment_id: Optional[int] = None
    outfit_id: Optional[int] = None


class UserFeedbackRead(FeedbackBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: Optional[int] = None
    garment_id: Optional[int] = None
    outfit_id: Optional[int] = None
    created_at: datetime


# AI Provider schemas
class AIProviderConfig(BaseModel):
    provider_type: AIProviderType
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    model: Optional[str] = None


class EnhanceRequest(BaseModel):
    outfit: OutfitRead
    context: str = ""
    user_preferences: dict = Field(default_factory=dict)


class EnhanceResponse(BaseModel):
    enhanced_description: str
    style_tips: List[str] = []
    confidence: float = Field(ge=0.0, le=1.0)


# Recommendation schemas
class RecommendationRequest(BaseModel):
    occasion: str = Field(..., max_length=100)
    season: Season = Season.ALL_SEASON
    formality: Optional[FormalityLevel] = None
    garment_ids: Optional[List[int]] = None
    exclude_garment_ids: Optional[List[int]] = None
    top_n: int = Field(default=5, ge=1, le=20)
    use_ai_enhancement: bool = False


class RecommendationResponse(BaseModel):
    outfits: List[OutfitWithGarments] = []
    total_found: int = 0


# Packing schemas
class PackingRequest(BaseModel):
    days: int = Field(..., ge=1, le=30)
    occasion: str = Field(..., max_length=100)
    season: Season = Season.ALL_SEASON
    garment_ids: Optional[List[int]] = None
    max_items: int = Field(default=15, ge=5, le=30)


class PackingResponse(BaseModel):
    outfits: List[OutfitWithGarments] = []
    garment_ids_used: List[int] = []
    mix_and_match_ratio: float = 0.0
    total_items: int = 0


# Feedback schemas
class RateOutfitRequest(BaseModel):
    outfit_id: int
    rating: int = Field(..., ge=-1, le=1)
    comment: Optional[str] = None


class RateGarmentRequest(BaseModel):
    garment_id: int
    rating: int = Field(..., ge=-1, le=1)
    comment: Optional[str] = None


# Health check
class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    timestamp: datetime
    database: str = "connected"
    ai_provider: str


# Pagination
class PaginatedResponse(BaseModel):
    items: List[BaseModel] = []
    total: int
    page: int
    page_size: int
    total_pages: int