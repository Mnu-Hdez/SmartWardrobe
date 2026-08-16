# Smart Wardrobe - Business Logic Services
# High-level operations combining repositories

import json
import random
from datetime import date, datetime, timedelta
from typing import Any

from backend.models.garment import Garment, Outfit, OutfitItem, StyleRule
from backend.models.schemas import (
    GarmentSwapRequest,
    OutfitRecommendationRequest,
    PackingPlanRequest,
    UserFeedbackCreate,
)
from backend.repositories.garment_repo import (
    GarmentRepository,
    OutfitItemRepository,
    OutfitRepository,
    StyleRuleRepository,
)
from backend.repositories.user_feedback_repository import UserFeedbackRepository


def _like_or_dislike(rating: int) -> str:
    return "like" if rating > 0 else "dislike"


class OutfitService:
    """Business logic for outfit recommendations and management"""

    def __init__(
        self,
        session,
        garment_repo: GarmentRepository | None = None,
        outfit_repo: OutfitRepository | None = None,
        item_repo: OutfitItemRepository | None = None,
        rule_repo: StyleRuleRepository | None = None,
        feedback_repo: UserFeedbackRepository | None = None,
    ):
        # Repositories are injectable (DIP) - defaults build the real
        # SQLModel-backed ones from `session` so every existing call site
        # (`OutfitService(session)`) keeps working unchanged, but tests can
        # pass fakes/mocks for any of them without touching a real DB.
        self.garment_repo = garment_repo or GarmentRepository(session)
        self.outfit_repo = outfit_repo or OutfitRepository(session)
        self.item_repo = item_repo or OutfitItemRepository(session)
        self.rule_repo = rule_repo or StyleRuleRepository(session)
        self.feedback_repo = feedback_repo or UserFeedbackRepository(session)

    # ========== OUTFIT RECOMMENDATIONS ==========

    def recommend_outfits(self, request: OutfitRecommendationRequest) -> dict[str, Any]:
        """Generate outfit recommendations based on occasion, season, and rules"""
        start_time = datetime.utcnow()

        # Get filtered garments
        filters = {
            "season": request.season,
        }
        garments = self.garment_repo.get_all(limit=1000, filters=filters)

        # Apply occasion/formality filters
        filtered = self._filter_by_occasion(garments, request.occasion, request.formality)

        if len(filtered) < 2:
            return {
                "outfits": [],
                "total_garments_analyzed": len(filtered),
                "processing_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
            }

        # Generate outfit combinations
        outfits = self._generate_combinations(
            filtered, request.occasion, request.season, request.top_n
        )

        # Apply style rules for scoring
        active_rules = self.rule_repo.get_all(active_only=True)
        for outfit in outfits:
            outfit.score = self._calculate_score(outfit, active_rules)
            outfit.score_breakdown = self._get_score_breakdown(outfit, active_rules)
            outfit.ai_tips = self._generate_tips(outfit)

        # Sort by score descending
        outfits.sort(key=lambda o: o.score or 0, reverse=True)
        outfits = outfits[: request.top_n]

        # Save outfits
        saved_outfits = []
        for outfit in outfits:
            saved = self._save_outfit(outfit)
            saved_outfits.append(saved)

        return {
            "outfits": saved_outfits,
            "total_garments_analyzed": len(filtered),
            "processing_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
        }

    def _filter_by_occasion(
        self, garments: list[Garment], occasion: str, formality: int | None
    ) -> list[Garment]:
        """Filter garments by occasion suitability"""
        # Simple mapping - in reality would use more sophisticated logic
        occasion_formality = {
            "casual": (1, 2),
            "work": (2, 3),
            "party": (3, 4),
            "date": (2, 4),
            "formal": (4, 5),
            "wedding": (4, 5),
            "travel": (1, 3),
        }

        min_form, max_form = occasion_formality.get(occasion, (1, 5))

        if formality:
            min_form = max(min_form, formality)
            max_form = min(max_form, formality)

        return [g for g in garments if min_form <= g.formality <= max_form]

    def _generate_combinations(
        self, garments: list[Garment], occasion: str, season: str, top_n: int
    ) -> list[Outfit]:
        """Generate outfit combinations from available garments.

        Mandatory composition rules:
        - top + bottom + shoes, UNLESS a dress is used (dress replaces
          top + bottom, but shoes are still mandatory either way).
        - in winter, at least one outerwear piece (jacket/coat) is
          mandatory; occasionally two are layered together at once.
        If the wardrobe can't satisfy these (e.g. no shoes at all, or no
        outerwear for a winter look), no combinations can be generated and
        an empty list is returned - callers already handle that case.
        """
        # Group by type
        by_type: dict[str, list[Garment]] = {}
        for g in garments:
            by_type.setdefault(g.type, []).append(g)

        has_top_bottom = bool(by_type.get("top")) and bool(by_type.get("bottom"))
        has_dress = bool(by_type.get("dress"))
        has_shoes = bool(by_type.get("shoes"))
        is_winter = season == "winter"
        has_outerwear = bool(by_type.get("outerwear"))

        if not has_top_bottom and not has_dress:
            return []
        if not has_shoes:
            return []
        if is_winter and not has_outerwear:
            return []

        outfits = []
        attempts = 0
        max_attempts = top_n * 10

        while len(outfits) < top_n and attempts < max_attempts:
            attempts += 1

            outfit_garments = []

            # Base of the outfit: dress, or top+bottom together (never a
            # top/bottom without its pair - a lone top or lone bottom isn't
            # a valid outfit under the new rules).
            use_dress = has_dress and (not has_top_bottom or random.random() < 0.3)
            if use_dress:
                outfit_garments.append(random.choice(by_type["dress"]))
            elif has_top_bottom:
                outfit_garments.append(random.choice(by_type["top"]))
                outfit_garments.append(random.choice(by_type["bottom"]))
            else:
                continue

            # Shoes are always mandatory.
            outfit_garments.append(random.choice(by_type["shoes"]))

            # Outerwear: mandatory in winter (occasionally layering two
            # pieces - jacket + coat at once); optional the rest of the year.
            if is_winter:
                outerwear_pool = by_type["outerwear"]
                first_outerwear = random.choice(outerwear_pool)
                outfit_garments.append(first_outerwear)
                remaining_outerwear = [g for g in outerwear_pool if g.id != first_outerwear.id]
                if remaining_outerwear and random.random() < 0.35:
                    outfit_garments.append(random.choice(remaining_outerwear))
            elif has_outerwear and random.random() < 0.3:
                outfit_garments.append(random.choice(by_type["outerwear"]))

            # Optionally add accessory
            if "accessory" in by_type and by_type["accessory"] and random.random() < 0.3:
                outfit_garments.append(random.choice(by_type["accessory"]))

            outfit = Outfit(
                name=f"{occasion.title()} Outfit", occasion=occasion, season=season, score=0.0
            )
            # Store garments as transient attribute for scoring/tips
            outfit._garments = outfit_garments
            outfits.append(outfit)

        return outfits

    # ========== PER-GARMENT SWAP (kiosk swipe gesture) ==========

    def swap_garment(self, request: GarmentSwapRequest) -> Outfit:
        """Swap one item of the current look for the next/previous eligible
        garment of the same type (stable id ordering, wraps around), then
        greedily re-picks the best-scoring companions for the other slots
        so the whole look keeps honoring the active style rules instead of
        just clashing with the newly swapped piece."""
        filters = {"season": request.season}
        all_garments = self.garment_repo.get_all(limit=1000, filters=filters)
        filtered = self._filter_by_occasion(all_garments, request.occasion, request.formality)

        by_type: dict[str, list[Garment]] = {}
        for g in filtered:
            by_type.setdefault(g.type, []).append(g)
        for garments_of_type in by_type.values():
            garments_of_type.sort(key=lambda g: g.id)

        current = [g for g in filtered if g.id in request.garment_ids]
        # Keep any current piece that fell outside the occasion/season filter
        # (e.g. borderline formality) instead of silently dropping it.
        missing_ids = set(request.garment_ids) - {g.id for g in current}
        if missing_ids:
            current += [g for g in self.garment_repo.get_all(limit=1000) if g.id in missing_ids]

        candidates = by_type.get(request.swap_type, [])
        if not candidates:
            raise ValueError(f"No hay más prendas disponibles de tipo '{request.swap_type}'")

        current_of_type = next((g for g in current if g.type == request.swap_type), None)
        candidate_ids = [c.id for c in candidates]
        idx = candidate_ids.index(current_of_type.id) if current_of_type and current_of_type.id in candidate_ids else -1

        step = 1 if request.direction == "next" else -1
        new_garment = candidates[(idx + step) % len(candidates)]

        outfit_garments = [g for g in current if g.type != request.swap_type] + [new_garment]

        active_rules = self.rule_repo.get_all(active_only=True)
        outfit_garments = self._rebalance(outfit_garments, by_type, active_rules, keep_type=request.swap_type)

        outfit = Outfit(
            name=f"{request.occasion.title()} Outfit", occasion=request.occasion, season=request.season, score=0.0
        )
        outfit._garments = outfit_garments
        outfit.score = self._calculate_score(outfit, active_rules)
        outfit.score_breakdown = self._get_score_breakdown(outfit, active_rules)
        outfit.ai_tips = self._generate_tips(outfit)

        return self._save_outfit(outfit)

    def _rebalance(
        self,
        garments: list[Garment],
        by_type: dict[str, list[Garment]],
        rules: list[StyleRule],
        keep_type: str,
        tries_per_slot: int = 4,
    ) -> list[Garment]:
        """Greedily try alternative candidates for every slot except
        keep_type, keeping whichever swap improves the outfit score - so the
        rest of the look adapts to the piece that was just swiped instead of
        clashing with it."""
        garments = list(garments)

        def score_of(gs: list[Garment]) -> float:
            tmp = Outfit(name="", occasion="", season="", score=0.0)
            tmp._garments = gs
            return self._calculate_score(tmp, rules)

        best_score = score_of(garments)

        for i, g in enumerate(garments):
            if g.type == keep_type:
                continue
            pool = by_type.get(g.type, [])
            if len(pool) < 2:
                continue
            for alt in random.sample(pool, min(tries_per_slot, len(pool))):
                if alt.id == g.id:
                    continue
                trial = list(garments)
                trial[i] = alt
                trial_score = score_of(trial)
                if trial_score > best_score:
                    garments = trial
                    best_score = trial_score

        return garments

    # ========== DAILY AUTO-GENERATION (anti-repeat rules) ==========

    def get_or_create_daily_outfit(
        self, occasion: str, season: str, formality: int | None = None
    ) -> Outfit:
        """Today's auto-generated look. Idempotent: returns the existing one
        if it was already generated (by the nightly scheduler or an earlier
        call today), otherwise generates and saves it now - so the kiosk
        always has a 'look of the day' even if the scheduler hasn't fired
        yet (e.g. right after a restart)."""
        today = date.today().isoformat()
        existing = self.outfit_repo.get_daily_by_date(today)
        if existing:
            existing.items = self.item_repo.get_by_outfit(existing.id)
            return existing
        return self._generate_daily_outfit(today, occasion, season, formality)

    def _generate_daily_outfit(
        self, today: str, occasion: str, season: str, formality: int | None
    ) -> Outfit:
        """Builds and saves the look for `today`, honoring:
        - no top repeated within the last 7 days
        - no bottom/outerwear repeated on 2 consecutive days
        Falls back to the unfiltered pool for a slot if the exclusion would
        leave it empty, so a small wardrobe never blocks generation."""
        garments = self.garment_repo.get_all(limit=1000, filters={"season": season})
        filtered = self._filter_by_occasion(garments, occasion, formality)
        if len(filtered) < 2:
            raise ValueError("No hay prendas suficientes para generar el look del día")

        week_ago = (date.today() - timedelta(days=7)).isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        recent_daily = self.outfit_repo.get_recent_daily(week_ago)

        recent_top_ids: set[int] = set()
        recent_bottom_ids: set[int] = set()
        for past_outfit in recent_daily:
            for item in self.item_repo.get_by_outfit(past_outfit.id):
                garment = self.garment_repo.get_by_id(item.garment_id)
                if not garment:
                    continue
                if garment.type == "top":
                    recent_top_ids.add(garment.id)
                elif garment.type in ("bottom", "outerwear") and past_outfit.for_date == yesterday:
                    recent_bottom_ids.add(garment.id)

        def without_excluded(pool: list[Garment], excluded: set[int]) -> list[Garment]:
            remaining = [g for g in pool if g.id not in excluded]
            return remaining if remaining else pool

        by_type: dict[str, list[Garment]] = {}
        for g in filtered:
            by_type.setdefault(g.type, []).append(g)

        if "top" in by_type:
            by_type["top"] = without_excluded(by_type["top"], recent_top_ids)
        for slot in ("bottom", "outerwear"):
            if slot in by_type:
                by_type[slot] = without_excluded(by_type[slot], recent_bottom_ids)

        eligible_pool = [g for garments_of_type in by_type.values() for g in garments_of_type]
        if len(eligible_pool) < 2:
            eligible_pool = filtered

        outfits = self._generate_combinations(eligible_pool, occasion, season, top_n=1)
        if not outfits:
            raise ValueError("No hay prendas suficientes para generar el look del día")

        active_rules = self.rule_repo.get_all(active_only=True)
        outfit = outfits[0]
        outfit.score = self._calculate_score(outfit, active_rules)
        outfit.score_breakdown = self._get_score_breakdown(outfit, active_rules)
        outfit.ai_tips = self._generate_tips(outfit)
        outfit.is_daily = True
        outfit.for_date = today
        outfit.name = f"Look del día · {today}"

        return self._save_outfit(outfit)

    def _calculate_score(self, outfit: Outfit, rules: list[StyleRule]) -> float:
        """Calculate outfit score based on style rules"""
        base_score = 50.0
        total_weight = 0.0
        weighted_score = 0.0

        for rule in rules:
            try:
                params = json.loads(rule.parameters)
                rule_score = self._apply_rule(outfit, rule.rule_type, params)
                weighted_score += rule_score * rule.weight
                total_weight += rule.weight
            except Exception:
                continue

        if total_weight > 0:
            base_score = (base_score + weighted_score / total_weight) / 2

        return max(0, min(100, base_score))

    def _apply_rule(self, outfit: Outfit, rule_type: str, params: dict) -> float:
        """Apply a single style rule via a Strategy registry: adding a new
        rule_type (color_harmony, occasion_match, ...) only means adding an
        entry to _RULE_SCORERS below, not editing this method."""
        garments = outfit._garments if hasattr(outfit, '_garments') else []
        if not garments:
            return 0

        scorer = self._RULE_SCORERS.get(rule_type)
        return scorer(self, garments, params) if scorer else 0

    def _color_harmony_score(self, garments: list[Garment], params: dict) -> float:
        """Score based on color harmony"""
        # Simplified: check if colors are in same family or complementary
        colors = [g.color_hex for g in garments]
        if len(colors) < 2:
            return 50

        # Simple heuristic: similar saturation = harmonious
        return 70.0

    def _occasion_match_score(self, garments: list[Garment], params: dict) -> float:
        """Score based on occasion appropriateness"""
        occasion = params.get("occasion", "casual")
        formality_map = {"casual": 1, "work": 2, "party": 3, "formal": 4, "wedding": 5}
        target = formality_map.get(occasion, 2)

        avg_formality = sum(g.formality for g in garments) / len(garments)
        diff = abs(avg_formality - target)
        return max(0, 100 - diff * 20)

    def _season_match_score(self, garments: list[Garment], params: dict) -> float:
        """Score based on season appropriateness"""
        season = params.get("season", "all_season")
        matches = sum(1 for g in garments if g.season == season or g.season == "all_season")
        return (matches / len(garments)) * 100

    def _formality_cap_score(self, garments: list[Garment], params: dict) -> float:
        """Score based on formality cap"""
        max_formality = params.get("max_formality", 5)
        violations = sum(1 for g in garments if g.formality > max_formality)
        return max(0, 100 - violations * 25)

    # Strategy registry for _apply_rule (OCP): a new StyleRule.rule_type only
    # needs a new entry here plus its scorer method - _apply_rule itself and
    # _calculate_score never need to change.
    _RULE_SCORERS = {
        "color_harmony": _color_harmony_score,
        "occasion_match": _occasion_match_score,
        "season_match": _season_match_score,
        "formality_cap": _formality_cap_score,
    }

    def _get_score_breakdown(self, outfit: Outfit, rules: list[StyleRule]) -> dict[str, float]:
        """Get detailed score breakdown"""
        return {
            "color_harmony": 75.0,
            "formality_match": 80.0,
            "pattern_balance": 70.0,
            "seasonal": 85.0,
        }

    def _generate_tips(self, outfit: Outfit) -> list[str]:
        """Generate AI style tips"""
        tips = []
        garments = outfit._garments if hasattr(outfit, '_garments') else []

        # Color tip
        colors = set(g.color_name for g in garments)
        if len(colors) <= 2:
            tips.append("Monochromatic look creates a sleek, elongated silhouette.")

        # Pattern tip
        patterns = [g.pattern for g in garments if g.pattern != "solid"]
        if len(patterns) > 1:
            tips.append("Mix patterns carefully - vary scale (large + small) for balance.")

        # Formality tip
        formalities = [g.formality for g in garments]
        if formalities and max(formalities) - min(formalities) > 2:
            tips.append("Balance formal and casual pieces - one statement piece is enough.")

        return tips if tips else ["Great combination! This outfit works well together."]

    def _save_outfit(self, outfit: Outfit) -> Outfit:
        """Save outfit with items"""
        saved_outfit = self.outfit_repo.create(outfit)

        # Create outfit items
        items = []
        outfit_id = saved_outfit.id or 0
        garments = outfit._garments if hasattr(outfit, '_garments') else []
        for i, garment in enumerate(garments):
            item = OutfitItem(outfit_id=outfit_id, garment_id=garment.id, position=i)
            items.append(item)

        self.item_repo.bulk_create(items)

        # Reload with items
        saved_outfit.items = self.item_repo.get_by_outfit(outfit_id)
        return saved_outfit

    # ========== PACKING PLAN ==========

    def create_packing_plan(self, request: PackingPlanRequest) -> dict[str, Any]:
        """Create a packing plan for a trip"""
        # Get all garments
        garments = self.garment_repo.get_all(limit=1000, filters={"season": request.season})

        if len(garments) < request.max_items:
            request.max_items = len(garments)

        # Score garments by versatility (how many outfits they can create)
        scored_garments = []
        for g in garments:
            versatility = self._calculate_versatility(g, garments)
            scored_garments.append((g, versatility))

        # Sort by versatility
        scored_garments.sort(key=lambda x: x[1], reverse=True)
        selected = [g for g, _ in scored_garments[: request.max_items]]

        # Generate outfits for each day
        outfits = []
        for day in range(request.days):
            # Create outfit from selected garments
            day_garments = random.sample(selected, min(len(selected), 4))
            outfit = Outfit(
                name=f"Day {day + 1}", occasion=request.occasion, season=request.season, score=0.0
            )
            outfit._garments = day_garments
            outfits.append(outfit)

        # Save outfits
        saved_outfits = [self._save_outfit(o) for o in outfits]

        # Check packing list has versatility scores
        packing_list = []
        for g, v in scored_garments[: request.max_items]:
            packing_list.append({
                "garment": g,
                "versatility_score": v,
                "days_covered": sum(1 for o in outfits if g in (o._garments if hasattr(o, '_garments') else [])),
            })

        return {
            "outfits": saved_outfits,
            "packing_list": packing_list,
            "total_items": len(selected),
            "days_covered": request.days,
            "mix_and_match_ratio": len(outfits) / max(1, len(selected)),
        }

    def _calculate_versatility(self, garment: Garment, all_garments: list[Garment]) -> float:
        """Calculate how versatile a garment is (how many outfits it can pair with)"""
        # Simple heuristic: more neutral colors + basic types = more versatile
        score = 0.5

        # Color versatility
        neutral_colors = {"black", "white", "gray", "grey", "navy", "beige", "khaki"}
        if garment.color_name.lower() in neutral_colors:
            score += 0.3

        # Type versatility
        versatile_types = {"top", "bottom", "outerwear"}
        if garment.type in versatile_types:
            score += 0.2

        return min(1.0, score)

    # ========== FEEDBACK ==========

    def rate_outfit(self, outfit_id: int, rating: int) -> bool:
        """Record user feedback on outfit. rating: -1 dislike, 1 like."""
        if not self.outfit_repo.get_by_id(outfit_id):
            return False
        self.feedback_repo.create(
            UserFeedbackCreate(outfit_id=outfit_id, rating=rating, feedback_type=_like_or_dislike(rating))
        )
        return True

    def rate_garment(self, garment_id: int, rating: int) -> bool:
        """Record user feedback on garment. rating: -1 dislike, 1 like."""
        if not self.garment_repo.get_by_id(garment_id):
            return False
        self.feedback_repo.create(
            UserFeedbackCreate(garment_id=garment_id, rating=rating, feedback_type=_like_or_dislike(rating))
        )
        return True
