# backend/domain/models.py
"""Pure domain models — no DB coupling, no SQLModel, just dataclasses."""
from dataclasses import dataclass, field
from datetime import datetime

from backend.domain.enums import (
    FormalityLevel,
    GarmentType,
    PatternType,
    Season,
)


@dataclass
class Garment:
    """Pure domain model for a garment."""
    name: str
    type: GarmentType
    dominant_color_hex: str
    color_name: str
    pattern: PatternType = PatternType.SOLID
    formality: FormalityLevel = FormalityLevel.CASUAL
    season: Season = Season.ALL_SEASON
    brand: str | None = None
    size: str | None = None
    material: str | None = None
    price: float | None = None
    purchase_date: datetime | None = None
    raw_image_path: str | None = None
    processed_image_path: str | None = None
    segmentation_mask_path: str | None = None
    notes: str | None = None
    is_favorite: bool = False
    wear_count: int = 0
    style_bias: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    id: int | None = None


@dataclass
class Outfit:
    """Pure domain model for an outfit."""
    name: str
    occasion: str
    season: Season = Season.ALL_SEASON
    formality: int = 1
    score: float = 0.0
    is_packing: bool = False
    packing_days: int | None = None
    composed_image_path: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    id: int | None = None


@dataclass
class OutfitGarmentLink:
    """Pure domain model for outfit-garment link."""
    outfit_id: int
    garment_id: int
    position: int = 0
    id: int | None = None


@dataclass
class StyleRule:
    """Pure domain model for a style rule."""
    name: str
    rule_type: str  # color_harmony, formality_match, pattern_balance, seasonal, occasion_match
    weight: float = 1.0
    is_active: bool = True
    parameters: dict = field(default_factory=dict)
    description: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    id: int | None = None


@dataclass
class UserFeedback:
    """Pure domain model for user feedback."""
    garment_id: int | None = None
    outfit_id: int | None = None
    rating: int = 0  # -1, 0, 1
    feedback_type: str = ""  # "garment", "outfit", "outfit_garment"
    context: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: int | None = None
