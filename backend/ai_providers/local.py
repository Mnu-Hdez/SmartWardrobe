from typing import Any

from backend.ai_providers import AIProvider
from backend.models.schemas import GarmentRead, OutfitRead, OutfitWithGarments


class LocalRulesProvider(AIProvider):
    """Local rules-based AI provider - no external API calls."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.name = "local"

    def get_provider_name(self) -> str:
        return self.name

    async def health_check(self) -> bool:
        return True

    async def enhance_recommendation(
        self,
        outfit: OutfitRead,
        context: str = "",
        user_preferences: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Enhance recommendation using local style rules."""
        garments = outfit.garments if hasattr(outfit, "garments") and outfit.garments else []

        # Generate description based on garment properties
        description_parts = []

        if garments:
            # Describe the outfit composition
            top_items = [g for g in garments if g.type in ["top", "dress", "outerwear"]]
            bottom_items = [g for g in garments if g.type in ["bottom", "shoes"]]
            accessories = [g for g in garments if g.type == "accessory"]

            if len(garments) == 1:
                item = garments[0]
                description_parts.append(
                    f"A {item.color_name} {item.type} perfect for {outfit.occasion}."
                )
            elif top_items and bottom_items:
                top = top_items[0]
                bottom = bottom_items[0]
                description_parts.append(
                    f"Pair the {top.color_name} {top.type} with {bottom.color_name} {bottom.type} "
                    f"for a {self._get_style_description(outfit.formality)} look."
                )

            if accessories:
                acc = accessories[0]
                description_parts.append(f"Complete with a {acc.color_name} {acc.type}.")

        # Add context-aware advice
        if context:
            description_parts.append(f"Perfect for {context}.")

        # Generate style tips based on rules
        style_tips = self._generate_style_tips(garments, outfit)

        return {
            "enhanced_description": " ".join(description_parts)
            if description_parts
            else f"A stylish {outfit.occasion} outfit.",
            "style_tips": style_tips,
            "confidence": 0.85,
        }

    async def generate_outfit_description(
        self, garments: list[GarmentRead], occasion: str, context: str = ""
    ) -> str:
        """Generate description for a set of garments."""
        if not garments:
            return f"A {occasion} outfit."

        parts = []
        colors = [g.color_name for g in garments]
        types = [g.type for g in garments]

        if len(set(colors)) == 1:
            parts.append(f"Monochromatic {colors[0]} ensemble")
        elif len(colors) == 2:
            parts.append(f"{colors[0]} and {colors[1]} combination")
        else:
            parts.append(f"Multi-color outfit with {', '.join(colors[:-1])} and {colors[-1]}")

        parts.append(f"featuring {', '.join(types)}")
        parts.append(f"for {occasion}")

        if context:
            parts.append(f"({context})")

        return ". ".join(parts) + "."

    def _get_style_description(self, formality: int) -> str:
        styles = {1: "casual", 2: "smart-casual", 3: "business-casual", 4: "formal", 5: "black-tie"}
        return styles.get(formality, "stylish")

    def _generate_style_tips(self, garments: list[GarmentRead], outfit: OutfitRead) -> list[str]:
        tips = []

        # Color harmony tips
        colors = [g.color_name for g in garments]
        if len(set(colors)) <= 2:
            tips.append("Monochromatic or two-tone palette creates cohesive look")
        elif len(colors) >= 4:
            tips.append("Consider reducing color count for more polished appearance")

        # Pattern tips
        patterns = [g.pattern for g in garments if g.pattern != "solid"]
        if len(patterns) >= 2:
            tips.append("Multiple patterns - ensure different scales for balance")
        elif len(patterns) == 1:
            tips.append(f"Single {patterns[0]} pattern adds visual interest")

        # Formality tips
        formalities = [g.formality for g in garments]
        if max(formalities) - min(formalities) > 2:
            tips.append("Mix of formalities - anchor with most formal piece")

        # Occasion-specific tips
        if outfit.occasion == "work":
            tips.append("Ensure shoulders covered and hemlines appropriate")
        elif outfit.occasion == "party":
            tips.append("Add statement accessory to elevate the look")
        elif outfit.occasion == "casual":
            tips.append("Roll sleeves or cuff pants for relaxed vibe")

        return tips[:5]  # Limit to 5 tips
