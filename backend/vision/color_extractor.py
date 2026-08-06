# Smart Wardrobe - Vision Pipeline
# ColorThief for dominant color extraction

import colorsys
import logging

from PIL import Image

logger = logging.getLogger(__name__)


class ColorExtractor:
    """Extract dominant color from garment image using ColorThief algorithm"""

    def __init__(self):
        pass

    def get_dominant_color(self, image: Image.Image, quality: int = 10) -> dict[str, any]:
        """
        Extract dominant color from image.
        Returns dict with hex, rgb, and color name.
        """
        # Resize for speed
        img = image.copy()
        img.thumbnail((200, 200), Image.Resampling.LANCZOS)

        # Convert to RGB
        img = img.convert("RGB")
        pixels = img.getdata()

        # Simple color quantization - count color frequencies
        color_counts = {}
        for pixel in pixels[::quality]:  # Sample every nth pixel
            # Quantize to reduce color space
            r, g, b = pixel
            r = (r // 32) * 32
            g = (g // 32) * 32
            b = (b // 32) * 32
            key = (r, g, b)
            color_counts[key] = color_counts.get(key, 0) + 1

        if not color_counts:
            return {"hex": "#666666", "rgb": (102, 102, 102), "name": "Gray"}

        # Get most frequent color
        dominant = max(color_counts, key=color_counts.get)
        r, g, b = dominant

        # Convert to hex
        hex_color = f"#{r:02x}{g:02x}{b:02x}"

        # Get color name
        name = self._rgb_to_name(r, g, b)

        return {"hex": hex_color, "rgb": (r, g, b), "name": name}

    def get_palette(self, image: Image.Image, color_count: int = 5, quality: int = 10) -> list:
        """Get color palette from image"""
        img = image.copy()
        img.thumbnail((200, 200), Image.Resampling.LANCZOS)
        img = img.convert("RGB")
        pixels = img.getdata()

        color_counts = {}
        for pixel in pixels[::quality]:
            r, g, b = pixel
            r = (r // 16) * 16
            g = (g // 16) * 16
            b = (b // 16) * 16
            key = (r, g, b)
            color_counts[key] = color_counts.get(key, 0) + 1

        # Sort by frequency
        sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)

        palette = []
        for (r, g, b), count in sorted_colors[:color_count]:
            palette.append(
                {
                    "hex": f"#{r:02x}{g:02x}{b:02x}",
                    "rgb": (r, g, b),
                    "name": self._rgb_to_name(r, g, b),
                    "percentage": count / sum(color_counts.values()),
                }
            )

        return palette

    def _rgb_to_name(self, r: int, g: int, b: int) -> str:
        """Convert RGB to closest color name"""
        # Simple color naming based on HSV
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        h = h * 360
        s = s * 100
        v = v * 100

        # Grayscale
        if s < 15:
            if v < 20:
                return "Black"
            elif v < 40:
                return "Dark Gray"
            elif v < 60:
                return "Gray"
            elif v < 80:
                return "Light Gray"
            else:
                return "White"

        # Hue-based naming
        if h < 15 or h >= 345:
            base = "Red"
        elif h < 45:
            base = "Orange"
        elif h < 70:
            base = "Yellow"
        elif h < 150:
            base = "Green"
        elif h < 210:
            base = "Cyan"
        elif h < 260:
            base = "Blue"
        elif h < 290:
            base = "Purple"
        elif h < 330:
            base = "Magenta"
        else:
            base = "Red"

        # Saturation/value modifiers
        if s < 50:
            if v > 70:
                return f"Pale {base}"
            else:
                return f"Muted {base}"
        elif v < 30:
            return f"Dark {base}"
        elif v > 80:
            return f"Bright {base}"
        else:
            return base
