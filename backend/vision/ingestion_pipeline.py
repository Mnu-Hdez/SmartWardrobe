# Smart Wardrobe - Vision Pipeline
# Ingestion Pipeline: Dual storage write (raw + processed garment mask as PNG)

import logging
import uuid
from typing import Any

from core.config import settings
from PIL import Image
from vision.classifier import CLIPClassifier
from vision.color_extractor import ColorExtractor
from vision.segmenter import SAMSegmenter

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Complete garment ingestion pipeline: raw save -> SAM segmentation -> CLIP classification -> Color extraction -> DB persist"""

    def __init__(self, device: str = "cpu"):
        self.device = device
        self.segmenter = SAMSegmenter(
            device=device, checkpoint_dir=settings.MODELS_CACHE_DIR / "sam"
        )
        self.classifier = CLIPClassifier(device=device)
        self.color_extractor = ColorExtractor()

    def process(self, image_file, metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Process uploaded garment image through full pipeline.
        Returns dict with all extracted data ready for DB insertion.
        """
        # Load image
        image = Image.open(image_file)
        image = image.convert("RGB")

        # 1. Save raw image
        raw_filename = self._save_raw_image(image)
        # raw_path = settings.IMAGES_RAW_DIR / raw_filename  # Not used, just for reference

        # 2. Segment with SAM
        logger.info("Running SAM segmentation...")
        mask = self.segmenter.segment_auto(image)

        # 3. Apply mask and save as PNG (preserves transparency)
        logger.info("Applying mask and saving processed image...")
        masked_image = self.segmenter.apply_mask(image, mask)
        processed_filename = self._save_processed_image(masked_image)

        # 4. Classify with CLIP
        logger.info("Running CLIP classification...")
        classification = self.classifier.classify(image)

        # 5. Extract dominant color
        logger.info("Extracting dominant color...")
        color_info = self.color_extractor.get_dominant_color(image)

        # 6. Prepare garment data
        garment_data = {
            "name": metadata.get("name", "Unnamed Garment"),
            "brand": metadata.get("brand"),
            "type": classification["type"],
            "season": metadata.get("season", "all_season"),
            "size": metadata.get("size"),
            "material": metadata.get("material"),
            "color_name": color_info["name"],
            "color_hex": color_info["hex"],
            "pattern": metadata.get("pattern", "solid"),
            "formality": classification["formality"],
            "raw_image_path": raw_filename,
            "processed_image_path": processed_filename,
        }

        logger.info(f"Ingestion complete: {garment_data['name']} ({garment_data['type']})")
        return garment_data

    def _save_raw_image(self, image: Image.Image) -> str:
        """Save raw image with original format"""
        ext = ".jpg"  # Default to JPEG for raw
        filename = f"{uuid.uuid4()}{ext}"
        path = settings.IMAGES_RAW_DIR / filename

        # Save as JPEG (efficient for raw storage)
        image.save(path, "JPEG", quality=90, optimize=True)
        return filename

    def _save_processed_image(self, image: Image.Image) -> str:
        """Save processed (masked) image as PNG (preserves alpha)"""
        filename = f"{uuid.uuid4()}.png"
        path = settings.IMAGES_PROCESSED_GARMENTS_DIR / filename

        # Save as PNG (required for transparency)
        image.save(path, "PNG", optimize=True)
        return filename

    def reprocess_garment(self, raw_image_path: str) -> dict[str, Any]:
        """
        Re-process an existing garment from raw image.
        Useful when SAM/CLIP models are updated.
        """
        raw_path = settings.IMAGES_RAW_DIR / raw_image_path
        if not raw_path.exists():
            raise FileNotFoundError(f"Raw image not found: {raw_path}")

        image = Image.open(raw_path).convert("RGB")

        # Re-run segmentation
        mask = self.segmenter.segment_auto(image)
        masked_image = self.segmenter.apply_mask(image, mask)
        processed_filename = self._save_processed_image(masked_image)

        # Re-run classification
        classification = self.classifier.classify(image)

        # Re-extract color
        color_info = self.color_extractor.get_dominant_color(image)

        return {
            "processed_image_path": processed_filename,
            "type": classification["type"],
            "formality": classification["formality"],
            "color_name": color_info["name"],
            "color_hex": color_info["hex"],
        }
