# backend/vision/pipeline.py
"""Vision pipeline orchestrator — composes stages."""
from dataclasses import dataclass
from typing import Any, Protocol

from PIL import Image


class VisionStage(Protocol):
    """Protocol for vision pipeline stages."""

    def process(self, image: "Image.Image", context: dict[str, Any]) -> dict[str, Any]:
        """Process image and update context."""
        ...


@dataclass
class VisionPipeline:
    """Orchestrates vision stages in sequence."""

    stages: list[Any]

    def run(self, image: Image.Image, initial_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run all stages in sequence, passing context through each."""
        context = initial_context or {}
        context["image"] = image

        for stage in self.stages:
            context = stage.process(context["image"], context)

        return context


def create_default_pipeline(
    sam_model_type: str | None = None,
    clip_model: str = "ViT-B-32",
    clip_pretrained: str = "openai",
    clip_device: str = "cuda",
) -> "VisionPipeline":
    """Create pipeline with default stages."""
    from backend.vision.stages.classifier_stage import create_classifier_stage
    from backend.vision.stages.color_stage import create_color_stage
    from backend.vision.stages.segmenter_stage import create_segmenter_stage

    return VisionPipeline(
        stages=[
            create_segmenter_stage(sam_model_type),
            create_classifier_stage(),
            create_color_stage(),
        ]
    )
