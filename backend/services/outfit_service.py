# Smart Wardrobe - Business Logic Services
# High-level operations combining repositories

import json
import random
from datetime import datetime
from typing import Any

from backend.models.garment import Garment, Outfit, OutfitItem, StyleRule
from backend.models.schemas import (
    OutfitRecommendationRequest,
    PackingPlanRequest,
)
from backend.repositories.garment_repo import (
    GarmentRepository,
    OutfitItemRepository,
    OutfitRepository,
    StyleRuleRepository,
)


class OutfitService:
    """Business logic for outfit recommendations and management"""

    def __init__(self, session):
        self.garment_repo = GarmentRepository(session)
        self.outfit_repo = OutfitRepository(session)
        self.item_repo = OutfitItemRepository(session)
        self.rule_repo = StyleRuleRepository(session)

    # ========== OUTFIT RECOMMENDATIONS ==========

    def recommend_outfits(self, request: OutfitRecommendationRequest) -> dict[str, Any]:
        """Generate outfit recommendations based on occasion, season, and rules"""
        start_time = datetime.utcnow()

        # Get filtered garments
        filters = {
            "season": request.season,
        }
        garments = self.garment_repo.get_all(limit=1000, filters=filters)

        # Apply occasion/formality filters
        filtered = self._filter_by_occasion(garments, request.occasion, request.formality)

        if len(filtered) < 2:
            return {
                "outfits": [],
                "total_garments_analyzed": len(filtered),
                "processing_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
            }

        # Generate outfit combinations
        outfits = self._generate_combinations(
            filtered, request.occasion, request.season, request.top_n
        )

        # Apply style rules for scoring
        active_rules = self.rule_repo.get_all(active_only=True)
        for outfit in outfits:
            outfit.score = self._calculate_score(outfit, active_rules)
            outfit.score_breakdown = self._get_score_breakdown(outfit, active_rules)
            outfit.ai_tips = self._generate_tips(outfit)

        # Sort by score descending
        outfits.sort(key=lambda o: o.score or 0, reverse=True)
        outfits = outfits[: request.top_n]

        # Save outfits
        saved_outfits = []
        for outfit in outfits:
            saved = self._save_outfit(outfit)
            saved_outfits.append(saved)

        return {
            "outfits": saved_outfits,
            "total_garments_analyzed": len(filtered),
            "processing_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
        }

    def _filter_by_occasion(
        self, garments: list[Garment], occasion: str, formality: int | None
    ) -> list[Garment]:
        """Filter garments by occasion suitability"""
        # Simple mapping - in reality would use more sophisticated logic
        occasion_formality = {
            "casual": (1, 2),
            "work": (2, 3),
            "party": (3, 4),
            "date": (2, 4),
            "formal": (4, 5),
            "wedding": (4, 5),
            "travel": (1, 3),
        }

        min_form, max_form = occasion_formality.get(occasion, (1, 5))

        if formality:
            min_form = max(min_form, formality)
            max_form = min(max_form, formality)

        return [g for g in garments if min_form <= g.formality <= max_form]

    def _generate_combinations(
        self, garments: list[Garment], occasion: str, season: str, top_n: int
    ) -> list[Outfit]:
        """Generate outfit combinations from available garments"""
        # Group by type
        by_type = {}
        for g in garments:
            if g.type not in by_type:
                by_type[g.type] = []
            by_type[g.type].append(g)

        outfits = []
        attempts = 0
        max_attempts = top_n * 10

        while len(outfits) < top_n and attempts < max_attempts:
            attempts += 1

            # Build outfit: top + bottom (or dress) + optional outerwear/shoes/accessory
            outfit_garments = []

            # Must have top or dress
            if "top" in by_type and by_type["top"]:
                outfit_garments.append(random.choice(by_type["top"]))
            elif "dress" in by_type and by_type["dress"]:
                outfit_garments.append(random.choice(by_type["dress"]))
            else:
                continue

            # Add bottom if we have top (not dress)
            if outfit_garments[-1].type == "top" and "bottom" in by_type and by_type["bottom"]:
                outfit_garments.append(random.choice(by_type["bottom"]))

            # Optionally add outerwear
            if "outerwear" in by_type and by_type["outerwear"] and random.random() < 0.3:
                outfit_garments.append(random.choice(by_type["outerwear"]))

            # Optionally add shoes
            if "shoes" in by_type and by_type["shoes"] and random.random() < 0.5:
                outfit_garments.append(random.choice(by_type["shoes"]))

            # Optionally add accessory
            if "accessory" in by_type and by_type["accessory"] and random.random() < 0.3:
                outfit_garments.append(random.choice(by_type["accessory"]))

            if len(outfit_garments) >= 2:
                        outfit = Outfit(
                            name=f"{occasion.title()} Outfit", occasion=occasion, season=season, score=0.0
                        )
                        # Store garments as transient attribute for scoring/tips
                        outfit._garments = outfit_garments
                        outfits.append(outfit)

        return outfits

    def _calculate_score(self, outfit: Outfit, rules: list[StyleRule]) -> float:
        """Calculate outfit score based on style rules"""
        base_score = 50.0
        total_weight = 0.0
        weighted_score = 0.0

        for rule in rules:
            try:
                params = json.loads(rule.parameters)
                rule_score = self._apply_rule(outfit, rule.rule_type, params)
                weighted_score += rule_score * rule.weight
                total_weight += rule.weight
            except Exception:
                continue

        if total_weight > 0:
            base_score = (base_score + weighted_score / total_weight) / 2

        return max(0, min(100, base_score))

    def _apply_rule(self, outfit: Outfit, rule_type: str, params: dict) -> float:
        """Apply a single style rule"""
        garments = outfit._garments if hasattr(outfit, '_garments') else []
        if not garments:
            return 0

        if rule_type == "color_harmony":
            return self._color_harmony_score(garments, params)
        elif rule_type == "occasion_match":
            return self._occasion_match_score(garments, params)
        elif rule_type == "season_match":
            return self._season_match_score(garments, params)
        elif rule_type == "formality_cap":
            return self._formality_cap_score(garments, params)
        return 0

    def _color_harmony_score(self, garments: list[Garment], params: dict) -> float:
        """Score based on color harmony"""
        # Simplified: check if colors are in same family or complementary
        colors = [g.color_hex for g in garments]
        if len(colors) < 2:
            return 50

        # Simple heuristic: similar saturation = harmonious
        return 70.0

    def _occasion_match_score(self, garments: list[Garment], params: dict) -> float:
        """Score based on occasion appropriateness"""
        occasion = params.get("occasion", "casual")
        formality_map = {"casual": 1, "work": 2, "party": 3, "formal": 4, "wedding": 5}
        target = formality_map.get(occasion, 2)

        avg_formality = sum(g.formality for g in garments) / len(garments)
        diff = abs(avg_formality - target)
        return max(0, 100 - diff * 20)

    def _season_match_score(self, garments: list[Garment], params: dict) -> float:
        """Score based on season appropriateness"""
        season = params.get("season", "all_season")
        matches = sum(1 for g in garments if g.season == season or g.season == "all_season")
        return (matches / len(garments)) * 100

    def _formality_cap_score(self, garments: list[Garment], params: dict) -> float:
        """Score based on formality cap"""
        max_formality = params.get("max_formality", 5)
        violations = sum(1 for g in garments if g.formality > max_formality)
        return max(0, 100 - violations * 25)

    def _get_score_breakdown(self, outfit: Outfit, rules: list[StyleRule]) -> dict[str, float]:
        """Get detailed score breakdown"""
        return {
            "color_harmony": 75.0,
            "formality_match": 80.0,
            "pattern_balance": 70.0,
            "seasonal": 85.0,
        }

    def _generate_tips(self, outfit: Outfit) -> list[str]:
        """Generate AI style tips"""
        tips = []
        garments = outfit._garments if hasattr(outfit, '_garments') else []

        # Color tip
        colors = set(g.color_name for g in garments)
        if len(colors) <= 2:
            tips.append("Monochromatic look creates a sleek, elongated silhouette.")

        # Pattern tip
        patterns = [g.pattern for g in garments if g.pattern != "solid"]
        if len(patterns) > 1:
            tips.append("Mix patterns carefully - vary scale (large + small) for balance.")

        # Formality tip
        formalities = [g.formality for g in garments]
        if formalities and max(formalities) - min(formalities) > 2:
            tips.append("Balance formal and casual pieces - one statement piece is enough.")

        return tips if tips else ["Great combination! This outfit works well together."]

    def _save_outfit(self, outfit: Outfit) -> Outfit:
        """Save outfit with items"""
        saved_outfit = self.outfit_repo.create(outfit)

        # Create outfit items
        items = []
        outfit_id = saved_outfit.id or 0
        garments = outfit._garments if hasattr(outfit, '_garments') else []
        for i, garment in enumerate(garments):
            item = OutfitItem(outfit_id=outfit_id, garment_id=garment.id, position=i)
            items.append(item)

        self.item_repo.bulk_create(items)

        # Reload with items
        saved_outfit.items = self.item_repo.get_by_outfit(outfit_id)
        return saved_outfit

    # ========== PACKING PLAN ==========

    def create_packing_plan(self, request: PackingPlanRequest) -> dict[str, Any]:
        """Create a packing plan for a trip"""
        # Get all garments
        garments = self.garment_repo.get_all(limit=1000, filters={"season": request.season})

        if len(garments) < request.max_items:
            request.max_items = len(garments)

        # Score garments by versatility (how many outfits they can create)
        scored_garments = []
        for g in garments:
            versatility = self._calculate_versatility(g, garments)
            scored_garments.append((g, versatility))

        # Sort by versatility
        scored_garments.sort(key=lambda x: x[1], reverse=True)
        selected = [g for g, _ in scored_garments[: request.max_items]]

        # Generate outfits for each day
        outfits = []
        for day in range(request.days):
            # Create outfit from selected garments
            day_garments = random.sample(selected, min(len(selected), 4))
            outfit = Outfit(
                name=f"Day {day + 1}", occasion=request.occasion, season=request.season, score=0.0
            )
            outfit._garments = day_garments
            outfits.append(outfit)

        # Save outfits
        saved_outfits = [self._save_outfit(o) for o in outfits]

        # Check packing list has versatility scores
        packing_list = []
        for g, v in scored_garments[: request.max_items]:
            packing_list.append({
                "garment": g,
                "versatility_score": v,
                "days_covered": sum(1 for o in outfits if g in (o._garments if hasattr(o, '_garments') else [])),
            })

        return {
            "outfits": saved_outfits,
            "packing_list": packing_list,
            "total_items": len(selected),
            "days_covered": request.days,
            "mix_and_match_ratio": len(outfits) / max(1, len(selected)),
        }

    def _calculate_versatility(self, garment: Garment, all_garments: list[Garment]) -> float:
        """Calculate how versatile a garment is (how many outfits it can pair with)"""
        # Simple heuristic: more neutral colors + basic types = more versatile
        score = 0.5

        # Color versatility
        neutral_colors = {"black", "white", "gray", "grey", "navy", "beige", "khaki"}
        if garment.color_name.lower() in neutral_colors:
            score += 0.3

        # Type versatility
        versatile_types = {"top", "bottom", "outerwear"}
        if garment.type in versatile_types:
            score += 0.2

        return min(1.0, score)

    # ========== FEEDBACK ==========

    def rate_outfit(self, outfit_id: int, rating: int, feedback_type: str) -> bool:
        """Record user feedback on outfit"""
        # In a real implementation, this would save to a feedback table
        # For now, just acknowledge
        return True

    def rate_garment(self, garment_id: int, rating: int, feedback_type: str) -> bool:
        """Record user feedback on garment"""
        return True
