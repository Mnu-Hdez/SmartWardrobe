import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

from backend.core.config import get_settings
from backend.database.connection import get_db_session
from backend.models.schemas import FormalityLevel, GarmentCreate, Season
from backend.repositories import GarmentRepository
from backend.vision.pipeline import create_default_pipeline


class IngestionPipeline:
    """Orchestrates the complete garment ingestion pipeline using VisionPipeline stages."""

    def __init__(self):
        self.settings = get_settings()
        self.pipeline = create_default_pipeline(
            sam_model_type=self.settings.sam_model_type,
            clip_model=self.settings.clip_model,
            clip_pretrained=self.settings.clip_pretrained,
            clip_device=self.settings.device,
        )

    def process_garment(
        self,
        image_path: str,
        name: str | None = None,
        brand: str | None = None,
        size: str | None = None,
        material: str | None = None,
        price: float | None = None,
        purchase_date: datetime | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a garment image through the full pipeline:
        1. Segment garment from background
        2. Classify type, color, pattern, formality, season
        3. Extract dominant colors
        4. Save processed images to dual storage (raw + processed)
        5. Store in database

        Returns:
            Dict with garment info and processing results
        """
        # Generate unique ID for this garment
        garment_id = str(uuid.uuid4())[:8]

        # Prepare output paths - DUAL STORAGE
        # raw: Original high-res image for display
        # processed: Segmented/processed image for AI
        raw_dir = Path(self.settings.images_raw_dir)
        processed_dir = Path(self.settings.images_processed_garments_dir)
        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

        original_ext = Path(image_path).suffix
        base_name = f"{garment_id}{original_ext}"

        # Copy original to RAW storage (for high-quality display)
        import shutil

        stored_raw = raw_dir / base_name
        shutil.copy2(image_path, stored_raw)

        # Open image
        image = Image.open(image_path).convert("RGB")

        # Run vision pipeline
        context = {
            "garment_id": garment_id,
            "processed_dir": str(processed_dir),
            "image": image,
        }
        result = self.pipeline.run(image, context)

        # Extract results from pipeline context
        masked_image_path = result.get("masked_image_path")
        classification = result.get("classification", {})
        color_info = result.get("color_info", {})

        # Default classification
        classification = {
            "type": "top",
            "color": "black",
            "pattern": "solid",
            "formality": "casual",
            "season": "all_season",
            "overall_confidence": 0.5,
            **classification,
        }

        # Default color info
        color_info = {
            "dominant_color_hex": "#000000",
            "dominant_color_name": "black",
            "palette": [],
            **color_info,
        }

        # Create garment record with DUAL image paths
        garment_data = GarmentCreate(
            name=name or f"Garment {garment_id}",
            brand=brand,
            type=classification["type"],
            color_name=color_info["dominant_color_name"],
            dominant_color_hex=color_info["dominant_color_hex"],
            pattern=classification["pattern"],
            formality=self._formality_to_level(classification["formality"]),
            season=self._season_to_enum(classification["season"]),
            material=material,
            size=size,
            price=price,
            purchase_date=purchase_date,
            notes=notes,
            raw_image_path=str(stored_raw),  # RAW: original for display
            processed_image_path=result.get("masked_image_path") or str(stored_raw),  # PROCESSED: segmented for AI
            segmentation_mask_path=result.get("mask_path"),
        )

        # Save to database
        with get_db_session() as session:
            repo = GarmentRepository(session)
            garment = repo.create(garment_data)

            # Store additional metadata
            garment.confidence_scores = json.dumps(
                {
                    "type": classification.get("type_confidence"),
                    "color": classification.get("color_confidence"),
                    "pattern": classification.get("pattern_confidence"),
                    "formality": classification.get("formality_confidence"),
                    "season": classification.get("season_confidence"),
                    "overall": classification.get("overall_confidence"),
                    "segmentation": result.get("segmentation_confidence"),
                }
            )

            # Store CLIP embedding if available
            if masked_image_path := result.get("masked_image_path"):
                try:
                    classify_image = Image.open(masked_image_path)
                    # Note: In production, reuse classifier from pipeline
                    from backend.vision.classifier import CLIPClassifier
                    classifier = CLIPClassifier()
                    embedding = classifier.get_embedding(classify_image)
                    garment.clip_embedding = json.dumps(embedding.tolist())
                except Exception as e:
                    print(f"Embedding extraction failed: {e}")

            session.add(garment)
            session.commit()
            session.refresh(garment)

        return {
            "garment_id": garment.id,
            "name": garment.name,
            "type": garment.type,
            "color": garment.color_name,
            "color_hex": garment.dominant_color_hex,
            "pattern": garment.pattern,
            "formality": garment.formality,
            "season": garment.season,
            "raw_image": str(stored_raw),
            "processed_image": result.get("masked_image_path"),
            "mask_image": result.get("mask_path"),
            "confidence_scores": json.loads(garment.confidence_scores)
            if garment.confidence_scores
            else {},
            "palette": result.get("color_info", {}).get("palette", []),
        }

    def _formality_to_level(self, formality: str) -> FormalityLevel:
        """Convert formality string to FormalityLevel enum."""
        from backend.models.schemas import FormalityLevel
        mapping = {
            "very casual": FormalityLevel.CASUAL,
            "casual": FormalityLevel.CASUAL,
            "smart casual": FormalityLevel.SMART_CASUAL,
            "business casual": FormalityLevel.BUSINESS_CASUAL,
            "formal": FormalityLevel.FORMAL,
            "very formal": FormalityLevel.BLACK_TIE,
            "black tie": FormalityLevel.BLACK_TIE,
        }
        return mapping.get(formality.lower(), FormalityLevel.CASUAL)

    def _season_to_enum(self, season: str) -> Season:
        """Convert season string to Season enum."""
        season = season.lower()
        if season in ["spring", "summer", "autumn", "fall", "winter", "all season"]:
            return Season(season.replace("fall", "autumn"))
        return Season.ALL_SEASON

    def batch_process(self, image_dir: str, **kwargs) -> list:
        """Process multiple images in a directory."""
        results = []
        image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

        for file_path in Path(image_dir).iterdir():
            if file_path.suffix.lower() in image_extensions:
                try:
                    print(f"Processing {file_path.name}...")
                    result = self.process_garment(str(file_path), **kwargs)
                    results.append(result)
                except Exception as e:
                    print(f"Failed to process {file_path.name}: {e}")
                    results.append({"error": str(e), "file": str(file_path)})

        return results


def create_ingestion_pipeline() -> IngestionPipeline:
    """Factory function."""
    return IngestionPipeline()

