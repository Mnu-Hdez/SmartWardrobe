import itertools
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlmodel import Session, select

from backend.core.config import get_settings
from backend.models.garment import Garment, Outfit, OutfitGarmentLink
from backend.repositories import GarmentRepository, OutfitRepository
from backend.services.style_engine import StyleEngine, StyleScore


@dataclass
class OutfitCandidate:
    """An outfit candidate with its garments and score."""

    garments: list[Garment]
    score: StyleScore
    occasion: str
    season: str

    def to_outfit_dict(self) -> dict[str, Any]:
        return {
            "garments": [g.id for g in self.garments],
            "score": self.score.to_dict(),
            "occasion": self.occasion,
            "season": self.season,
        }


class OutfitComposer:
    """Generate top-N diverse outfits from wardrobe."""

    def __init__(self, session: Session):
        self.session = session
        self.settings = get_settings()
        self.garment_repo = GarmentRepository(session)
        self.outfit_repo = OutfitRepository(session)
        self.style_engine = StyleEngine(session)

    def compose_outfits(
        self,
        occasion: str = "casual",
        season: str = "all_season",
        formality: int | None = None,
        top_n: int = 5,
        exclude_garment_ids: list[int] | None = None,
        min_score: float = 30.0,
        diversity_factor: float = 0.3,
    ) -> list[OutfitCandidate]:
        """
        Generate top-N diverse outfits.

        Args:
            occasion: Occasion type (casual, work, party, wedding, etc.)
            season: Season filter
            formality: Target formality level (1-5)
            top_n: Number of outfits to return
            exclude_garment_ids: Garments to exclude
            min_score: Minimum score threshold
            diversity_factor: How much to penalize similar outfits (0-1)
        """
        # Get available garments
        garments = self.garment_repo.get_all(limit=500)

        # Apply filters
        garments = self._filter_garments(garments, season, formality, exclude_garment_ids)

        if len(garments) < 2:
            return []

        # Group by type for efficient combination generation
        by_type = defaultdict(list)
        for g in garments:
            by_type[g.type].append(g)

        # Define valid outfit templates per occasion
        templates = self._get_templates(occasion)

        # Generate all valid combinations
        candidates = []
        for template in templates:
            # Check if we have all required types
            type_lists = [by_type.get(t, []) for t in template]
            if not all(type_lists):
                continue

            # Generate combinations
            for combo in itertools.product(*type_lists):
                # Ensure unique garments
                if len(set(g.id for g in combo)) == len(combo):
                    candidates.append(list(combo))

        if not candidates:
            return []

        # Score all candidates
        scored_candidates = []
        for garment_list in candidates:
            mock_outfit = Outfit(occasion=occasion, season=season)
            score = self.style_engine.score_outfit(mock_outfit, occasion, season)
            # Override with actual combo scoring
            score = self._score_garment_combo(garment_list, occasion, season)

            if score.total >= min_score:
                scored_candidates.append(
                    OutfitCandidate(
                        garments=garment_list, score=score, occasion=occasion, season=season
                    )
                )

        if not scored_candidates:
            return []

        # Sort by score descending
        scored_candidates.sort(key=lambda c: c.score.total, reverse=True)

        # Apply diversity filtering
        diverse = self._apply_diversity_filter(scored_candidates, diversity_factor)

        return diverse[:top_n]

    def recommend(
        self,
        occasion: str = "casual",
        season: str = "all_season",
        formality: int | None = None,
        garment_ids: list[int] | None = None,
        exclude_garment_ids: list[int] | None = None,
        top_n: int = 5,
    ) -> list[tuple[Outfit, float]]:
        """
        Generate outfit recommendations matching the API endpoint expectations.
        Returns list of (outfit, score) tuples.
        """
        candidates = self.compose_outfits(
            occasion=occasion,
            season=season,
            formality=formality,
            top_n=top_n,
            exclude_garment_ids=exclude_garment_ids,
        )

        # Create actual Outfit objects from candidates
        results = []
        for candidate in candidates:
            outfit = self._create_outfit_from_candidate(candidate)
            if outfit:
                results.append((outfit, candidate.score.total))

        return results

    def _create_outfit_from_candidate(self, candidate: OutfitCandidate) -> Outfit | None:
        """Create an Outfit database object from a candidate."""
        try:
            outfit = Outfit(
                name=f"{candidate.occasion.title()} Outfit",
                occasion=candidate.occasion,
                season=candidate.season,
                score=candidate.score.total,
            )
            self.session.add(outfit)
            self.session.commit()
            self.session.refresh(outfit)

            # Add garment links
            for pos, garment in enumerate(candidate.garments):
                link = OutfitGarmentLink(
                    outfit_id=outfit.id, garment_id=garment.id, position=pos
                )
                self.session.add(link)

            self.session.commit()
            self.session.refresh(outfit)
            return outfit
        except Exception:
            self.session.rollback()
            return None

    def _filter_garments(
        self,
        garments: list[Garment],
        season: str,
        formality: int | None,
        exclude_ids: list[int] | None,
    ) -> list[Garment]:
        """Filter garments by criteria."""
        filtered = garments

        if season != "all_season":
            filtered = [g for g in filtered if g.season == season or g.season == "all_season"]

        if formality is not None:
            # Allow ±1 formality difference
            filtered = [g for g in filtered if abs(g.formality - formality) <= 1]

        if exclude_ids:
            filtered = [g for g in filtered if g.id not in exclude_ids]

        return filtered

    def _get_templates(self, occasion: str) -> list[list[str]]:
        """Get outfit templates for occasion."""
        templates = {
            "casual": [
                ["top", "bottom"],
                ["top", "bottom", "shoes"],
                ["top", "bottom", "outerwear"],
                ["dress"],
                ["dress", "shoes"],
                ["top", "bottom", "accessory"],
            ],
            "work": [
                ["top", "bottom"],
                ["top", "bottom", "outerwear"],
                ["top", "bottom", "shoes"],
                ["dress"],
                ["dress", "outerwear"],
            ],
            "business": [
                ["top", "bottom"],
                ["top", "bottom", "outerwear"],
                ["dress"],
                ["dress", "outerwear"],
            ],
            "party": [
                ["top", "bottom"],
                ["top", "bottom", "shoes"],
                ["dress"],
                ["dress", "shoes"],
                ["top", "bottom", "outerwear"],
            ],
            "wedding": [
                ["top", "bottom"],
                ["top", "bottom", "outerwear"],
                ["dress"],
                ["dress", "outerwear"],
                ["dress", "shoes", "accessory"],
            ],
            "formal": [
                ["top", "bottom"],
                ["top", "bottom", "outerwear"],
                ["dress"],
                ["dress", "outerwear"],
            ],
            "travel": [
                ["top", "bottom"],
                ["top", "bottom", "shoes"],
                ["top", "bottom", "outerwear"],
                ["dress"],
                ["dress", "shoes"],
                ["top", "bottom", "accessory"],
            ],
        }
        return templates.get(occasion.lower(), templates["casual"])

    def _score_garment_combo(
        self, garments: list[Garment], occasion: str, season: str
    ) -> StyleScore:
        """Score a specific combination of garments."""
        # Create a temporary outfit for scoring
        mock_outfit = Outfit(
            occasion=occasion,
            season=season,
            formality=int(sum(g.formality for g in garments) / len(garments)),
        )

        # Override _get_garments to use our specific list
        original = self.style_engine._get_garments
        self.style_engine._get_garments = lambda o: garments

        try:
            score = self.style_engine.score_outfit(mock_outfit, occasion, season)
        finally:
            self.style_engine._get_garments = original

        return score

    def _apply_diversity_filter(
        self, candidates: list[OutfitCandidate], diversity_factor: float
    ) -> list[OutfitCandidate]:
        """Filter candidates to ensure diversity."""
        if diversity_factor <= 0 or len(candidates) <= 1:
            return candidates

        selected = [candidates[0]]  # Always include top scorer

        for candidate in candidates[1:]:
            # Check similarity to already selected
            max_similarity = 0.0
            for sel in selected:
                sim = self._calculate_similarity(candidate, sel)
                max_similarity = max(max_similarity, sim)

            # Apply diversity penalty
            diversity_penalty = max_similarity * diversity_factor * 100
            adjusted_score = candidate.score.total - diversity_penalty

            # If still competitive, include it
            if adjusted_score >= selected[-1].score.total * 0.7:
                candidate.score.total = adjusted_score
                selected.append(candidate)

            if len(selected) >= len(candidates):
                break

        # Re-sort by adjusted score
        selected.sort(key=lambda c: c.score.total, reverse=True)
        return selected

    def _calculate_similarity(self, c1: OutfitCandidate, c2: OutfitCandidate) -> float:
        """Calculate similarity between two outfit candidates (0-1)."""
        ids1 = set(g.id for g in c1.garments)
        ids2 = set(g.id for g in c2.garments)

        if not ids1 or not ids2:
            return 0.0

        intersection = len(ids1 & ids2)
        union = len(ids1 | ids2)

        return intersection / union if union > 0 else 0.0

    def save_outfit(self, candidate: OutfitCandidate, name: str | None = None) -> Outfit:
        """Save an outfit candidate to database."""
        outfit = Outfit(
            name=name or f"{candidate.occasion.title()} Outfit #{candidate.score.total:.0f}",
            occasion=candidate.occasion,
            season=candidate.season,
            score=candidate.score.total,
        )
        self.session.add(outfit)
        self.session.flush()  # Get ID

        # Add garment links
        for pos, garment in enumerate(candidate.garments):
            link = OutfitGarmentLink(outfit_id=outfit.id, garment_id=garment.id, position=pos)
            self.session.add(link)

        self.session.commit()
        self.session.refresh(outfit)
        return outfit

    def get_outfit_with_details(self, outfit_id: int) -> dict[str, Any] | None:
        """Get outfit with full garment details."""
        outfit = self.session.get(Outfit, outfit_id)
        if not outfit:
            return None

        links = self.session.exec(
            select(OutfitGarmentLink).where(OutfitGarmentLink.outfit_id == outfit_id)
        ).all()

        garment_ids = [link.garment_id for link in links]
        garments = self.garment_repo.get_by_ids(garment_ids)

        # Score it
        score = self.style_engine.score_outfit(outfit, outfit.occasion, outfit.season)

        return {
            "id": outfit.id,
            "name": outfit.name,
            "occasion": outfit.occasion,
            "season": outfit.season,
            "formality": outfit.formality,
            "score": score.total,
            "score_breakdown": score.to_dict(),
            "is_packing": outfit.is_packing,
            "created_at": outfit.created_at,
            "updated_at": outfit.updated_at,
            "garments": [
                {
                    "id": g.id,
                    "name": g.name,
                    "brand": g.brand,
                    "type": g.type,
                    "color_name": g.color_name,
                    "dominant_color_hex": g.dominant_color_hex,
                    "pattern": g.pattern,
                    "formality": g.formality,
                    "season": g.season,
                    "material": g.material,
                    "size": g.size,
                    "is_favorite": g.is_favorite,
                    "wear_count": g.wear_count,
                    "raw_image_path": g.raw_image_path,
                    "processed_image_path": g.processed_image_path,
                    "segmentation_mask_path": g.mask_image_path,
                    "notes": None,
                    "created_at": g.created_at,
                    "updated_at": g.updated_at,
                }
                for g in garments
            ],
        }


