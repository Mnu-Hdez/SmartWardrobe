# Smart Wardrobe - AI Providers
# NVIDIA NIM integration

import logging

import requests

from backend.core.config import settings

logger = logging.getLogger(__name__)


class NVIDIANIMProvider:
    """NVIDIA NIM integration for advanced AI recommendations"""

    def __init__(self):
        self.name = "nim"
        self.api_key = settings.NIM_API_KEY
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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
        """Ask NIM to suggest tags for a garment based on its metadata.
        Falls back to the local heuristic provider if NIM is unavailable
        or the response can't be parsed - suggestions are non-critical,
        so a broken NIM call should never block adding a garment."""
        from backend.ai_providers.local import LocalRulesProvider

        def fallback() -> list[str]:
            return LocalRulesProvider().suggest_tags(
                name, garment_type, color_name, material, pattern, brand, season, existing_tags
            )

        if not self.api_key:
            logger.warning("NIM API key not configured, falling back to local tag suggestions")
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
            "Do not repeat the type or color verbatim unless genuinely useful. "
            "Respond ONLY with a JSON array of strings, nothing else.\n\n"
            + "\n".join(details)
        )

        try:
            response = self._call_nim(prompt)
            content = response["choices"][0]["message"]["content"]
            import json

            tags = json.loads(content)
            if not isinstance(tags, list):
                raise ValueError("NIM tag response was not a list")
            cleaned = []
            existing_lower = {t.lower() for t in (existing_tags or [])}
            for t in tags:
                t = str(t).strip().lower()
                if t and t not in existing_lower and t not in cleaned:
                    cleaned.append(t)
            return cleaned[:6] if cleaned else fallback()
        except Exception as e:
            logger.error(f"NIM tag suggestion failed: {e}, falling back to local")
            return fallback()

    def analyze_image(self, image_bytes: bytes, mime_type: str) -> dict:
        """Ask a NIM vision-language model to guess garment metadata from the
        photo. Falls back to the local color-only heuristic on any failure
        (missing key, model unavailable, bad JSON) so a flaky vision call
        never blocks the manual form."""
        import base64
        import json

        from backend.ai_providers.local import LocalRulesProvider

        valid_types = {"top", "bottom", "dress", "outerwear", "shoes", "accessory"}
        valid_patterns = {
            "solid", "striped", "checked", "floral", "polka_dot",
            "geometric", "abstract", "animal_print", "paisley", "houndstooth",
        }
        empty = {
            "name": None, "type": None, "color_name": None, "color_hex": None,
            "material": None, "pattern": None, "formality": None, "tags": [],
        }

        if not self.api_key:
            logger.warning("NIM API key not configured, falling back to local color analysis")
            return LocalRulesProvider().analyze_image(image_bytes, mime_type)

        prompt = (
            "Look at this photo of a single clothing item and guess its attributes. "
            "Respond ONLY with a JSON object with these exact keys:\n"
            '- "name": short descriptive name\n'
            f'- "type": one of {sorted(valid_types)}\n'
            '- "color_name": dominant color in plain English\n'
            '- "color_hex": hex code approximating the dominant color\n'
            '- "material": best guess fabric/material, or null if unclear\n'
            f'- "pattern": one of {sorted(valid_patterns)}\n'
            '- "formality": integer 1-5 (1=very casual, 5=black tie)\n'
            '- "tags": up to 5 short lowercase style/use-case tags\n'
            "Use null for anything you can't tell confidently. No prose, JSON only."
        )

        try:
            b64 = base64.b64encode(image_bytes).decode("ascii")
            payload = {
                "model": settings.NIM_VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                            },
                        ],
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 500,
            }
            response = requests.post(
                f"{self.base_url}/chat/completions", headers=self.headers, json=payload, timeout=30
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)

            result = dict(empty)
            if data.get("name"):
                result["name"] = str(data["name"])[:200]
            if data.get("type") in valid_types:
                result["type"] = data["type"]
            if data.get("color_name"):
                result["color_name"] = str(data["color_name"])[:50]
            hex_val = data.get("color_hex")
            if isinstance(hex_val, str) and len(hex_val) == 7 and hex_val.startswith("#"):
                result["color_hex"] = hex_val
            if data.get("material"):
                result["material"] = str(data["material"])[:100]
            if data.get("pattern") in valid_patterns:
                result["pattern"] = data["pattern"]
            formality = data.get("formality")
            if isinstance(formality, int) and 1 <= formality <= 5:
                result["formality"] = formality
            tags = data.get("tags")
            if isinstance(tags, list):
                result["tags"] = [str(t).strip().lower() for t in tags if str(t).strip()][:5]
            return result
        except Exception as e:
            logger.error(f"NIM image analysis failed: {e}, falling back to local color analysis")
            return LocalRulesProvider().analyze_image(image_bytes, mime_type)

    def _call_nim(self, prompt: str) -> dict:
        """Call NIM API"""
        payload = {
            "model": "meta/llama-3.1-70b-instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional fashion stylist. Respond only with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        response = requests.post(
            f"{self.base_url}/chat/completions", headers=self.headers, json=payload, timeout=30
        )
        response.raise_for_status()
        return response.json()
