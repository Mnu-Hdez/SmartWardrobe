from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models.outfit import Outfit, OutfitGarmentLink
    from backend.models.style_rule import StyleRule
    from backend.models.user_feedback import UserFeedback


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


class Garment(SQLModel, table=True):
    __tablename__ = "garments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    type: GarmentType = Field(index=True)
    color_hex: str = Field(max_length=7)  # #RRGGBB
    color_name: str = Field(max_length=50)
    secondary_color_hex: Optional[str] = Field(default=None, max_length=7)
    pattern: PatternType = Field(default=PatternType.SOLID)
    formality: FormalityLevel = Field(default=FormalityLevel.CASUAL)
    season: Season = Field(default=Season.ALL_SEASON)
    brand: Optional[str] = Field(default=None, max_length=100)
    size: Optional[str] = Field(default=None, max_length=20)
    material: Optional[str] = Field(default=None, max_length=100)
    
    # Image paths
    original_image_path: str = Field(max_length=500)
    processed_image_path: str = Field(max_length=500)
    mask_image_path: Optional[str] = Field(default=None, max_length=500)
    
    # CLIP embeddings (stored as JSON string of float array)
    clip_embedding: Optional[str] = Field(default=None)  # JSON string of float array
    
    # AI analysis metadata
    confidence_scores: Optional[str] = Field(default=None)  # JSON string
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Bias learning from feedback
    style_bias: float = Field(default=0.0)  # -1 to 1, learned from feedback
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    outfit_links: List["OutfitGarmentLink"] = Relationship(back_populates="garment")
    feedbacks: List["UserFeedback"] = Relationship(back_populates="garment")


class Outfit(SQLModel, table=True):
    __tablename__ = "outfits"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    occasion: str = Field(max_length=50, index=True)  # casual, work, party, wedding, etc.
    season: Season = Field(default=Season.ALL_SEASON, index=True)
    formality: FormalityLevel = Field(default=FormalityLevel.CASUAL, index=True)
    score: float = Field(default=0.0)  # 0-100 score from composer
    
    # Image
    composed_image_path: Optional[str] = Field(default=None, max_length=500)
    
    # Metadata
    is_packing: bool = Field(default=False)
    packing_days: Optional[int] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    garment_links: List["OutfitGarmentLink"] = Relationship(back_populates="outfit")
    feedbacks: List["UserFeedback"] = Relationship(back_populates="outfit")


class OutfitGarmentLink(SQLModel, table=True):
    __tablename__ = "outfit_garment_links"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    outfit_id: int = Field(foreign_key="outfits.id", index=True)
    garment_id: int = Field(foreign_key="garments.id", index=True)
    position: int = Field(default=0)  # layer order
    
    # Relationships
    outfit: "Outfit" = Relationship(back_populates="garment_links")
    garment: "Garment" = Relationship(back_populates="outfit_links")


class StyleRule(SQLModel, table=True):
    __tablename__ = "style_rules"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True)
    description: str
    rule_type: str = Field(max_length=50)  # color_harmony, formality_match, pattern_balance, seasonal
    weight: float = Field(default=1.0)  # weight in scoring
    is_active: bool = Field(default=True)
    parameters: str = Field(default="{}")  # JSON string of rule parameters
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserFeedback(SQLModel, table=True):
    __tablename__ = "user_feedbacks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    garment_id: Optional[int] = Field(default=None, foreign_key="garments.id", index=True)
    outfit_id: Optional[int] = Field(default=None, foreign_key="outfits.id", index=True)
    rating: int = Field(ge=-1, le=1)  # -1 (dislike), 0 (neutral), 1 (like)
    feedback_type: str = Field(max_length=20)  # "garment", "outfit", "outfit_garment"
    context: Optional[str] = Field(default=None, max_length=500)  # occasion, context notes
    
    # Relationships
    garment: Optional["Garment"] = Relationship(back_populates="feedbacks")
    outfit: Optional["Outfit"] = Relationship(back_populates="feedbacks")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)