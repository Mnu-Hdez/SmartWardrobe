# Smart Wardrobe - Database Models
# SQLModel models with dual image paths

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String, Text
from sqlmodel import JSON, Column, Field, Relationship, SQLModel


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


class Garment(SQLModel, table=True):
    """Garment model with dual image storage (raw + processed mask)"""

    __tablename__ = "garment"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(200), nullable=False))
    brand: str | None = Field(default=None, sa_column=Column(String(100)))
    type: str = Field(sa_column=Column(String(50), nullable=False))  # Use GarmentType values
    season: str = Field(default=Season.ALL_SEASON, sa_column=Column(String(50), nullable=False))
    size: str | None = Field(default=None, sa_column=Column(String(20)))
    material: str | None = Field(default=None, sa_column=Column(String(100)))
    color_name: str = Field(sa_column=Column(String(50), nullable=False))
    color_hex: str = Field(sa_column=Column(String(7), nullable=False))  # #RRGGBB
    pattern: str = Field(default=Pattern.SOLID, sa_column=Column(String(50), nullable=False))
    formality: int = Field(default=1, sa_column=Column(Integer, nullable=False))  # 1-5
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))

    # Dual image storage paths
    raw_image_path: str = Field(sa_column=Column(String(500), nullable=False))
    processed_image_path: str = Field(sa_column=Column(String(500), nullable=False))

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False)
    )

    # Relationships
    outfit_items: list["OutfitItem"] = Relationship(back_populates="garment")

    def __repr__(self):
        return f"<Garment(id={self.id}, name='{self.name}', type='{self.type}')>"


class Outfit(SQLModel, table=True):
    """Outfit model"""

    __tablename__ = "outfit"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    name: str | None = Field(default=None, sa_column=Column(String(200)))
    occasion: str = Field(sa_column=Column(String(50), nullable=False))
    season: str = Field(sa_column=Column(String(50), nullable=False))
    score: float | None = Field(default=None, sa_column=Column(Integer))
    score_breakdown: dict | None = Field(default=None, sa_column=Column(JSON))
    ai_tips: list[str] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False)
    )

    # Relationships
    items: list["OutfitItem"] = Relationship(back_populates="outfit")

    def __repr__(self):
        return f"<Outfit(id={self.id}, occasion='{self.occasion}', score={self.score})>"


class OutfitItem(SQLModel, table=True):
    """Outfit-Garment junction with position (layer order)"""

    __tablename__ = "outfit_item"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    outfit_id: int = Field(foreign_key="outfit.id", nullable=False)
    garment_id: int = Field(foreign_key="garment.id", nullable=False)
    position: int = Field(sa_column=Column(Integer, nullable=False))  # Layer order

    # Relationships
    outfit: Outfit | None = Relationship(back_populates="items")
    garment: Garment | None = Relationship(back_populates="outfit_items")


# Backward compatibility alias for tests
OutfitGarmentLink = OutfitItem


class StyleRuleType(str, Enum):
    COLOR_HARMONY = "color_harmony"
    OCCASION_MATCH = "occasion_match"
    SEASON_MATCH = "season_match"
    FORMALITY_CAP = "formality_cap"


class StyleRule(SQLModel, table=True):
    """Style rules for outfit recommendations"""

    __tablename__ = "style_rule"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(200), nullable=False))
    rule_type: str = Field(sa_column=Column(String(50), nullable=False))
    parameters: str = Field(sa_column=Column(Text, nullable=False))  # JSON string
    weight: float = Field(default=1.0, sa_column=Column(Integer, nullable=False))
    is_active: bool = Field(default=True, sa_column=Column(Integer, nullable=False))
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False)
    )

    def __repr__(self):
        return f"<StyleRule(id={self.id}, name='{self.name}', type='{self.rule_type}')>"


class UserFeedback(SQLModel, table=True):
    """User feedback on outfits and garments"""

    __tablename__ = "user_feedback"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    garment_id: int | None = Field(default=None, foreign_key="garment.id")
    outfit_id: int | None = Field(default=None, foreign_key="outfit.id")
    rating: int = Field(sa_column=Column(Integer, nullable=False))  # -1, 0, 1
    feedback_type: str = Field(sa_column=Column(String(50), nullable=False))  # "outfit", "garment"
    context: str | None = Field(default=None, sa_column=Column(String(500)))
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False)
    )

    def __repr__(self):
        return f"<UserFeedback(id={self.id}, rating={self.rating}, type='{self.feedback_type}')>"
