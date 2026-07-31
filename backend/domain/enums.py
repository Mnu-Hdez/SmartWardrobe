# backend/domain/enums.py
from enum import IntEnum, StrEnum


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


class FeedbackType(StrEnum):
    LIKE = "like"
    DISLIKE = "dislike"
    NEUTRAL = "neutral"


class AIProviderType(StrEnum):
    LOCAL = "local"
    NIM = "nim"


class StyleRuleType(StrEnum):
    COLOR_HARMONY = "color_harmony"
    FORMALITY_MATCH = "formality_match"
    PATTERN_BALANCE = "pattern_balance"
    SEASON_MATCH = "season_match"
    OCCASION_MATCH = "occasion_match"
