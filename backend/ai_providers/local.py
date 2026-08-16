# Smart Wardrobe - AI Providers
# Local rules-based provider: tag suggestions + on-device image analysis.
# No API key required. Used directly when AI_PROVIDER=local, and as the
# fallback for NIM/Gemini when their key is missing or a call fails.

import logging

from PIL import Image

logger = logging.getLogger(__name__)


class LocalRulesProvider:
    """Local, no-API-key AI provider: tag suggestions + on-device image
    analysis (SAM+CLIP+color, see backend.vision.ingestion_pipeline)."""

    def __init__(self):
        self.name = "local"

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
        """Heuristic tag suggestions used when NIM/Gemini are unavailable or as their fallback."""
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
        """On-device analysis via the local SAM+CLIP vision pipeline (type,
        pattern, formality, dominant color) - no API key required. Falls
        back to color-only (colorthief) if the vision pipeline can't run
        (weights not downloaded yet, missing torch/segment-anything, out of
        memory on the Pi, etc.), so auto-fill still gives the user
        *something* to review even when the heavier models aren't available.
        Every field returned here stays editable in the form before the
        person saves the garment, same as the NIM/Gemini providers."""
        try:
            from io import BytesIO

            from backend.vision.ingestion_pipeline import IngestionPipeline

            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            return IngestionPipeline().analyze_image(image)
        except Exception as e:
            logger.warning(f"Local vision pipeline unavailable ({e}), falling back to color-only analysis")
            return self._analyze_image_color_only(image_bytes)

    def _analyze_image_color_only(self, image_bytes: bytes) -> dict:
        """Color-only fallback: extract the dominant color from the photo
        via colorthief (a lighter dependency than the full SAM+CLIP
        pipeline) so auto-fill still gives the user *something* to review
        even when the vision pipeline can't run. Cannot guess name/type/
        material/pattern without it, so those stay null and the user fills
        them manually."""
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
