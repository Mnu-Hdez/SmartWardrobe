from unittest.mock import Mock, patch

import numpy as np
import pytest
from PIL import Image


class TestVisionPipeline:
    """Test vision pipeline components."""

    @pytest.fixture
    def sample_image(self):
        """Create a sample test image."""
        # Create a simple colored image
        img = Image.new("RGB", (224, 224), color="red")
        return img

    @pytest.fixture
    def sample_image_path(self, tmp_path, sample_image):
        """Save sample image to temp file."""
        path = tmp_path / "test_garment.jpg"
        sample_image.save(path)
        return str(path)


class TestSAMSegmenter:
    """Test Segment Anything Model segmenter."""

    @patch("backend.vision.segmenter.sam_model_registry")
    @patch("backend.vision.segmenter.SamPredictor")
    def test_segmenter_initialization(self, mock_predictor, mock_registry, sample_image):
        """Test SAM segmenter initializes correctly."""
        from backend.vision.segmenter import SAMSegmenter

        # Mock SAM model
        mock_sam = Mock()
        mock_registry.return_value = mock_sam
        mock_sam.to = Mock(return_value=mock_sam)

        _ = SAMSegmenter(model_type="vit_b")

        mock_registry.assert_called_once_with("vit_b")
        mock_sam.to.assert_called_once()

    @patch("backend.vision.segmenter.SamPredictor")
    @patch("backend.vision.segmenter.sam_model_registry")
    def test_segment_auto(self, mock_registry, mock_predictor_class, sample_image):
        """Test automatic segmentation."""
        from backend.vision.segmenter import SAMSegmenter

        # Setup mocks
        mock_sam = Mock()
        mock_registry.return_value = mock_sam

        mock_predictor = Mock()
        mock_predictor_class.return_value = mock_predictor

        # Mock mask generation
        mock_generator = Mock()
        mock_generator.generate.return_value = [
            {"segmentation": np.ones((224, 224), dtype=bool), "area": 50000, "stability_score": 0.9}
        ]

        with patch(
            "backend.vision.segmenter.SamAutomaticMaskGenerator", return_value=mock_generator
        ):
            segmenter = SAMSegmenter()
            segmenter.predictor = mock_predictor
            segmenter.model = mock_sam

            mask, masked_img, score = segmenter.segment_auto(sample_image)

            assert mask.shape == (224, 224)
            assert isinstance(masked_img, Image.Image)
            assert 0 <= score <= 1

    @patch("backend.vision.segmenter.SamPredictor")
    @patch("backend.vision.segmenter.sam_model_registry")
    def test_segment_with_point(self, mock_registry, mock_predictor_class, sample_image):
        """Test segmentation with point prompt."""
        from backend.vision.segmenter import SAMSegmenter

        mock_sam = Mock()
        mock_registry.return_value = mock_sam

        mock_predictor = Mock()
        mock_predictor_class.return_value = mock_predictor

        # Mock prediction output
        mock_predictor.predict.return_value = (
            np.array([np.ones((224, 224), dtype=bool)]),  # masks
            np.array([0.9]),  # scores
            np.array([[]]),  # logits
        )

        segmenter = SAMSegmenter()
        segmenter.predictor = mock_predictor

        mask, masked_img, score = segmenter.segment(sample_image, point=(112, 112))

        assert mask.shape == (224, 224)
        assert isinstance(masked_img, Image.Image)
        assert score == 0.9
        mock_predictor.set_image.assert_called_once()
        mock_predictor.predict.assert_called_once()


