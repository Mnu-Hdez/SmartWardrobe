from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

# All relationships use string references to avoid circular imports
# Related tables are defined in this same file


class GarmentType(StrEnum):
    TOP = "top"
    BOTTOM = "bottom"
    DRESS = "dress"
    OUTERWEAR = "outerwear"
    SHOES = "shoes"
    ACCESSORY = "accessory"


class Season(StrEnum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"
    ALL_SEASON = "all_season"


class FormalityLevel(IntEnum):
    CASUAL = 1
    SMART_CASUAL = 2
    BUSINESS_CASUAL = 3
    FORMAL = 4
    BLACK_TIE = 5


class PatternType(StrEnum):
    SOLID = "solid"
    STRIPED = "striped"
    CHECKERED = "checkered"
    FLORAL = "floral"
    POLKA_DOT = "polka_dot"
    GEOMETRIC = "geometric"
    ABSTRACT = "abstract"


class Garment(SQLModel, table=True):
    __tablename__ = "garments"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    type: GarmentType = Field(index=True)
    dominant_color_hex: str = Field(max_length=7)  # #RRGGBB
    color_name: str = Field(max_length=50)
    secondary_color_hex: str | None = Field(default=None, max_length=7)
    pattern: PatternType = Field(default=PatternType.SOLID)
    formality: FormalityLevel = Field(default=FormalityLevel.CASUAL)
    season: Season = Field(default=Season.ALL_SEASON)
    brand: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=20)
    material: str | None = Field(default=None, max_length=100)

    # Image paths - dual storage structure
    # raw_image_path: Original high-resolution image for display
    # processed_image_path: Segmented/processed image for AI processing
    raw_image_path: str = Field(max_length=500)
    processed_image_path: str = Field(max_length=500)
    mask_image_path: str | None = Field(default=None, max_length=500)

    # CLIP embeddings (stored as JSON string of float array)
    clip_embedding: str | None = Field(default=None)  # JSON string of float array

    # AI analysis metadata
    confidence_scores: str | None = Field(default=None)  # JSON string
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    # Bias learning from feedback
    style_bias: float = Field(default=0.0)  # -1 to 1, learned from feedback

    # Frontend fields
    is_favorite: bool = Field(default=False)
    wear_count: int = Field(default=0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    outfit_links: list["OutfitGarmentLink"] = Relationship(back_populates="garment")
    feedbacks: list["UserFeedback"] = Relationship(back_populates="garment")


class Outfit(SQLModel, table=True):
    __tablename__ = "outfits"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    occasion: str = Field(max_length=50, index=True)  # casual, work, party, wedding, etc.
    season: Season = Field(default=Season.ALL_SEASON, index=True)
    formality: FormalityLevel = Field(default=FormalityLevel.CASUAL, index=True)
    score: float = Field(default=0.0)  # 0-100 score from composer

    # Image
    composed_image_path: str | None = Field(default=None, max_length=500)

    # Metadata
    is_packing: bool = Field(default=False)
    packing_days: int | None = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    garment_links: list["OutfitGarmentLink"] = Relationship(back_populates="outfit")
    feedbacks: list["UserFeedback"] = Relationship(back_populates="outfit")


class OutfitGarmentLink(SQLModel, table=True):
    __tablename__ = "outfit_garment_links"

    id: int | None = Field(default=None, primary_key=True)
    outfit_id: int = Field(foreign_key="outfits.id", index=True)
    garment_id: int = Field(foreign_key="garments.id", index=True)
    position: int = Field(default=0)  # layer order

    # Relationships
    outfit: "Outfit" = Relationship(back_populates="garment_links")
    garment: "Garment" = Relationship(back_populates="outfit_links")


class StyleRule(SQLModel, table=True):
    __tablename__ = "style_rules"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True)
    description: str
    rule_type: str = Field(
        max_length=50
    )  # color_harmony, formality_match, pattern_balance, seasonal
    weight: float = Field(default=1.0)  # weight in scoring
    is_active: bool = Field(default=True)
    parameters: str = Field(default="{}")  # JSON string of rule parameters

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserFeedback(SQLModel, table=True):
    __tablename__ = "user_feedbacks"

    id: int | None = Field(default=None, primary_key=True)
    garment_id: int | None = Field(default=None, foreign_key="garments.id", index=True)
    outfit_id: int | None = Field(default=None, foreign_key="outfits.id", index=True)
    rating: int = Field(ge=-1, le=1)  # -1 (dislike), 0 (neutral), 1 (like)
    feedback_type: str = Field(max_length=20)  # "garment", "outfit", "outfit_garment"
    context: str | None = Field(default=None, max_length=500)  # occasion, context notes

    # Relationships
    garment: Optional["Garment"] = Relationship(back_populates="feedbacks")
    outfit: Optional["Outfit"] = Relationship(back_populates="feedbacks")

    created_at: datetime = Field(default_factory=datetime.utcnow)
