# Smart Wardrobe - Vision Pipeline
# On-device garment analysis: SAM segmentation + CLIP classification (type,
# pattern, formality) + dominant-color extraction. Fully local, no external
# API keys required.
#
# Wired into two call sites, both with a safe fallback if the heavy models
# aren't available/downloaded (never blocks the user):
#   - LocalRulesProvider.analyze_image() -> the "Auto-fill with AI" button
#     on the add-garment form. Every field stays editable before saving,
#     same review-before-accept pattern as the NIM/Gemini providers.
#   - POST /garments -> generates the real background-removed
#     `processed_image_path` instead of just copying the raw upload.

import logging
import uuid

from PIL import Image

from backend.core.config import settings
from backend.vision.classifier import CLIPClassifier
from backend.vision.color_extractor import ColorExtractor
from backend.vision.segmenter import SAMSegmenter

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """On-device garment vision pipeline.

    SAM and CLIP are expensive to initialize (model download + load onto
    device), so instances are cached at the class level and shared across
    every request for the process lifetime instead of being reloaded per
    call.
    """

    _segmenter: SAMSegmenter | None = None
    _classifier: CLIPClassifier | None = None
    _color_extractor: ColorExtractor | None = None

    def __init__(self, device: str | None = None):
        self.device = device or settings.DEVICE

    def _get_segmenter(self) -> SAMSegmenter:
        if IngestionPipeline._segmenter is None:
            IngestionPipeline._segmenter = SAMSegmenter(
                model_type=settings.SAM_MODEL_TYPE,
                device=self.device,
                checkpoint_dir=settings.MODELS_CACHE_DIR / "sam",
            )
        return IngestionPipeline._segmenter

    def _get_classifier(self) -> CLIPClassifier:
        if IngestionPipeline._classifier is None:
            IngestionPipeline._classifier = CLIPClassifier(
                model_name=settings.CLIP_MODEL,
                pretrained=settings.CLIP_PRETRAINED,
                device=self.device,
            )
        return IngestionPipeline._classifier

    def _get_color_extractor(self) -> ColorExtractor:
        if IngestionPipeline._color_extractor is None:
            IngestionPipeline._color_extractor = ColorExtractor()
        return IngestionPipeline._color_extractor

    def analyze_image(self, image: Image.Image) -> dict:
        """Best-effort field guesses for the add-garment auto-fill form.

        Shaped exactly like ImageAnalysisResponse (name/type/color_name/
        color_hex/material/pattern/formality/tags) so callers can splat the
        result straight into the response model. Returns null for fields
        this pipeline can't produce (name, material, tags) rather than
        guessing - same contract the NIM/Gemini providers already follow.
        """
        classification = self._get_classifier().classify(image)
        color_info = self._get_color_extractor().get_dominant_color(image)

        return {
            "name": None,
            "type": classification.get("type"),
            "color_name": color_info.get("name"),
            "color_hex": color_info.get("hex"),
            "material": None,
            "pattern": classification.get("pattern"),
            "formality": classification.get("formality"),
            "tags": [],
        }

    def segment_and_save(self, image: Image.Image, filename_hint: str | None = None) -> str:
        """Runs SAM segmentation and saves the masked (background-removed)
        garment as a transparent PNG under IMAGES_PROCESSED_GARMENTS_DIR.

        Returns the saved filename. Raises on any failure (missing weights,
        OOM, corrupt image) - the caller (POST /garments) already falls
        back to copying the raw image untouched, the same degrade-gracefully
        pattern every AI-dependent feature in this app follows.
        """
        segmenter = self._get_segmenter()
        mask = segmenter.segment_auto(image)
        masked_image = segmenter.apply_mask(image, mask)

        filename = f"{filename_hint or uuid.uuid4()}.png"
        path = settings.IMAGES_PROCESSED_GARMENTS_DIR / filename
        masked_image.save(path, "PNG", optimize=True)
        return filename
