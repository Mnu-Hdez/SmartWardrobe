# Smart Wardrobe - AI Providers
# Google Gemini (Google AI Studio) integration

import base64
import json
import logging

import requests

from backend.core.config import settings
from backend.models.garment import Garment, Outfit
from backend.models.schemas import OutfitRecommendationRequest, PackingPlanRequest

logger = logging.getLogger(__name__)

VALID_TYPES = {"top", "bottom", "dress", "outerwear", "shoes", "accessory"}
VALID_PATTERNS = {
    "solid", "striped", "checked", "floral", "polka_dot",
    "geometric", "abstract", "animal_print", "paisley", "houndstooth",
}


class GeminiProvider:
    """Google Gemini integration via Google AI Studio (Generative Language API)."""

    def __init__(self):
        self.name = "gemini"
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def _endpoint(self) -> str:
        return f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"

    def _call_gemini(self, parts: list[dict], temperature: float = 0.4) -> dict:
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        response = requests.post(self._endpoint(), json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def _extract_text(self, response: dict) -> str:
        return response["candidates"][0]["content"]["parts"][0]["text"]

    def suggest_tags(
        self,
        name: str,
        garment_type: str,
        color_name: str | None = None,
        material: str | None = None,
        pattern: str | None = None,
        brand: str | None = None,
        season: str | None = None,
        existing_tags: list[str] | None = None,
    ) -> list[str]:
        from backend.ai_providers.local import LocalRulesProvider

        def fallback() -> list[str]:
            return LocalRulesProvider().suggest_tags(
                name, garment_type, color_name, material, pattern, brand, season, existing_tags
            )

        if not self.api_key:
            logger.warning("Gemini API key not configured, falling back to local tag suggestions")
            return fallback()

        details = [f"name: {name}", f"type: {garment_type}"]
        if color_name:
            details.append(f"color: {color_name}")
        if material:
            details.append(f"material: {material}")
        if pattern:
            details.append(f"pattern: {pattern}")
        if brand:
            details.append(f"brand: {brand}")
        if season:
            details.append(f"season: {season}")
        if existing_tags:
            details.append(f"tags already applied (do not repeat these): {', '.join(existing_tags)}")

        prompt = (
            "Suggest up to 6 short, lowercase, single/double-word tags for this garment, "
            "useful for search and outfit matching (style, vibe, fabric feel, use-case, etc). "
            "Respond ONLY with a JSON array of strings, nothing else.\n\n" + "\n".join(details)
        )

        try:
            response = self._call_gemini([{"text": prompt}])
            tags = json.loads(self._extract_text(response))
            if not isinstance(tags, list):
                raise ValueError("Gemini tag response was not a list")
            existing_lower = {t.lower() for t in (existing_tags or [])}
            cleaned = []
            for t in tags:
                t = str(t).strip().lower()
                if t and t not in existing_lower and t not in cleaned:
                    cleaned.append(t)
            return cleaned[:6] if cleaned else fallback()
        except Exception as e:
            logger.error(f"Gemini tag suggestion failed: {e}, falling back to local")
            return fallback()

    def analyze_image(self, image_bytes: bytes, mime_type: str) -> dict:
        """Ask Gemini to guess garment metadata straight from the photo.
        Returns a dict matching ImageAnalysisResponse fields (minus `provider`,
        which the caller sets). Never raises - falls back to an empty guess
        so a flaky vision call never blocks the manual form."""
        empty = {
            "name": None, "type": None, "color_name": None, "color_hex": None,
            "material": None, "pattern": None, "formality": None, "tags": [],
        }
        if not self.api_key:
            logger.warning("Gemini API key not configured, cannot analyze image")
            return empty

        prompt = (
            "Look at this photo of a single clothing item and guess its attributes. "
            "Respond ONLY with a JSON object with these exact keys:\n"
            '- "name": short descriptive name (e.g. "Navy Wool Overcoat")\n'
            f'- "type": one of {sorted(VALID_TYPES)}\n'
            '- "color_name": the dominant color in plain English (e.g. "Navy Blue")\n'
            '- "color_hex": a hex code approximating the dominant color, e.g. "#1a2b4c"\n'
            '- "material": best guess fabric/material, or null if unclear\n'
            f'- "pattern": one of {sorted(VALID_PATTERNS)}\n'
            '- "formality": integer 1-5 (1=very casual, 5=black tie)\n'
            '- "tags": up to 5 short lowercase style/use-case tags\n'
            "If you cannot tell a field confidently, use null for it. No prose, JSON only."
        )

        try:
            b64 = base64.b64encode(image_bytes).decode("ascii")
            parts = [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_type, "data": b64}},
            ]
            response = self._call_gemini(parts, temperature=0.2)
            data = json.loads(self._extract_text(response))

            result = dict(empty)
            if data.get("name"):
                result["name"] = str(data["name"])[:200]
            if data.get("type") in VALID_TYPES:
                result["type"] = data["type"]
            if data.get("color_name"):
                result["color_name"] = str(data["color_name"])[:50]
            hex_val = data.get("color_hex")
            if isinstance(hex_val, str) and len(hex_val) == 7 and hex_val.startswith("#"):
                result["color_hex"] = hex_val
            if data.get("material"):
                result["material"] = str(data["material"])[:100]
            if data.get("pattern") in VALID_PATTERNS:
                result["pattern"] = data["pattern"]
            formality = data.get("formality")
            if isinstance(formality, int) and 1 <= formality <= 5:
                result["formality"] = formality
            tags = data.get("tags")
            if isinstance(tags, list):
                result["tags"] = [str(t).strip().lower() for t in tags if str(t).strip()][:5]
            return result
        except Exception as e:
            logger.error(f"Gemini image analysis failed: {e}")
            return empty

    def recommend_outfits(
        self, request: OutfitRecommendationRequest, garments: list[Garment]
    ) -> list[Outfit]:
        from backend.ai_providers.local import LocalRulesProvider

        if not self.api_key:
            return LocalRulesProvider().recommend_outfits(request, garments)

        try:
            context = "\n".join(
                f"- {g.name} ({g.type}, {g.color_name}, formality: {g.formality}/5, "
                f"season: {g.season}, pattern: {g.pattern})"
                for g in garments
            )
            prompt = (
                f"You are a professional stylist. Recommend {request.top_n} outfit(s) for a "
                f"{request.occasion} occasion in {request.season} season.\n\nAvailable garments:\n"
                f"{context}\n\nReturn a JSON array of outfits, each with: name, garments "
                "(list of garment names used), score (0-100), score_breakdown "
                "(color_harmony, formality_match, pattern_balance, seasonal), tips (1-2 strings)."
            )
            response = self._call_gemini([{"text": prompt}], temperature=0.7)
            outfits_data = json.loads(self._extract_text(response))
            outfits = []
            for o in outfits_data:
                outfits.append(
                    Outfit(
                        name=o.get("name", "Recommended Outfit"),
                        occasion=request.occasion,
                        season=request.season,
                        score=o.get("score", 75),
                        score_breakdown=o.get("score_breakdown", {}),
                        ai_tips=o.get("tips", []),
                    )
                )
            return outfits
        except Exception as e:
            logger.error(f"Gemini recommendation failed: {e}, falling back to local")
            return LocalRulesProvider().recommend_outfits(request, garments)

    def create_packing_plan(self, request: PackingPlanRequest, garments: list[Garment]) -> dict:
        from backend.ai_providers.local import LocalRulesProvider

        return LocalRulesProvider().create_packing_plan(request, garments)
