import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from backend.core.config import get_settings
from backend.models.garment import Garment, Outfit, OutfitGarmentLink, StyleRule
from backend.repositories import GarmentRepository, StyleRuleRepository, UserFeedbackRepository


@dataclass
class StyleScore:
    """Detailed style score breakdown."""

    color_harmony: float = 0.0
    formality_match: float = 0.0
    pattern_balance: float = 0.0
    seasonal: float = 0.0
    occasion: float = 0.0
    user_bias: float = 0.0
    total: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "color_harmony": self.color_harmony,
            "formality_match": self.formality_match,
            "pattern_balance": self.pattern_balance,
            "seasonal": self.seasonal,
            "occasion": self.occasion,
            "user_bias": self.user_bias,
            "total": self.total,
            "details": self.details,
        }


class StyleEngine:
    """Engine for scoring outfits based on style rules."""

    def __init__(self, session: Session):
        self.session = session
        self.settings = get_settings()
        self.garment_repo = GarmentRepository(session)
        self.rule_repo = StyleRuleRepository(session)
        self.feedback_repo = UserFeedbackRepository(session)
        self._rules_cache = None

    def _get_rules(self) -> list[StyleRule]:
        """Get active style rules, cached."""
        if self._rules_cache is None:
            self._rules_cache = self.rule_repo.get_all(active_only=True)
        return self._rules_cache

    def _get_garments(self, outfit: Outfit) -> list[Garment]:
        """Get garments for an outfit from DB."""
        links = self.session.exec(
            select(OutfitGarmentLink).where(OutfitGarmentLink.outfit_id == outfit.id)
        ).all()
        garment_ids = [link.garment_id for link in links]
        if not garment_ids:
            return []
        return self.garment_repo.get_by_ids(garment_ids)

    def score_outfit(
        self, outfit: Outfit, occasion: str = "casual", season: str = "all_season"
    ) -> StyleScore:
        """Score an outfit across all style dimensions."""
        garments = self._get_garments(outfit)

        if not garments:
            return StyleScore(total=0.0, details={"error": "No garments found"})

        score = StyleScore()
        details = {}

        # 1. Color Harmony
        score.color_harmony, color_details = self._score_color_harmony(garments)
        details["color_harmony"] = color_details

        # 2. Formality Match
        score.formality_match, formality_details = self._score_formality_match(garments, occasion)
        details["formality_match"] = formality_details

        # 3. Pattern Balance
        score.pattern_balance, pattern_details = self._score_pattern_balance(garments)
        details["pattern_balance"] = pattern_details

        # 4. Seasonal Appropriateness
        score.seasonal, seasonal_details = self._score_seasonal(garments, season)
        details["seasonal"] = seasonal_details

        # 5. Occasion Match
        score.occasion, occasion_details = self._score_occasion(garments, occasion)
        details["occasion"] = occasion_details

        # 6. User Bias (learned preferences)
        score.user_bias, bias_details = self._score_user_bias(garments)
        details["user_bias"] = bias_details

        # Calculate weighted total
        rules = self._get_rules()
        weights = {r.rule_type: r.weight for r in rules}

        score.total = (
            score.color_harmony * weights.get("color_harmony", 1.0)
            + score.formality_match * weights.get("formality_match", 1.0)
            + score.pattern_balance * weights.get("pattern_balance", 1.0)
            + score.seasonal * weights.get("seasonal", 1.0)
            + score.occasion * weights.get("occasion_match", 1.0)
            + score.user_bias * 1.0  # User bias always weight 1.0
        )

        # Normalize to 0-100
        max_possible = sum(
            [
                100 * weights.get("color_harmony", 1.0),
                100 * weights.get("formality_match", 1.0),
                100 * weights.get("pattern_balance", 1.0),
                100 * weights.get("seasonal", 1.0),
                100 * weights.get("occasion_match", 1.0),
                100,  # user bias
            ]
        )
        if max_possible > 0:
            score.total = min(100.0, max(0.0, (score.total / max_possible) * 100))

        score.details = details
        return score

    def _score_color_harmony(self, garments: list[Garment]) -> tuple[float, dict]:
        """Score color harmony based on color theory."""
        if len(garments) < 2:
            return 100.0, {"method": "single_item", "score": 100}

        colors = [g.color_hex for g in garments]

        # Convert to HSV for analysis
        hsv_colors = [self._hex_to_hsv(c) for c in colors]
        hues = [h for h, s, v in hsv_colors]
        saturations = [s for h, s, v in hsv_colors]
        values = [v for h, s, v in hsv_colors]

        # Calculate pairwise hue differences
        hue_diffs = []
        for i in range(len(hues)):
            for j in range(i + 1, len(hues)):
                diff = abs(hues[i] - hues[j])
                diff = min(diff, 360 - diff)  # Circular distance
                hue_diffs.append(diff)

        if not hue_diffs:
            return 50.0, {"method": "no_comparison"}

        avg_hue_diff = sum(hue_diffs) / len(hue_diffs)

        # Score based on color theory
        # Complementary (~180°): high score
        # Analogous (~30°): high score
        # Triadic (~120°): good score
        # Monochromatic (0°): good score
        # Clashing (60-150 but not special): lower score

        best_match = float("inf")
        harmony_type = "clashing"

        for diff in hue_diffs:
            # Check complementary (180°)
            comp_score = abs(diff - 180)
            # Check analogous (30°)
            ana_score = abs(diff - 30)
            # Check triadic (120°)
            tri_score = abs(diff - 120)
            # Check monochromatic (0°)
            mono_score = diff

            min_score = min(comp_score, ana_score, tri_score, mono_score)
            if min_score < best_match:
                best_match = min_score
                if min_score == comp_score:
                    harmony_type = "complementary"
                elif min_score == ana_score:
                    harmony_type = "analogous"
                elif min_score == tri_score:
                    harmony_type = "triadic"
                else:
                    harmony_type = "monochromatic"

        # Convert to 0-100 score (0° max deviation)
        if best_match <= 15:
            harmony_score = 100
        elif best_match <= 30:
            harmony_score = 85
        elif best_match <= 45:
            harmony_score = 70
        elif best_match <= 60:
            harmony_score = 55
        else:
            harmony_score = 40

        # Bonus for consistent saturation/value
        sat_std = self._std(saturations)
        val_std = self._std(values)

        if sat_std < 30 and val_std < 30:
            harmony_score = min(100, harmony_score + 10)

        return harmony_score, {
            "type": harmony_type,
            "avg_hue_diff": round(avg_hue_diff, 1),
            "best_match_deviation": round(best_match, 1),
            "saturation_consistency": round(100 - sat_std, 1),
            "value_consistency": round(100 - val_std, 1),
        }

    def _score_formality_match(self, garments: list[Garment], occasion: str) -> tuple[float, dict]:
        """Score formality consistency and occasion appropriateness."""
        if not garments:
            return 0.0, {}

        formalities = [g.formality for g in garments]
        avg_formality = sum(formalities) / len(formalities)
        formality_spread = max(formalities) - min(formalities)

        # Occasion target formalities
        occasion_targets = {
            "casual": 1,
            "date": 2,
            "work": 3,
            "business": 3,
            "party": 3,
            "formal": 4,
            "wedding": 4,
            "black_tie": 5,
        }

        target = occasion_targets.get(occasion.lower(), 2)

        # Score based on spread (consistency) and distance from target
        spread_score = max(0, 100 - formality_spread * 20)  # Penalize spread > 1
        target_score = max(0, 100 - abs(avg_formality - target) * 20)

        combined = (spread_score + target_score) / 2

        return combined, {
            "avg_formality": round(avg_formality, 1),
            "target_formality": target,
            "spread": formality_spread,
            "spread_score": spread_score,
            "target_score": target_score,
        }

    def _score_pattern_balance(self, garments: list[Garment]) -> tuple[float, dict]:
        """Score pattern balance - avoid too many competing patterns."""
        if not garments:
            return 100.0, {}

        patterns = [g.pattern for g in garments]
        non_solid = [p for p in patterns if p != "solid"]

        num_patterns = len(non_solid)

        if num_patterns == 0:
            return 80.0, {"type": "all_solid", "count": 0}  # Solid is safe but boring
        elif num_patterns == 1:
            return 100.0, {"type": "one_pattern", "pattern": non_solid[0]}  # Perfect accent
        elif num_patterns == 2:
            # Check if patterns are different types
            if non_solid[0] != non_solid[1]:
                return 85.0, {"type": "two_different", "patterns": non_solid}
            else:
                return 60.0, {"type": "two_same", "pattern": non_solid[0]}  # Same pattern twice
        elif num_patterns == 3:
            return 40.0, {"type": "three_patterns", "patterns": non_solid}
        else:
            return 20.0, {"type": "too_many", "count": num_patterns}

    def _score_seasonal(self, garments: list[Garment], season: str) -> tuple[float, dict]:
        """Score seasonal appropriateness."""
        if season == "all_season" or not garments:
            return 100.0, {"season": season, "match": "any"}

        matches = sum(1 for g in garments if g.season == season or g.season == "all_season")
        total = len(garments)

        score = (matches / total) * 100

        return score, {
            "season": season,
            "matching_items": matches,
            "total_items": total,
            "match_percentage": round(score, 1),
        }

    def _score_occasion(self, garments: list[Garment], occasion: str) -> tuple[float, dict]:
        """Score occasion appropriateness based on garment types and formality."""
        if not garments:
            return 50.0, {}

        # Define expected garment types for occasions
        occasion_types = {
            "casual": ["top", "bottom", "shoes", "outerwear"],
            "work": ["top", "bottom", "shoes", "outerwear"],
            "business": ["top", "bottom", "shoes", "outerwear"],
            "formal": ["top", "bottom", "shoes", "outerwear", "accessory"],
            "party": ["top", "bottom", "shoes", "accessory", "outerwear"],
            "wedding": ["top", "bottom", "shoes", "accessory", "outerwear"],
            "date": ["top", "bottom", "shoes", "outerwear"],
            "travel": ["top", "bottom", "shoes", "outerwear"],
        }

        expected = occasion_types.get(occasion.lower(), ["top", "bottom", "shoes"])
        present_types = set(g.type for g in garments)

        # Check coverage
        coverage = sum(1 for t in expected if t in present_types) / len(expected)

        # Check for inappropriate items (e.g., sneakers at black tie)
        inappropriate = 0
        for g in garments:
            if occasion.lower() in ["formal", "wedding", "black_tie"] and g.type == "shoes":
                if g.formality < 3:
                    inappropriate += 1

        score = coverage * 100 - inappropriate * 15
        return max(0, min(100, score)), {
            "occasion": occasion,
            "coverage": round(coverage * 100, 1),
            "expected_types": expected,
            "present_types": list(present_types),
            "inappropriate_count": inappropriate,
        }

    def _score_user_bias(self, garments: list[Garment]) -> tuple[float, dict]:
        """Score based on learned user preferences."""
        if not garments:
            return 0.0, {}

        biases = [g.style_bias for g in garments if g.style_bias != 0.0]

        if not biases:
            return 0.0, {"count": 0, "avg_bias": 0.0}

        avg_bias = sum(biases) / len(biases)
        # Convert -1..1 to 0..100
        score = (avg_bias + 1) * 50

        return score, {
            "garments_with_bias": len(biases),
            "avg_bias": round(avg_bias, 3),
            "bias_score": round(score, 1),
        }

    def _hex_to_hsv(self, hex_color: str) -> tuple[float, float, float]:
        """Convert hex color to HSV."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0

        max_c = max(r, g, b)
        min_c = min(r, g, b)
        delta = max_c - min_c

        # Value
        v = max_c

        # Saturation
        s = 0 if max_c == 0 else delta / max_c

        # Hue
        h = 0
        if delta != 0:
            if max_c == r:
                h = 60 * ((g - b) / delta % 6)
            elif max_c == g:
                h = 60 * ((b - r) / delta + 2)
            else:
                h = 60 * ((r - g) / delta + 4)

        return h, s * 100, v * 100

    def _std(self, values: list[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))

    def get_rule_weights(self) -> dict[str, float]:
        """Get current rule weights for transparency."""
        rules = self._get_rules()
        return {r.rule_type: r.weight for r in rules}

    def update_rule_weight(self, rule_type: str, weight: float) -> bool:
        """Update a rule's weight."""
        rules = self._get_rules()
        for r in rules:
            if r.rule_type == rule_type:
                r.weight = weight
                r.updated_at = datetime.utcnow()
                self.session.add(r)
                self.session.commit()
                self._rules_cache = None  # Invalidate cache
                return True
        return False
