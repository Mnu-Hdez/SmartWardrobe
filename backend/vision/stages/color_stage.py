# backend/vision/stages/color_stage.py
"""Color extraction stage — wraps color extractor."""

from typing import Any

from PIL import Image

from backend.vision.color_extractor import ColorExtractor, extract_colors_from_image


class ColorStage:
    """Color extraction stage — wraps color extractor."""

    def __init__(self):
        self.color_extractor = ColorExtractor()

    def process(self, image: "Image.Image", context: dict[str, Any]) -> dict[str, Any]:
        """Run color extraction, update context with color info."""
        # Default color info
        color_info = {
            "dominant_color_hex": "#000000",
            "dominant_color_name": "black",
            "palette": [],
        }

        try:
            # Use masked image if available
            masked_image_path = context.get("masked_image_path")
            mask_path = context.get("mask_path")

            color_info = extract_colors_from_image(masked_image_path, mask_path)
            print(
                f"Dominant color: {color_info['dominant_color_name']} ({color_info['dominant_color_hex']})"
            )
        except Exception as e:
            print(f"Color extraction failed: {e}")

        context["color_info"] = color_info
        return context


def create_color_stage() -> "ColorStage":
    """Factory function."""
    return ColorStage()
