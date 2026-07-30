
from pathlib import Path

import numpy as np
import requests
from PIL import Image
from segment_anything import SamPredictor, sam_model_registry

from backend.core.config import get_settings


class SAMSegmenter:
    """Segment Anything Model (SAM) for garment segmentation."""

    def __init__(self, model_type: str = None, checkpoint_path: str = None):
        self.settings = get_settings()
        self.model_type = model_type or self.settings.sam_model_type
        self.checkpoint_path = checkpoint_path or self._get_checkpoint_path()
        self.predictor = None
        self._load_model()

    def _get_checkpoint_path(self) -> str:
        """Get or download SAM checkpoint."""
        cache_dir = Path(self.settings.models_cache_dir) / "sam"
        cache_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_file = cache_dir / f"sam_{self.model_type}.pth"

        if not checkpoint_file.exists():
            print(f"Downloading SAM {self.model_type} checkpoint...")
            url = self.settings.sam_checkpoint_url
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(checkpoint_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded to {checkpoint_file}")

        return str(checkpoint_file)

    def _load_model(self):
        """Load SAM model."""
        try:
            sam = sam_model_registry[self.model_type](checkpoint=self.checkpoint_path)
            sam.to(device=self.settings.device)
            self.predictor = SamPredictor(sam)
            print(f"SAM {self.model_type} loaded on {self.settings.device}")
        except ImportError:
            raise ImportError(
                "segment-anything not installed. Install with: pip install segment-anything"
            )
        except Exception as e:
            # Handle corrupted checkpoint file
            if "failed finding central directory" in str(e) or "corrupted" in str(e).lower():
                print(f"Corrupted checkpoint detected, removing and re-downloading: {e}")
                try:
                    Path(self.checkpoint_path).unlink(missing_ok=True)
                except Exception:
                    pass
                # Re-download
                self.checkpoint_path = self._get_checkpoint_path()
                sam = sam_model_registry[self.model_type](checkpoint=self.checkpoint_path)
                sam.to(device=self.settings.device)
                self.predictor = SamPredictor(sam)
                print(f"SAM {self.model_type} re-downloaded and loaded on {self.settings.device}")
            else:
                raise RuntimeError(f"Failed to load SAM: {e}")

    def segment(
        self,
        image: Image.Image,
        point: tuple[int, int] | None = None,
        box: tuple[int, int, int, int] | None = None,
    ) -> tuple[np.ndarray, Image.Image, float]:
        """
        Segment garment from image.

        Args:
            image: PIL Image
            point: Optional (x, y) point prompt (center of garment)
            box: Optional (x1, y1, x2, y2) box prompt

        Returns:
            Tuple of (mask_array, masked_image, confidence_score)
        """
        if self.predictor is None:
            raise RuntimeError("SAM predictor not initialized")

        # Convert to numpy
        image_np = np.array(image)

        # Set image
        self.predictor.set_image(image_np)

        # Prepare prompts
        if point is None:
            # Default to center of image
            h, w = image_np.shape[:2]
            point = (w // 2, h // 2)

        input_point = np.array([point])
        input_label = np.array([1])  # foreground

        # Predict
        masks, scores, logits = self.predictor.predict(
            point_coords=input_point, point_labels=input_label, multimask_output=True
        )

        # Select best mask
        best_idx = np.argmax(scores)
        mask = masks[best_idx]
        score = scores[best_idx]

        # Apply mask to image
        masked_image = self._apply_mask(image, mask)

        return mask, masked_image, float(score)

    def segment_with_box(
        self, image: Image.Image, box: tuple[int, int, int, int]
    ) -> tuple[np.ndarray, Image.Image, float]:
        """Segment using box prompt."""
        if self.predictor is None:
            raise RuntimeError("SAM predictor not initialized")

        image_np = np.array(image)
        self.predictor.set_image(image_np)

        input_box = np.array(box)

        masks, scores, logits = self.predictor.predict(
            box=input_box[None, :], multimask_output=True
        )

        best_idx = np.argmax(scores)
        mask = masks[best_idx]
        score = scores[best_idx]

        masked_image = self._apply_mask(image, mask)

        return mask, masked_image, float(score)

    def _apply_mask(self, image: Image.Image, mask: np.ndarray) -> Image.Image:
        """Apply mask to image, making background transparent."""
        image_np = np.array(image).copy()

        # Ensure mask is boolean
        mask_bool = mask > 0

        # Create RGBA image
        if image_np.shape[2] == 3:
            rgba = np.zeros((image_np.shape[0], image_np.shape[1], 4), dtype=np.uint8)
            rgba[:, :, :3] = image_np
        else:
            rgba = image_np.copy()

        # Set alpha channel
        rgba[:, :, 3] = mask_bool * 255

        return Image.fromarray(rgba, "RGBA")

    def get_bounding_box(self, mask: np.ndarray) -> tuple[int, int, int, int]:
        """Get bounding box of mask."""
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)

        if not np.any(rows) or not np.any(cols):
            return 0, 0, mask.shape[1], mask.shape[0]

        y1, y2 = np.where(rows)[0][[0, -1]]
        x1, x2 = np.where(cols)[0][[0, -1]]

        return int(x1), int(y1), int(x2), int(y2)
