# Smart Wardrobe - Vision Pipeline
# SAM Segmenter for garment isolation

import logging
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class SAMSegmenter:
    """Segment Anything Model (SAM) for garment segmentation"""

    def __init__(
        self, model_type: str = "vit_b", device: str = "cpu", checkpoint_dir: Path | None = None
    ):
        self.model_type = model_type
        self.device = device
        self.checkpoint_dir = checkpoint_dir or Path("/app/data/models_cache/sam")
        self.model = None
        self.predictor = None

    def load(self):
        """Load SAM model"""
        try:
            from segment_anything import SamPredictor, sam_model_registry
        except ImportError:
            logger.error("segment_anything not installed. Run: pip install segment-anything")
            raise

        # Model checkpoint mapping
        checkpoints = {
            "vit_b": "sam_vit_b_01ec64.pth",
            "vit_l": "sam_vit_l_0b3195.pth",
            "vit_h": "sam_vit_h_4b8939.pth",
        }

        checkpoint_name = checkpoints.get(self.model_type, "sam_vit_b_01ec64.pth")
        checkpoint_path = self.checkpoint_dir / checkpoint_name

        # Download if not exists
        if not checkpoint_path.exists():
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            self._download_checkpoint(checkpoint_name, checkpoint_path)

        # Load model
        sam = sam_model_registry[self.model_type](checkpoint=str(checkpoint_path))
        sam.to(device=self.device)
        sam.eval()

        self.predictor = SamPredictor(sam)
        self.model = sam
        logger.info(f"SAM {self.model_type} loaded on {self.device}")

    def _download_checkpoint(self, name: str, path: Path):
        """Download SAM checkpoint from official source"""
        import urllib.request

        urls = {
            "sam_vit_b_01ec64.pth": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth",
            "sam_vit_l_0b3195.pth": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth",
            "sam_vit_h_4b8939.pth": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
        }
        url = urls.get(name)
        if url:
            logger.info(f"Downloading SAM checkpoint from {url}...")
            urllib.request.urlretrieve(url, path)
            logger.info(f"Downloaded to {path}")

    def segment(
        self, image: Image.Image, box: tuple[int, int, int, int] | None = None
    ) -> np.ndarray:
        """
        Segment garment from image.
        Returns binary mask as numpy array (H, W) with values 0/1.
        """
        if self.predictor is None:
            self.load()

        # Convert PIL to numpy
        image_np = np.array(image.convert("RGB"))

        # Set image in predictor
        self.predictor.set_image(image_np)

        # If no box provided, use center box covering most of image
        if box is None:
            h, w = image_np.shape[:2]
            margin = min(w, h) // 10
            box = (margin, margin, w - margin, h - margin)

        # Predict mask
        masks, scores, logits = self.predictor.predict(box=np.array(box), multimask_output=True)

        # Return best mask
        best_mask = masks[np.argmax(scores)]
        return best_mask.astype(np.uint8)

    def segment_auto(self, image: Image.Image) -> np.ndarray:
        """Automatic segmentation using everything mode"""
        if self.predictor is None:
            self.load()

        image_np = np.array(image.convert("RGB"))
        self.predictor.set_image(image_np)

        # Use automatic mask generation
        from segment_anything import SamAutomaticMaskGenerator

        mask_generator = SamAutomaticMaskGenerator(self.model)
        masks = mask_generator.generate(image_np)

        # Find largest mask (likely the garment)
        if masks:
            largest = max(masks, key=lambda m: m["area"])
            return largest["segmentation"].astype(np.uint8)

        # Fallback: center box
        h, w = image_np.shape[:2]
        margin = min(w, h) // 10
        box = (margin, margin, w - margin, h - margin)
        return self.segment(image, box)

    def apply_mask(self, image: Image.Image, mask: np.ndarray) -> Image.Image:
        """Apply mask to image, returning RGBA with transparency"""
        # Ensure image is RGBA
        image_rgba = image.convert("RGBA")
        image_np = np.array(image_rgba)

        # Apply mask to alpha channel
        alpha = (mask * 255).astype(np.uint8)
        image_np[:, :, 3] = alpha

        return Image.fromarray(image_np, "RGBA")

    def crop_to_mask(self, image: Image.Image, mask: np.ndarray, padding: int = 20) -> Image.Image:
        """Crop image to mask bounding box with padding"""
        # Find mask bounds
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        if not rows.any() or not cols.any():
            return image

        y_min, y_max = np.where(rows)[0][[0, -1]]
        x_min, x_max = np.where(cols)[0][[0, -1]]

        # Add padding
        h, w = mask.shape
        y_min = max(0, y_min - padding)
        y_max = min(h, y_max + padding)
        x_min = max(0, x_min - padding)
        x_max = min(w, x_max + padding)

        # Crop both image and mask
        cropped_image = image.crop((x_min, y_min, x_max, y_max))
        return cropped_image
