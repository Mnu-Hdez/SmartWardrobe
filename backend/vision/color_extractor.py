

import numpy as np
from colorthief import ColorThief  # type: ignore[import-untyped]
from PIL import Image


class ColorExtractor:
    """Extract dominant colors from garment images."""

    def __init__(self, quality: int = 10):
        self.quality = quality

    def extract_dominant_color(self, image_path: str, mask_path: str | None = None) -> tuple[str, str]:
        """
        Extract dominant color from image.

        Returns:
            Tuple of (hex_color, color_name)
        """
        # Use mask if available to extract only garment
        if mask_path:
            return self._extract_with_mask(image_path, mask_path)

        # Fallback to whole image
        color_thief = ColorThief(image_path)
        dominant_color = color_thief.get_color(quality=self.quality)
        hex_color = self._rgb_to_hex(dominant_color)
        color_name = self._get_color_name(dominant_color)

        return hex_color, color_name

    def extract_palette(
        self, image_path: str, color_count: int = 5, mask_path: str | None = None
    ) -> list[tuple[str, str]]:
        """Extract color palette from image."""
        if mask_path:
            return self._extract_palette_with_mask(image_path, mask_path, color_count)

        color_thief = ColorThief(image_path)
        palette = color_thief.get_palette(color_count=color_count, quality=self.quality)

        return [(self._rgb_to_hex(c), self._get_color_name(c)) for c in palette]

    def _extract_with_mask(self, image_path: str, mask_path: str) -> tuple[str, str]:
        """Extract color from masked region only."""
        image = Image.open(image_path).convert("RGB")
        mask = Image.open(mask_path).convert("L")

        # Apply mask
        image_np = np.array(image)
        mask_np = np.array(mask) > 128

        # Get pixels where mask is True
        masked_pixels = image_np[mask_np]

        if len(masked_pixels) == 0:
            # Fallback to whole image
            return self.extract_dominant_color(image_path)

        # Calculate average color of masked region
        avg_color = np.mean(masked_pixels, axis=0).astype(int)
        hex_color = self._rgb_to_hex(tuple(avg_color))
        color_name = self._get_color_name(tuple(avg_color))

        return hex_color, color_name

    def _extract_palette_with_mask(
        self, image_path: str, mask_path: str, color_count: int
    ) -> list[tuple[str, str]]:
        """Extract palette from masked region using k-means."""
        from sklearn.cluster import KMeans  # type: ignore[import-untyped]

        image = Image.open(image_path).convert("RGB")
        mask = Image.open(mask_path).convert("L")

        image_np = np.array(image)
        mask_np = np.array(mask) > 128

        masked_pixels = image_np[mask_np]

        if len(masked_pixels) < color_count:
            return self.extract_palette(image_path, color_count)

        # K-means clustering
        kmeans = KMeans(n_clusters=color_count, random_state=42, n_init=10)
        kmeans.fit(masked_pixels)

        # Get cluster centers and sort by frequency
        centers = kmeans.cluster_centers_.astype(int)
        labels = kmeans.labels_

        # Count frequency of each cluster
        unique, counts = np.unique(labels, return_counts=True)
        sorted_indices = np.argsort(-counts)

        palette = []
        for idx in sorted_indices:
            color = tuple(centers[idx])
            palette.append((self._rgb_to_hex(color), self._get_color_name(color)))

        return palette

    def _rgb_to_hex(self, rgb: tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex string."""
        return f"#{max(0, min(255, rgb[0])):02X}{max(0, min(255, rgb[1])):02X}{max(0, min(255, rgb[2])):02X}"

    def _get_color_name(self, rgb: tuple[int, int, int]) -> str:
        """Get human-readable color name from RGB."""
        # Basic color name mapping
        r, g, b = rgb

        # Check for grayscale
        if abs(r - g) < 15 and abs(g - b) < 15 and abs(r - b) < 15:
            if r < 50:
                return "black"
            elif r < 100:
                return "dark gray"
            elif r < 150:
                return "gray"
            elif r < 200:
                return "light gray"
            else:
                return "white"

        # Find dominant channel
        max_val = max(r, g, b)
        min_val = min(r, g, b)

        # Color wheel approach
        if r == max_val and g == min_val and b == min_val:
            return "red"
        elif g == max_val and r == min_val and b == min_val:
            return "green"
        elif b == max_val and r == min_val and g == min_val:
            return "blue"
        elif r == max_val and g == max_val and b == min_val:
            return "yellow"
        elif r == max_val and b == max_val and g == min_val:
            return "magenta"
        elif g == max_val and b == max_val and r == min_val:
            return "cyan"

        # More nuanced colors
        if r > g and r > b:
            if g > b * 1.5:
                return "orange" if r > 200 else "brown"
            elif b > g * 1.5:
                return "purple"
            else:
                return "red" if r > 180 else "maroon"
        elif g > r and g > b:
            if r > b * 1.5:
                return "olive"
            elif b > r * 1.5:
                return "teal"
            else:
                return "green"
        elif b > r and b > g:
            if r > g * 1.5:
                return "pink"
            elif g > r * 1.5:
                return "turquoise"
            else:
                return "blue" if b > 150 else "navy"

        # Pastel/muted colors
        if max_val < 150 and min_val > 50:
            return "muted " + self._get_color_name((r * 2, g * 2, b * 2))

        return "unknown"


def extract_colors_from_image(
    image_path: str, mask_path: str | None = None, palette_size: int = 5
) -> dict:
    """Convenience function to extract all color info."""
    extractor = ColorExtractor()

    dominant_hex, dominant_name = extractor.extract_dominant_color(image_path, mask_path)
    palette = extractor.extract_palette(image_path, palette_size, mask_path)

    return {
        "dominant_color_hex": dominant_hex,
        "dominant_color_name": dominant_name,
        "palette": [{"hex": hex_, "name": name} for hex_, name in palette],
    }
