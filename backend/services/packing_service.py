import itertools
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

from backend.models.garment import Garment, Outfit
from backend.repositories import GarmentRepository, OutfitRepository
from backend.services.outfit_composer import OutfitComposer
from backend.services.style_engine import StyleEngine


@dataclass
class PackingItem:
    """An item in the packing list."""

    garment: Garment
    outfits_used: int
    versatility_score: float  # How many different outfits it can pair with


@dataclass
class PackingResult:
    """Result of packing optimization."""

    outfits: list[dict[str, Any]]
    packing_list: list[PackingItem]
    total_items: int
    days_covered: int
    mix_and_match_ratio: float
    garment_ids_used: list[int]


class PackingService:
    """Optimize packing for N days with minimal items and maximum mix-and-match."""

    def __init__(self, session: Session):
        self.session = session
        self.garment_repo = GarmentRepository(session)
        self.outfit_repo = OutfitRepository(session)
        self.style_engine = StyleEngine(session)
        self.composer = OutfitComposer(session)

    def plan_packing(
        self,
        days: int,
        occasion: str = "travel",
        season: str = "all_season",
        max_items: int = 15,
        garment_ids: list[int] | None = None,
        must_include_ids: list[int] | None = None,
    ) -> PackingResult:
        """
        Generate optimal packing list for N days.

        Algorithm:
        1. Start with must-include items
        2. Generate all valid outfit combinations
        3. Use greedy set cover to select minimum items covering N days
        4. Prioritize items with highest versatility (pair with most other items)
        """
        # Get available garments
        if garment_ids:
            garments = self.garment_repo.get_by_ids(garment_ids)
        else:
            garments = self.garment_repo.get_all(limit=500)

        # Filter by season
        if season != "all_season":
            seasonal = [g for g in garments if g.season == season or g.season == "all_season"]
            if seasonal:
                garments = seasonal

        if len(garments) < 2:
            raise ValueError("Not enough garments for packing")

        # Handle must-include
        must_include = []
        if must_include_ids:
            must_include = [g for g in garments if g.id in must_include_ids]
            if len(must_include) > max_items:
                raise ValueError("Must-include items exceed max_items limit")

        # Generate all valid outfits from available garments
        all_outfits = self._generate_all_outfits(garments, occasion)

        if not all_outfits:
            raise ValueError("No valid outfits can be created from available garments")

        # Score all outfits
        for outfit_data in all_outfits:
            mock_outfit = Outfit(occasion=occasion, season=season)
            score = self.style_engine.score_outfit(mock_outfit, occasion, season)
            outfit_data["score"] = score.total
            outfit_data["score_breakdown"] = score.to_dict()

        # Sort by score descending
        all_outfits.sort(key=lambda x: x["score"], reverse=True)

        # Greedy selection: build packing list covering N days
        selected_outfits = []
        selected_garment_ids: set[int] = set(g.id for g in must_include)
        available_outfits = all_outfits.copy()

        # Add must-include items to selected
        for item in must_include:
            pass  # Already in selected_garment_ids

        for day in range(days):
            best_outfit = None

            for outfit_data in available_outfits:
                garment_ids = set(outfit_data["garment_ids"])

                # Check if adding this outfit stays within max_items
                new_items = garment_ids - selected_garment_ids
                if len(selected_garment_ids) + len(new_items) > max_items:
                    continue

                # Check if we already have too many similar outfits
                if self._too_similar(outfit_data, selected_outfits):
                    continue

                best_outfit = outfit_data
                break

            if best_outfit:
                selected_outfits.append(best_outfit)
                selected_garment_ids.update(best_outfit["garment_ids"])

                # Remove used outfits from available
                available_outfits = [
                    o for o in available_outfits if not self._too_similar(o, [best_outfit])
                ]
            else:
                # No more outfits fit in budget, break
                break

        # If we didn't get enough days, relax constraints
        if len(selected_outfits) < days:
            # Try without similarity filter
            for outfit_data in all_outfits:
                if outfit_data not in selected_outfits:
                    garment_ids = set(outfit_data["garment_ids"])
                    new_items = garment_ids - selected_garment_ids
                    if len(selected_garment_ids) + len(new_items) <= max_items:
                        selected_outfits.append(outfit_data)
                        selected_garment_ids.update(garment_ids)
                        if len(selected_outfits) >= days:
                            break

        # Calculate packing list with versatility scores
        packing_items = self._calculate_versatility(
            list(selected_garment_ids), selected_outfits, all_outfits
        )

        # Calculate metrics
        total_items = len(selected_garment_ids)
        days_covered = len(selected_outfits)
        mix_match_ratio = total_items / (days_covered * 3) if days_covered > 0 else 0

        return PackingResult(
            outfits=selected_outfits[:days],
            packing_list=packing_items,
            total_items=total_items,
            days_covered=days_covered,
            mix_and_match_ratio=round(mix_match_ratio, 2),
            garment_ids_used=list(selected_garment_ids),
        )

    def _generate_all_outfits(self, garments: list[Garment], occasion: str) -> list[dict[str, Any]]:
        """Generate all valid outfit combinations from garments."""
        by_type = defaultdict(list)
        for g in garments:
            by_type[g.type].append(g)

        templates = self.composer._get_templates(occasion)

        outfits = []
        for template in templates:
            type_lists = [by_type.get(t, []) for t in template]
            if not all(type_lists):
                continue

            for combo in itertools.product(*type_lists):
                if len(set(g.id for g in combo)) == len(combo):
                    outfits.append(
                        {
                            "garment_ids": [g.id for g in combo],
                            "garment_types": [g.type for g in combo],
                            "template": template,
                        }
                    )

        return outfits

    def _too_similar(
        self, outfit: dict[str, Any], selected: list[dict[str, Any]], threshold: float = 0.7
    ) -> bool:
        """Check if outfit is too similar to already selected ones."""
        outfit_ids = set(outfit["garment_ids"])

        for sel in selected:
            sel_ids = set(sel["garment_ids"])
            intersection = len(outfit_ids & sel_ids)
            union = len(outfit_ids | sel_ids)
            similarity = intersection / union if union > 0 else 0

            if similarity >= threshold:
                return True

        return False

    def _calculate_versatility(
        self,
        selected_ids: list[int],
        selected_outfits: list[dict[str, Any]],
        all_outfits: list[dict[str, Any]],
    ) -> list[PackingItem]:
        """Calculate versatility score for each selected garment."""
        garment_outfit_count = defaultdict(int)
        garment_pairings = defaultdict(set)

        # Count how many selected outfits each garment appears in
        for outfit in selected_outfits:
            for gid in outfit["garment_ids"]:
                garment_outfit_count[gid] += 1

        # Count how many OTHER selected garments each garment pairs with
        for outfit in selected_outfits:
            ids = outfit["garment_ids"]
            for gid in ids:
                for other in ids:
                    if other != gid:
                        garment_pairings[gid].add(other)

        # Also consider potential pairings in all valid outfits
        for outfit in all_outfits:
            ids = outfit["garment_ids"]
            for gid in ids:
                if gid in selected_ids:
                    for other in ids:
                        if other != gid and other in selected_ids:
                            garment_pairings[gid].add(other)

        items = []
        for gid in selected_ids:
            garment = self.garment_repo.get_by_id(gid)
            if not garment:
                continue

            outfits_used = garment_outfit_count.get(gid, 0)
            pairing_count = len(garment_pairings.get(gid, set()))

            # Versatility = pairings / max_possible_pairings
            max_pairings = len(selected_ids) - 1
            versatility = pairing_count / max_pairings if max_pairings > 0 else 0

            items.append(
                PackingItem(
                    garment=garment,
                    outfits_used=outfits_used,
                    versatility_score=round(versatility, 3),
                )
            )

        # Sort by versatility descending
        items.sort(key=lambda x: x.versatility_score, reverse=True)
        return items

    def get_item_suggestions(
        self, days: int, occasion: str, season: str, current_garment_ids: list[int]
    ) -> list[dict[str, Any]]:
        """Get suggested items to add to packing list."""
        garments = self.garment_repo.get_all(limit=500)

        if season != "all_season":
            seasonal = [g for g in garments if g.season == season or g.season == "all_season"]
            if seasonal:
                garments = seasonal

        # Exclude already selected
        garments = [g for g in garments if g.id not in current_garment_ids]

        # Score each garment by how many new outfits it would enable
        suggestions = []
        for garment in garments:
            # Quick versatility estimate: how many types does it complement?
            new_outfits = 0
            for template in self.composer._get_templates(occasion):
                if garment.type in template:
                    # Count how many other types we have
                    other_types = [t for t in template if t != garment.type]
                    has_all = all(
                        any(
                            g.id in current_garment_ids and g.type == t
                            for g in self.garment_repo.get_all(limit=500)
                        )
                        for t in other_types
                    )
                    if has_all:
                        new_outfits += 1

            if new_outfits > 0:
                suggestions.append(
                    {
                        "garment": garment,
                        "new_outfits_enabled": new_outfits,
                        "versatility_bonus": new_outfits * 10,
                    }
                )

        suggestions.sort(key=lambda x: x["versatility_bonus"], reverse=True)
        return suggestions[:10]
