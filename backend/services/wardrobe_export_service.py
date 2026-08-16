# Smart Wardrobe - Export/Import Service
# Wardrobe <-> .zip (wardrobe.json + images/) round-trip. Extracted out of
# the HTTP router (SRP): the router's job is to parse the request and shape
# the response, not to know about zipfile/manifest formats or how images are
# stored on disk.

import io
import json
import shutil
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError
from sqlmodel import Session

from backend.core.config import settings
from backend.models.garment import Garment
from backend.models.schemas import GarmentCreate, GarmentResponse
from backend.repositories.garment_repo import GarmentRepository


class WardrobeExportService:
    """Builds and consumes the whole-wardrobe .zip export format:
    `wardrobe.json` (garment metadata) + `images/` (each garment's raw
    photo, referenced by the manifest entry's `image_file`)."""

    def __init__(self, session: Session):
        self.repo = GarmentRepository(session)

    def export_to_zip(self) -> io.BytesIO:
        """Build the export archive in memory and return it positioned at
        the start, ready to stream."""
        garments = self.repo.get_all(limit=100000)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            manifest = []
            for g in garments:
                entry = json.loads(GarmentResponse.model_validate(g).model_dump_json())
                raw_path = settings.IMAGES_RAW_DIR / g.raw_image_path
                if raw_path.exists():
                    archive_name = f"images/{g.raw_image_path}"
                    zf.write(raw_path, archive_name)
                    entry["image_file"] = archive_name
                else:
                    entry["image_file"] = None
                manifest.append(entry)

            zf.writestr(
                "wardrobe.json",
                json.dumps(
                    {
                        "version": 1,
                        "exported_at": datetime.utcnow().isoformat(),
                        "garments": manifest,
                    },
                    indent=2,
                ),
            )

        buffer.seek(0)
        return buffer

    @staticmethod
    def export_filename() -> str:
        return f"smart-wardrobe-export-{datetime.utcnow().strftime('%Y-%m-%d')}.zip"

    def import_from_zip(self, raw_bytes: bytes) -> dict[str, int]:
        """Import every entry from a previously exported .zip. Additive
        merge, not an overwrite - every entry becomes a brand-new garment
        with a fresh id and its own copied image file, regardless of what
        was already in the wardrobe. Entries whose image is missing from
        the archive, or whose metadata fails validation, are skipped rather
        than aborting the whole import.

        Raises ValueError for a malformed archive (not a zip, or missing
        wardrobe.json/invalid JSON) - the caller maps that to a 400.
        """
        try:
            zf = zipfile.ZipFile(io.BytesIO(raw_bytes))
        except zipfile.BadZipFile as e:
            raise ValueError("File is not a valid .zip export") from e

        try:
            manifest = json.loads(zf.read("wardrobe.json"))
        except KeyError as e:
            raise ValueError("Zip is missing wardrobe.json") from e
        except json.JSONDecodeError as e:
            raise ValueError("wardrobe.json is not valid JSON") from e

        archive_names = set(zf.namelist())
        imported = 0
        skipped = 0

        for entry in manifest.get("garments", []):
            image_file = entry.get("image_file")
            if not image_file or image_file not in archive_names:
                skipped += 1
                continue

            try:
                garment_data = GarmentCreate(
                    name=entry.get("name", "Imported garment"),
                    brand=entry.get("brand"),
                    type=entry.get("type", "top"),
                    season=entry.get("season", "all_season"),
                    size=entry.get("size"),
                    material=entry.get("material"),
                    color_name=entry.get("color_name", "Unknown"),
                    color_hex=entry.get("color_hex", "#4a4a4a"),
                    pattern=entry.get("pattern", "solid"),
                    formality=entry.get("formality", 1),
                    tags=entry.get("tags", []),
                )
            except ValidationError:
                skipped += 1
                continue

            image_bytes = zf.read(image_file)
            ext = Path(image_file).suffix or ".jpg"
            raw_filename = f"{uuid.uuid4()}{ext}"
            raw_path = settings.IMAGES_RAW_DIR / raw_filename
            with open(raw_path, "wb") as f:
                f.write(image_bytes)

            processed_filename = f"{uuid.uuid4()}.png"
            processed_path = settings.IMAGES_PROCESSED_GARMENTS_DIR / processed_filename
            shutil.copy2(raw_path, processed_path)

            garment = Garment(
                **garment_data.model_dump(),
                raw_image_path=raw_filename,
                processed_image_path=processed_filename,
            )
            self.repo.create(garment)
            imported += 1

        return {"imported": imported, "skipped": skipped}
