# backend/vision/stages/classifier_stage.py
"""Classification stage — wraps CLIP classifier."""
from typing import Any

from PIL import Image

from backend.vision.classifier import CLIPClassifier


class ClassifierStage:
    """Classification stage — wraps CLIP classifier."""

    def __init__(
        self,
        model_name: str = "ViT-B-32",
        pretrained: str = "openai",
        device: str = "cuda",
    ):
        self.classifier = None
        try:
            self.classifier = CLIPClassifier(
                model_name=model_name,
                pretrained=pretrained,
                device=device,
            )
        except Exception as e:
            print(f"Warning: Could not load CLIP classifier: {e}")
            self.classifier = None

    def process(self, image: "Image.Image", context: dict[str, Any]) -> dict[str, Any]:
        """Run classification on image, update context with classification results."""
        # Default classification
        classification = {
            "type": "top",
            "color": "black",
            "pattern": "solid",
            "formality": "casual",
            "season": "all_season",
            "overall_confidence": 0.5,
        }

        if not self.classifier:
            context["classification"] = classification
            return context

        try:
            # Use masked image for classification if available
            classify_image = context.get("masked_image") or image
            classification = self.classifier.classify(classify_image)
            print(
                f"Classification: {classification['type']} ({classification['type_confidence']:.2f})"
            )
        except Exception as e:
            print(f"Classification failed: {e}")

        context["classification"] = classification
        return context


def create_classifier_stage(
    model_name: str = "ViT-B-32",
    pretrained: str = "openai",
    device: str = "cuda",
) -> "ClassifierStage":
    """Factory function."""
    return ClassifierStage(
        model_name=model_name,
        pretrained=pretrained,
        device=device,
    )
