from typing import Any

import numpy as np
import open_clip  # type: ignore[import-untyped]
import torch
from PIL import Image

from backend.core.config import get_settings

# Default labels for classification
GARMENT_TYPES: list[str] = [
    "t-shirt",
    "shirt",
    "blouse",
    "sweater",
    "hoodie",
    "jacket",
    "coat",
    "blazer",
    "cardigan",
    "tank top",
    "crop top",
    "polo",
    "turtleneck",
    "jeans",
    "trousers",
    "shorts",
    "skirt",
    "leggings",
    "sweatpants",
    "dress",
    "jumpsuit",
    "romper",
    "sneakers",
    "boots",
    "sandals",
    "loafers",
    "heels",
    "flats",
    "oxfords",
    "scarf",
    "hat",
    "belt",
    "bag",
    "backpack",
    "sunglasses",
    "jewelry",
    "watch",
]

COLORS = [
    "red",
    "blue",
    "green",
    "yellow",
    "orange",
    "purple",
    "pink",
    "brown",
    "black",
    "white",
    "gray",
    "grey",
    "beige",
    "navy",
    "maroon",
    "teal",
    "olive",
    "coral",
    "lavender",
    "turquoise",
    "gold",
    "silver",
    "bronze",
]

PATTERNS = [
    "solid",
    "striped",
    "checked",
    "plaid",
    "floral",
    "polka dot",
    "geometric",
    "abstract",
    "animal print",
    "paisley",
    "houndstooth",
]

FORMALITY = ["very casual", "casual", "smart casual", "business casual", "formal", "very formal"]

SEASONS = ["spring", "summer", "autumn", "winter", "all season"]


class CLIPClassifier:
    """CLIP-based zero-shot classifier for garments."""

    def __init__(
        self, model_name: str = "ViT-B-32", pretrained: str = "openai", device: str = "cuda"
    ):
        self.settings = get_settings()
        self.model_name = model_name
        self.pretrained = pretrained
        self.device = device if torch.cuda.is_available() else "cpu"

        self.model: Any = None
        self.preprocess: Any = None
        self.tokenizer: Any = None
        self._text_embeddings: dict[str, tuple[list[str], torch.Tensor]] = {}
        self._load_model()

        # Pre-compute text embeddings for all labels
        self._compute_text_embeddings()

    def _load_model(self):
        """Load CLIP model."""
        try:
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                self.model_name, pretrained=self.pretrained, device=self.device
            )
            self.tokenizer = open_clip.get_tokenizer(self.model_name)
            self.model.eval()
            print(f"CLIP {self.model_name} ({self.pretrained}) loaded on {self.device}")
        except ImportError:
            raise ImportError(
                "open-clip-torch not installed. Install with: pip install open-clip-torch"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load CLIP: {e}")

    def _compute_text_embeddings(self):
        """Pre-compute text embeddings for all label categories."""
        with torch.no_grad():
            # Garment types
            type_tokens = self.tokenizer(GARMENT_TYPES).to(self.device)
            type_embeds = self.model.encode_text(type_tokens)
            type_embeds /= type_embeds.norm(dim=-1, keepdim=True)
            self._text_embeddings["type"] = (GARMENT_TYPES, type_embeds)

            # Colors
            color_tokens = self.tokenizer(COLORS).to(self.device)
            color_embeds = self.model.encode_text(color_tokens)
            color_embeds /= color_embeds.norm(dim=-1, keepdim=True)
            self._text_embeddings["color"] = (COLORS, color_embeds)

            # Patterns
            pattern_tokens = self.tokenizer(PATTERNS).to(self.device)
            pattern_embeds = self.model.encode_text(pattern_tokens)
            pattern_embeds /= pattern_embeds.norm(dim=-1, keepdim=True)
            self._text_embeddings["pattern"] = (PATTERNS, pattern_embeds)

            # Formality
            formal_tokens = self.tokenizer(FORMALITY).to(self.device)
            formal_embeds = self.model.encode_text(formal_tokens)
            formal_embeds /= formal_embeds.norm(dim=-1, keepdim=True)
            self._text_embeddings["formality"] = (FORMALITY, formal_embeds)

            # Seasons
            season_tokens = self.tokenizer(SEASONS).to(self.device)
            season_embeds = self.model.encode_text(season_tokens)
            season_embeds /= season_embeds.norm(dim=-1, keepdim=True)
            self._text_embeddings["season"] = (SEASONS, season_embeds)

    def classify(self, image: Image.Image) -> dict[str, Any]:
        """
        Classify garment image.

        Returns:
            Dict with type, color, pattern, formality, season and confidences
        """
        # Preprocess image
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            # Get image embedding
            image_embed = self.model.encode_image(image_tensor)
            image_embed /= image_embed.norm(dim=-1, keepdim=True)

            # Classify each category
            results = {}

            for category, (labels, text_embeds) in self._text_embeddings.items():
                # Compute similarities
                similarities = (100.0 * image_embed @ text_embeds.T).softmax(dim=-1)
                probs = similarities[0].cpu().numpy()

                # Get top prediction
                top_idx = np.argmax(probs)
                results[f"{category}"] = labels[top_idx]
                results[f"{category}_confidence"] = float(probs[top_idx])

                # Store top 3 for debugging
                top3_idx = np.argsort(probs)[-3:][::-1]
                results[f"{category}_top3"] = [
                    {"label": labels[i], "confidence": float(probs[i])} for i in top3_idx
                ]

        # Overall confidence (geometric mean of confidences)
        confidences = [
            results.get(f"{c}_confidence", 0.5)
            for c in ["type", "color", "pattern", "formality", "season"]
        ]
        results["overall_confidence"] = float(np.prod(confidences) ** (1.0 / len(confidences)))

        return results

    def get_embedding(self, image: Image.Image) -> np.ndarray:
        """Get CLIP image embedding for similarity search."""
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            embed = self.model.encode_image(image_tensor)
            embed /= embed.norm(dim=-1, keepdim=True)

        return embed[0].cpu().numpy()

    def find_similar_garments(
        self, query_image: Image.Image, garment_embeddings: list[np.ndarray], top_k: int = 5
    ) -> list[tuple[int, float]]:
        """Find similar garments by embedding similarity."""
        query_embed = self.get_embedding(query_image)

        similarities = []
        for i, emb in enumerate(garment_embeddings):
            sim = float(query_embed @ emb)
            similarities.append((i, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


def create_classifier() -> CLIPClassifier:
    """Factory function."""
    return CLIPClassifier()