class TestCLIPClassifier:
    """Test CLIP-based garment classifier."""

    @patch("backend.vision.classifier.open_clip.create_model_and_transforms")
    @patch("backend.vision.classifier.open_clip.get_tokenizer")
    def test_classifier_initialization(self, mock_tokenizer, mock_create_model):
        """Test CLIP classifier initializes correctly."""
        from backend.vision.classifier import CLIPClassifier

        mock_model = Mock()
        mock_preprocess = Mock()
        mock_create_model.return_value = (mock_model, None, mock_preprocess)

        mock_tokenizer_instance = Mock()
        mock_tokenizer.return_value = mock_tokenizer_instance

        classifier = CLIPClassifier(model_name="ViT-B-32", pretrained="openai")

        assert classifier.model_name == "ViT-B-32"
        assert classifier.pretrained == "openai"
        mock_create_model.assert_called_once()
        mock_tokenizer.assert_called_once_with("ViT-B-32")

    @patch("backend.vision.classifier.open_clip.create_model_and_transforms")
    @patch("backend.vision.classifier.open_clip.get_tokenizer")
    def test_classify_garment(self, mock_tokenizer, mock_create_model, sample_image):
        """Test garment classification."""
        from backend.vision.classifier import CLIPClassifier

        mock_model = Mock()
        mock_preprocess = Mock()
        mock_create_model.return_value = (mock_model, None, mock_preprocess)

        mock_tokenizer_instance = Mock()
        mock_tokenizer.return_value = mock_tokenizer_instance

        # Mock embeddings
        mock_text_embeds = Mock()
        mock_text_embeds.norm.return_value = mock_text_embeds
        mock_image_embeds = Mock()
        mock_image_embeds.norm.return_value = mock_image_embeds

        # Mock similarity computation
        mock_model.encode_text.return_value = mock_text_embeds
        mock_model.encode_image.return_value = mock_image_embeds

        # Mock softmax output for each category
        with patch("torch.nn.functional.softmax") as mock_softmax:
            mock_softmax.return_value = Mock(
                cpu=Mock(
                    return_value=Mock(numpy=Mock(return_value=np.array([0.8, 0.1, 0.05, 0.05])))
                )
            )

            classifier = CLIPClassifier()
            result = classifier.classify(sample_image)

            assert "type" in result
            assert "color" in result
            assert "pattern" in result
            assert "formality" in result
            assert "season" in result
            assert "type_confidence" in result
            assert "overall_confidence" in result

    def test_get_embedding(self, sample_image):
        """Test getting image embedding."""
        from backend.vision.classifier import CLIPClassifier

        with patch.object(CLIPClassifier, "__init__", lambda self: None):
            classifier = CLIPClassifier()
            classifier.model = Mock()
            classifier.preprocess = Mock(return_value=Mock())
            classifier.device = "cpu"

            mock_embed = Mock()
            mock_embed.norm.return_value = mock_embed
            mock_embed.cpu.return_value.numpy.return_value = np.random.rand(512)

            classifier.model.encode_image = Mock(return_value=mock_embed)

            embedding = classifier.get_embedding(sample_image)

            assert embedding.shape == (512,)
            assert isinstance(embedding, np.ndarray)


class TestColorExtractor:
    """Test color extraction from garment images."""

    def test_extract_dominant_color(self, sample_image_path):
        """Test dominant color extraction."""
        from backend.vision.color_extractor import ColorExtractor

        extractor = ColorExtractor()

        # Test with simple image
        hex_color, color_name = extractor.extract_dominant_color(sample_image_path)

        assert hex_color.startswith("#")
        assert len(hex_color) == 7
        assert isinstance(color_name, str)
        assert len(color_name) > 0

    def test_extract_palette(self, sample_image_path):
        """Test color palette extraction."""
        from backend.vision.color_extractor import ColorExtractor

        extractor = ColorExtractor()
        palette = extractor.extract_palette(sample_image_path, color_count=3)

        assert len(palette) <= 3
        for hex_color, color_name in palette:
            assert hex_color.startswith("#")
            assert len(hex_color) == 7

    def test_rgb_to_hex(self):
        """Test RGB to hex conversion."""
        from backend.vision.color_extractor import ColorExtractor

        extractor = ColorExtractor()

        assert extractor._rgb_to_hex((255, 0, 0)) == "#FF0000"
        assert extractor._rgb_to_hex((0, 255, 0)) == "#00FF00"
        assert extractor._rgb_to_hex((0, 0, 255)) == "#0000FF"
        assert extractor._rgb_to_hex((128, 128, 128)) == "#808080"
        assert extractor._rgb_to_hex((0, 0, 0)) == "#000000"
        assert extractor._rgb_to_hex((255, 255, 255)) == "#FFFFFF"

    def test_get_color_name(self):
        """Test color name mapping."""
        from backend.vision.color_extractor import ColorExtractor

        extractor = ColorExtractor()

        # Basic colors
        assert extractor._get_color_name((255, 0, 0)) == "red"
        assert extractor._get_color_name((0, 255, 0)) == "green"
        assert extractor._get_color_name((0, 0, 255)) == "blue"

        # Grayscale
        assert extractor._get_color_name((0, 0, 0)) == "black"
        assert extractor._get_color_name((255, 255, 255)) == "white"
        assert "gray" in extractor._get_color_name((128, 128, 128))

        # Mixed colors
        assert extractor._get_color_name((255, 165, 0)) == "orange"
        assert extractor._get_color_name((255, 255, 0)) == "yellow"
        assert extractor._get_color_name((255, 0, 255)) == "magenta"
        assert extractor._get_color_name((0, 255, 255)) == "cyan"


