# Smart Wardrobe - Vision Pipeline
# CLIP Classifier for garment type and formality

import logging

import open_clip
import torch
from PIL import Image

logger = logging.getLogger(__name__)


class CLIPClassifier:
    """CLIP-based classifier for garment type and formality"""

    # Garment type prompts for CLIP
    TYPE_PROMPTS = [
        "a photo of a top, shirt, blouse, t-shirt",
        "a photo of a bottom, pants, jeans, trousers, skirt",
        "a photo of a dress, gown",
        "a photo of outerwear, jacket, coat, blazer",
        "a photo of shoes, sneakers, boots, heels",
        "a photo of an accessory, hat, bag, scarf, jewelry",
    ]

    TYPE_LABELS = ["top", "bottom", "dress", "outerwear", "shoes", "accessory"]

    # Pattern prompts - labels match backend.models.garment.Pattern exactly,
    # so classify()'s output can be written straight into a Garment without
    # any translation layer.
    PATTERN_PROMPTS = [
        "a solid, plain, single-color garment with no pattern",
        "a striped garment with parallel lines",
        "a checked or plaid garment with a grid pattern",
        "a floral garment with a flower print",
        "a garment with a polka dot pattern",
        "a garment with a geometric pattern",
        "a garment with an abstract print pattern",
        "a garment with an animal print pattern like leopard or zebra stripes",
        "a garment with a paisley pattern",
        "a garment with a houndstooth pattern",
    ]

    PATTERN_LABELS = [
        "solid", "striped", "checked", "floral", "polka_dot",
        "geometric", "abstract", "animal_print", "paisley", "houndstooth",
    ]

    # Formality prompts
    FORMALITY_PROMPTS = [
        "casual everyday clothing",
        "smart casual outfit",
        "business casual professional wear",
        "formal evening wear",
        "gala black tie formal wear",
    ]

    FORMALITY_LEVELS = [1, 2, 3, 4, 5]

    def __init__(
        self, model_name: str = "ViT-B-32", pretrained: str = "openai", device: str = "cpu"
    ):
        self.model_name = model_name
        self.pretrained = pretrained
        self.device = device
        self.model = None
        self.preprocess = None
        self.tokenizer = None
        self.type_text_features = None
        self.pattern_text_features = None
        self.formality_text_features = None

    def load(self):
        """Load CLIP model and precompute text features"""
        try:
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                self.model_name, pretrained=self.pretrained, device=self.device
            )
            self.tokenizer = open_clip.get_tokenizer(self.model_name)
            self.model.eval()

            # Precompute text features for types
            with torch.no_grad():
                type_tokens = self.tokenizer(self.TYPE_PROMPTS).to(self.device)
                self.type_text_features = self.model.encode_text(type_tokens)
                self.type_text_features /= self.type_text_features.norm(dim=-1, keepdim=True)

                pattern_tokens = self.tokenizer(self.PATTERN_PROMPTS).to(self.device)
                self.pattern_text_features = self.model.encode_text(pattern_tokens)
                self.pattern_text_features /= self.pattern_text_features.norm(dim=-1, keepdim=True)

                formality_tokens = self.tokenizer(self.FORMALITY_PROMPTS).to(self.device)
                self.formality_text_features = self.model.encode_text(formality_tokens)
                self.formality_text_features /= self.formality_text_features.norm(
                    dim=-1, keepdim=True
                )

            logger.info(f"CLIP {self.model_name} ({self.pretrained}) loaded on {self.device}")

        except ImportError:
            logger.error("open_clip_torch not installed. Run: pip install open_clip_torch")
            raise

    def classify_type(self, image: Image.Image) -> dict[str, any]:
        """Classify garment type"""
        if self.model is None:
            self.load()

        # Preprocess image
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            image_features = self.model.encode_image(image_tensor)
            image_features /= image_features.norm(dim=-1, keepdim=True)

            # Compute similarity
            similarity = (100.0 * image_features @ self.type_text_features.T).softmax(dim=-1)
            probs = similarity[0].cpu().numpy()

        best_idx = probs.argmax()
        return {
            "type": self.TYPE_LABELS[best_idx],
            "confidence": float(probs[best_idx]),
            "all_scores": {
                self.TYPE_LABELS[i]: float(probs[i]) for i in range(len(self.TYPE_LABELS))
            },
        }

    def classify_pattern(self, image: Image.Image) -> dict[str, any]:
        """Classify garment pattern (solid, striped, checked, ...)"""
        if self.model is None:
            self.load()

        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            image_features = self.model.encode_image(image_tensor)
            image_features /= image_features.norm(dim=-1, keepdim=True)

            similarity = (100.0 * image_features @ self.pattern_text_features.T).softmax(dim=-1)
            probs = similarity[0].cpu().numpy()

        best_idx = probs.argmax()
        return {
            "pattern": self.PATTERN_LABELS[best_idx],
            "confidence": float(probs[best_idx]),
            "all_scores": {
                self.PATTERN_LABELS[i]: float(probs[i]) for i in range(len(self.PATTERN_LABELS))
            },
        }

    def classify_formality(self, image: Image.Image) -> dict[str, any]:
        """Classify garment formality level (1-5)"""
        if self.model is None:
            self.load()

        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            image_features = self.model.encode_image(image_tensor)
            image_features /= image_features.norm(dim=-1, keepdim=True)

            similarity = (100.0 * image_features @ self.formality_text_features.T).softmax(dim=-1)
            probs = similarity[0].cpu().numpy()

        best_idx = probs.argmax()
        return {
            "formality": self.FORMALITY_LEVELS[best_idx],
            "confidence": float(probs[best_idx]),
            "all_scores": {
                self.FORMALITY_LEVELS[i]: float(probs[i]) for i in range(len(self.FORMALITY_LEVELS))
            },
        }

    def classify(self, image: Image.Image) -> dict[str, any]:
        """Classify type, pattern and formality in one call"""
        type_result = self.classify_type(image)
        pattern_result = self.classify_pattern(image)
        formality_result = self.classify_formality(image)
        return {
            "type": type_result["type"],
            "type_confidence": type_result["confidence"],
            "pattern": pattern_result["pattern"],
            "pattern_confidence": pattern_result["confidence"],
            "formality": formality_result["formality"],
            "formality_confidence": formality_result["confidence"],
        }
