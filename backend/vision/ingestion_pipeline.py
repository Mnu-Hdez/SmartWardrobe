import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

from backend.core.config import get_settings
from backend.database.connection import get_db_session
from backend.models.garment import GarmentCreate
from backend.repositories import GarmentRepository
from backend.vision.classifier import CLIPClassifier
from backend.vision.color_extractor import ColorExtractor, extract_colors_from_image
from backend.vision.segmenter import SAMSegmenter


class IngestionPipeline:
    """Orchestrates the complete garment ingestion pipeline."""

    def __init__(self):
        self.settings = get_settings()
        self.segmenter = None
        self.classifier = None
        self.color_extractor = None
        self._init_models()

    def _init_models(self):
        """Initialize vision models lazily."""
        try:
            self.segmenter = SAMSegmenter(model_type=self.settings.sam_model_type)
        except Exception as e:
            print(f"Warning: Could not load SAM segmenter: {e}")
            self.segmenter = None

        try:
            self.classifier = CLIPClassifier(
                model_name=self.settings.clip_model,
                pretrained=self.settings.clip_pretrained,
                device=self.settings.device,
            )
        except Exception as e:
            print(f"Warning: Could not load CLIP classifier: {e}")
            self.classifier = None

        self.color_extractor = ColorExtractor()

    def process_garment(
        self,
        image_path: str,
        name: str = None,
        brand: str = None,
        size: str = None,
        material: str = None,
        price: float = None,
        purchase_date: datetime = None,
        notes: str = None,
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

        # 1. Segmentation
        mask_path = None
        masked_image_path = None
        segmentation_confidence = 0.0

        if self.segmenter:
            try:
                mask, masked_img, seg_score = self.segmenter.segment(image)

                # Save masked image to PROCESSED storage
                masked_image_path = str(processed_dir / f"{garment_id}_masked{original_ext}")
                masked_img.save(masked_image_path)

                # Save mask
                mask_path = str(processed_dir / f"{garment_id}_mask.png")
                Image.fromarray((mask * 255).astype("uint8")).save(mask_path)

                segmentation_confidence = seg_score
                print(f"Segmentation confidence: {seg_score:.2f}")
            except Exception as e:
                print(f"Segmentation failed: {e}")
        else:
            # Use original image as fallback
            masked_image_path = str(processed_dir / f"{garment_id}_masked{original_ext}")
            image.save(masked_image_path)

        # 2. Classification
        classification = {
            "type": "top",
            "color": "black",
            "pattern": "solid",
            "formality": "casual",
            "season": "all_season",
            "overall_confidence": 0.5,
        }

        if self.classifier:
            try:
                # Use masked image for classification if available
                classify_image = Image.open(masked_image_path) if masked_image_path else image
                classification = self.classifier.classify(classify_image)
                print(
                    f"Classification: {classification['type']} ({classification['type_confidence']:.2f})"
                )
            except Exception as e:
                print(f"Classification failed: {e}")

        # 3. Color extraction
        color_info = {
            "dominant_color_hex": "#000000",
            "dominant_color_name": "black",
            "palette": [],
        }

        try:
            color_info = extract_colors_from_image(masked_image_path or str(stored_raw), mask_path)
            print(
                f"Dominant color: {color_info['dominant_color_name']} ({color_info['dominant_color_hex']})"
            )
        except Exception as e:
            print(f"Color extraction failed: {e}")

        # 4. Create garment record with DUAL image paths
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
            processed_image_path=masked_image_path
            or str(stored_raw),  # PROCESSED: segmented for AI
            segmentation_mask_path=mask_path,
        )

        # 5. Save to database
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
                    "segmentation": segmentation_confidence,
                }
            )

            # Store CLIP embedding if available
            if self.classifier and masked_image_path:
                try:
                    classify_image = Image.open(masked_image_path)
                    embedding = self.classifier.get_embedding(classify_image)
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
            "processed_image": masked_image_path,
            "mask_image": mask_path,
            "confidence_scores": json.loads(garment.confidence_scores)
            if garment.confidence_scores
            else {},
            "palette": color_info["palette"],
        }

    def _formality_to_level(self, formality: str) -> int:
        """Convert formality string to level 1-5."""
        mapping = {
            "very casual": 1,
            "casual": 1,
            "smart casual": 2,
            "business casual": 3,
            "formal": 4,
            "very formal": 5,
            "black tie": 5,
        }
        return mapping.get(formality.lower(), 1)

    def _season_to_enum(self, season: str) -> str:
        """Convert season string to enum."""
        season = season.lower()
        if season in ["spring", "summer", "autumn", "fall", "winter", "all season"]:
            return season.replace("fall", "autumn")
        return "all_season"

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