class TestIngestionPipeline:
    """Test the on-device SAM+CLIP+color ingestion pipeline."""

    def test_analyze_image_shape(self, sample_image):
        """analyze_image() must return every ImageAnalysisResponse field,
        with type/pattern/formality/color coming from the classifier and
        color extractor, and name/material/tags left null (this pipeline
        can't guess those)."""
        from backend.vision.ingestion_pipeline import IngestionPipeline

        pipeline = IngestionPipeline()
        mock_classifier = Mock()
        mock_classifier.classify.return_value = {
            "type": "top",
            "type_confidence": 0.9,
            "pattern": "solid",
            "pattern_confidence": 0.8,
            "formality": 2,
            "formality_confidence": 0.7,
        }
        mock_color_extractor = Mock()
        mock_color_extractor.get_dominant_color.return_value = {
            "hex": "#ff0000", "rgb": (255, 0, 0), "name": "Red",
        }
        pipeline._get_classifier = Mock(return_value=mock_classifier)
        pipeline._get_color_extractor = Mock(return_value=mock_color_extractor)

        result = pipeline.analyze_image(sample_image)

        assert result["type"] == "top"
        assert result["pattern"] == "solid"
        assert result["formality"] == 2
        assert result["color_hex"] == "#ff0000"
        assert result["color_name"] == "Red"
        assert result["name"] is None
        assert result["material"] is None
        assert result["tags"] == []

    def test_segment_and_save(self, sample_image, tmp_path, monkeypatch):
        """segment_and_save() must run segmentation, apply the mask, and
        write a PNG under IMAGES_PROCESSED_GARMENTS_DIR, returning its
        filename."""
        from backend.core.config import settings
        from backend.vision.ingestion_pipeline import IngestionPipeline

        monkeypatch.setattr(settings, "IMAGES_PROCESSED_GARMENTS_DIR", tmp_path)

        pipeline = IngestionPipeline()
        mock_segmenter = Mock()
        mock_segmenter.segment_auto.return_value = np.ones((224, 224), dtype="uint8")
        mock_segmenter.apply_mask.return_value = sample_image.convert("RGBA")
        pipeline._get_segmenter = Mock(return_value=mock_segmenter)

        filename = pipeline.segment_and_save(sample_image, filename_hint="test-garment")

        assert filename == "test-garment.png"
        assert (tmp_path / filename).exists()

    def test_analyze_image_used_by_local_provider_fallback(self):
        """LocalRulesProvider.analyze_image must fall back to color-only
        analysis if the vision pipeline raises (e.g. missing weights),
        instead of propagating the error to the caller."""
        from backend.ai_providers.local import LocalRulesProvider

        provider = LocalRulesProvider()
        img = Image.new("RGB", (10, 10), color="blue")
        import io

        buf = io.BytesIO()
        img.save(buf, format="JPEG")

        # No mocking of the vision pipeline - on a machine without the SAM/
        # CLIP weights downloaded this will raise internally, and the
        # fallback path must still return a well-formed result.
        result = provider.analyze_image(buf.getvalue(), "image/jpeg")
        assert "color_hex" in result
        assert "type" in result


# Integration tests for vision pipeline
class TestVisionPipelineIntegration:
    """Test vision components working together."""

    @pytest.fixture
    def test_image(self, tmp_path):
        """Create a realistic test garment image."""
        # Create an image with a distinct object on background
        img = Image.new("RGB", (400, 400), color="white")  # White background
        # Add a colored rectangle (simulating a garment)
        from PIL import ImageDraw

        draw = ImageDraw.Draw(img)
        draw.rectangle([100, 100, 300, 300], fill="blue")
        path = tmp_path / "test_garment.jpg"
        img.save(path)
        return str(path)

    @pytest.mark.skipif(
        not pytest.importorskip("segment_anything", reason="SAM not available"),
        reason="Requires segment-anything package",
    )
    def test_full_pipeline_with_real_models(self, test_image):
        """Test pipeline with real models (requires models downloaded)."""

        # This test requires actual model weights
        # Run manually with: pytest tests/unit/test_vision.py::TestVisionPipelineIntegration::test_full_pipeline_with_real_models -v -s
        pass


# Fixtures and utilities
@pytest.fixture
def mock_pil_image():
    """Create a mock PIL image for testing."""
    return Image.new("RGB", (224, 224), color="blue")
