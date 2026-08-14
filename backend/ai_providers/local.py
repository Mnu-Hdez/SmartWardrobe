# Smart Wardrobe - AI Providers
# Local rules-based provider

from typing import Any

from backend.models.garment import Garment, Outfit
from backend.models.schemas import OutfitRecommendationRequest, PackingPlanRequest


class LocalRulesProvider:
    """Local rules-based AI provider for outfit recommendations"""

    def __init__(self):
        self.name = "local"

    def recommend_outfits(
        self, request: OutfitRecommendationRequest, garments: list[Garment]
    ) -> list[Outfit]:
        """Generate outfit recommendations using local rules"""
        # Filter by occasion suitability
        filtered = self._filter_by_occasion(garments, request.occasion, request.formality or 0)

        if len(filtered) < 2:
            return []

        # Generate combinations
        outfits = self._generate_combinations(
            filtered, request.occasion, request.season, request.top_n
        )

        # Score and sort
        for outfit in outfits:
            outfit.score = self._score_outfit(outfit, request.occasion)
            outfit.score_breakdown = self._get_score_breakdown(outfit)
            outfit.ai_tips = self._generate_tips(outfit)

        outfits.sort(key=lambda o: o.score or 0, reverse=True)
        return outfits[: request.top_n]

    def create_packing_plan(
        self, request: PackingPlanRequest, garments: list[Garment]
    ) -> dict[str, Any]:
        """Create packing plan using local rules"""
        # Filter by season
        filtered = [g for g in garments if g.season == request.season or g.season == "all_season"]

        if not filtered:
            return {
                "outfits": [],
                "packing_list": [],
                "total_items": 0,
                "days_covered": 0,
                "mix_and_match_ratio": 0,
            }

        # Score by versatility
        scored = [(g, self._versatility_score(g)) for g in filtered]
        scored.sort(key=lambda x: x[1], reverse=True)
        selected = [g for g, _ in scored[: request.max_items]]

        # Generate daily outfits
        outfits = []
        for day in range(request.days):
            day_garments = self._select_daily_outfit(selected, request.occasion)
            outfit = Outfit(
                name=f"Day {day + 1}",
                occasion=request.occasion,
                season=request.season,
                score=self._score_outfit_from_garments(day_garments, request.occasion),
            )
            outfit.garments = day_garments  # type: ignore
            outfits.append(outfit)

        packing_list = [
            {"garment": g, "versatility_score": v, "days_covered": 1}
            for g, v in scored[: request.max_items]
        ]

        return {
            "outfits": outfits,
            "packing_list": packing_list,
            "total_items": len(selected),
            "days_covered": request.days,
            "mix_and_match_ratio": len(outfits) / max(1, len(selected)),
        }

    def _filter_by_occasion(
        self, garments: list[Garment], occasion: str, formality: int = None
    ) -> list[Garment]:
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
        if formality is not None:
            min_form = max(min_form, formality)
            max_form = min(max_form, formality)

        return [g for g in garments if min_form <= g.formality <= max_form]

    def _generate_combinations(
        self, garments: list[Garment], occasion: str, season: str, top_n: int
    ) -> list[Outfit]:
        import random

        by_type = {}
        for g in garments:
            by_type.setdefault(g.type, []).append(g)

        outfits = []
        attempts = 0
        max_attempts = top_n * 10

        while len(outfits) < top_n and attempts < max_attempts:
            attempts += 1
            outfit_garments = []

            if "top" in by_type and by_type["top"]:
                outfit_garments.append(random.choice(by_type["top"]))
            elif "dress" in by_type and by_type["dress"]:
                outfit_garments.append(random.choice(by_type["dress"]))
            else:
                continue

            if outfit_garments[-1].type == "top" and "bottom" in by_type and by_type["bottom"]:
                outfit_garments.append(random.choice(by_type["bottom"]))

            if "outerwear" in by_type and by_type["outerwear"] and random.random() < 0.3:
                outfit_garments.append(random.choice(by_type["outerwear"]))

            if "shoes" in by_type and by_type["shoes"] and random.random() < 0.5:
                outfit_garments.append(random.choice(by_type["shoes"]))

            if "accessory" in by_type and by_type["accessory"] and random.random() < 0.3:
                outfit_garments.append(random.choice(by_type["accessory"]))

            if len(outfit_garments) >= 2:
                outfit = Outfit(name=f"{occasion.title()} Outfit", occasion=occasion, season=season)
                outfit.garments = outfit_garments  # type: ignore
                outfits.append(outfit)

        return outfits

    def _score_outfit(self, outfit: Outfit, occasion: str) -> float:
        return self._score_outfit_from_garments(outfit.garments, occasion)  # type: ignore

    def _score_outfit_from_garments(self, garments: list[Garment], occasion: str) -> float:
        if not garments:
            return 0.0

        occasion_formality = {
            "casual": 1,
            "work": 2,
            "party": 3,
            "date": 2,
            "formal": 4,
            "wedding": 5,
            "travel": 2,
        }
        target = occasion_formality.get(occasion, 2)

        avg_formality = sum(g.formality for g in garments) / len(garments)
        formality_score = max(0, 100 - abs(avg_formality - target) * 20)

        # Color harmony (simplified)
        colors = set(g.color_name for g in garments)
        color_score = 80 if len(colors) <= 3 else 60

        # Pattern balance
        patterns = [g.pattern for g in garments if g.pattern != "solid"]
        pattern_score = 90 if len(patterns) <= 1 else (70 if len(patterns) == 2 else 50)

        return formality_score * 0.5 + color_score * 0.3 + pattern_score * 0.2

    def _get_score_breakdown(self, outfit: Outfit) -> dict[str, float]:
        return {
            "color_harmony": 75.0,
            "formality_match": 80.0,
            "pattern_balance": 70.0,
            "seasonal": 85.0,
        }

    def _generate_tips(self, outfit: Outfit) -> list[str]:
        tips = []
        garments = outfit.garments  # type: ignore

        colors = set(g.color_name for g in garments)
        if len(colors) <= 2:
            tips.append("Monochromatic look creates a sleek, elongated silhouette.")

        patterns = [g.pattern for g in garments if g.pattern != "solid"]
        if len(patterns) > 1:
            tips.append("Mix patterns carefully - vary scale (large + small) for balance.")

        formalities = [g.formality for g in garments]
        if max(formalities) - min(formalities) > 2:
            tips.append("Balance formal and casual pieces - one statement piece is enough.")

        return tips if tips else ["Great combination! This outfit works well together."]

    def _versatility_score(self, garment: Garment) -> float:
        score = 0.5
        neutral_colors = {"black", "white", "gray", "grey", "navy", "beige", "khaki"}
        if garment.color_name.lower() in neutral_colors:
            score += 0.3
        versatile_types = {"top", "bottom", "outerwear"}
        if garment.type in versatile_types:
            score += 0.2
        return min(1.0, score)

    def suggest_tags(
        self,
        name: str,
        garment_type: str,
        color_name: str | None = None,
        material: str | None = None,
        pattern: str | None = None,
        brand: str | None = None,
        season: str | None = None,
        existing_tags: list[str] | None = None,
    ) -> list[str]:
        """Heuristic tag suggestions used when NIM is unavailable or as its fallback."""
        existing = {t.lower() for t in (existing_tags or [])}
        suggestions: list[str] = []

        def add(tag: str):
            tag = tag.strip().lower()
            if tag and tag not in existing and tag not in suggestions:
                suggestions.append(tag)

        if color_name:
            add(color_name)
        if material:
            add(material)
        if garment_type:
            add(garment_type)
        if pattern and pattern != "solid":
            add(pattern)
        if season and season != "all_season":
            add(season)
        if brand:
            add(brand)

        neutral_colors = {"black", "white", "gray", "grey", "navy", "beige", "khaki"}
        if color_name and color_name.lower() in neutral_colors:
            add("versatile")
            add("neutral")

        casual_materials = {"denim", "cotton"}
        formal_materials = {"silk", "wool", "cashmere"}
        if material and material.lower() in casual_materials:
            add("casual")
        if material and material.lower() in formal_materials:
            add("smart")

        return suggestions[:8]

    def analyze_image(self, image_bytes: bytes, mime_type: str) -> dict:
        """No-AI fallback: extract the dominant color from the photo via
        colorthief (already a project dependency) so auto-fill still gives
        the user *something* to review even with AI_PROVIDER=local. Cannot
        guess name/type/material/pattern without a vision model, so those
        stay null and the user fills them manually."""
        empty = {
            "name": None, "type": None, "color_name": None, "color_hex": None,
            "material": None, "pattern": None, "formality": None, "tags": [],
        }
        try:
            from io import BytesIO

            from colorthief import ColorThief

            color_thief = ColorThief(BytesIO(image_bytes))
            r, g, b = color_thief.get_color(quality=1)
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            result = dict(empty)
            result["color_hex"] = hex_color
            result["color_name"] = self._nearest_color_name(r, g, b)
            return result
        except Exception:
            return empty

    def _nearest_color_name(self, r: int, g: int, b: int) -> str:
        palette = {
            "Black": (0, 0, 0), "White": (255, 255, 255), "Gray": (128, 128, 128),
            "Navy": (0, 0, 128), "Blue": (30, 60, 200), "Light Blue": (120, 170, 230),
            "Red": (200, 30, 30), "Maroon": (128, 0, 0), "Pink": (230, 130, 170),
            "Orange": (230, 120, 30), "Yellow": (230, 210, 50), "Beige": (220, 200, 170),
            "Brown": (120, 80, 50), "Green": (40, 130, 60), "Olive": (110, 120, 40),
            "Purple": (120, 50, 150), "Khaki": (180, 170, 120),
        }
        best_name, best_dist = "Gray", float("inf")
        for name, (pr, pg, pb) in palette.items():
            dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
            if dist < best_dist:
                best_dist, best_name = dist, name
        return best_name

    def _select_daily_outfit(self, garments: list[Garment], occasion: str) -> list[Garment]:
        import random

        by_type = {}
        for g in garments:
            by_type.setdefault(g.type, []).append(g)

        outfit = []
        if "top" in by_type and by_type["top"]:
            outfit.append(random.choice(by_type["top"]))
        elif "dress" in by_type and by_type["dress"]:
            outfit.append(random.choice(by_type["dress"]))

        if outfit and outfit[-1].type == "top" and "bottom" in by_type and by_type["bottom"]:
            outfit.append(random.choice(by_type["bottom"]))

        if "outerwear" in by_type and by_type["outerwear"] and random.random() < 0.3:
            outfit.append(random.choice(by_type["outerwear"]))

        if "shoes" in by_type and by_type["shoes"] and random.random() < 0.5:
            outfit.append(random.choice(by_type["shoes"]))

        if "accessory" in by_type and by_type["accessory"] and random.random() < 0.3:
            outfit.append(random.choice(by_type["accessory"]))

        return outfit
