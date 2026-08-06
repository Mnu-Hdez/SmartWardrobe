# backend/vision/stages/segmenter_stage.py
"""Segmentation stage — wraps SAM segmenter."""

from pathlib import Path
from typing import Any

from PIL import Image

from backend.vision.segmenter import SAMSegmenter


class SegmenterStage:
    """Segmentation stage — wraps SAM segmenter."""

    def __init__(self, model_type: str | None = None):
        self.segmenter = None
        try:
            self.segmenter = SAMSegmenter(model_type=model_type)
        except Exception as e:
            print(f"Warning: Could not load SAM segmenter: {e}")
            self.segmenter = None

    def process(self, image: "Image.Image", context: dict[str, Any]) -> dict[str, Any]:
        """Run segmentation on image, update context with mask and masked image."""
        if not self.segmenter:
            # Fallback: use original image
            context["masked_image"] = context["image"]
            context["mask_path"] = None
            context["masked_image_path"] = None
            context["segmentation_confidence"] = 0.0
            return context

        try:
            mask, masked_img, seg_score = self.segmenter.segment(context["image"])

            # Save masked image to processed storage
            processed_dir = Path(context["processed_dir"])
            processed_dir.mkdir(parents=True, exist_ok=True)

            masked_image_path = str(
                processed_dir / f"{context.get('garment_id', 'unknown')}_masked.png"
            )
            masked_img.save(masked_image_path)

            # Save mask
            mask_path = str(
                Path(context["processed_dir"]) / f"{context.get('garment_id', 'unknown')}_mask.png"
            )
            from PIL import Image as PILImage

            PILImage.fromarray((mask * 255).astype("uint8")).save(mask_path)

            context["mask"] = mask
            context["masked_image"] = masked_img
            context["masked_image_path"] = masked_image_path
            context["mask_path"] = mask_path
            context["segmentation_confidence"] = float(seg_score)
            print(f"Segmentation confidence: {seg_score:.2f}")

        except Exception as e:
            print(f"Segmentation failed: {e}")
            context["masked_image"] = context["image"]
            context["mask_path"] = None
            context["masked_image_path"] = None
            context["segmentation_confidence"] = 0.0

        return context


def create_segmenter_stage(model_type: str | None = None) -> "SegmenterStage":
    """Factory function."""
    return SegmenterStage(model_type=model_type)
