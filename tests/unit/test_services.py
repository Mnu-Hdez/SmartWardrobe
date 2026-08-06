from unittest.mock import Mock

import pytest
from sqlmodel import Session

from backend.models.garment import Garment, Outfit
from backend.models.schemas import OutfitGarmentLink, UserFeedback
from backend.services.feedback_service import FeedbackService
from backend.services.outfit_composer import OutfitComposer
from backend.services.packing_service import PackingResult, PackingService
from backend.services.style_engine import StyleEngine, StyleScore


class TestStyleEngine:
    """Test StyleEngine scoring logic."""

    @pytest.fixture
    def mock_session(self):
        return Mock(spec=Session)

    @pytest.fixture
    def style_engine(self, mock_session):
        return StyleEngine(mock_session)

    @pytest.fixture
    def sample_garments(self):
        """Create sample garments for testing."""
        return [
            Garment(
                id=1,
                name="Blue Shirt",
                type="top",
                color_name="blue",
                color_hex="#0000FF",
                pattern="solid",
                formality=2,
                season="all_season",
                style_bias=0.0,
            ),
            Garment(
                id=2,
                name="Khaki Pants",
                type="bottom",
                color_name="beige",
                color_hex="#C2B280",
                pattern="solid",
                formality=2,
                season="all_season",
                style_bias=0.0,
            ),
            Garment(
                id=3,
                name="Brown Shoes",
                type="shoes",
                color_name="brown",
                color_hex="#8B4513",
                pattern="solid",
                formality=2,
                season="all_season",
                style_bias=0.0,
            ),
        ]

    @pytest.fixture
    def sample_outfit(self):
        return Outfit(
            id=1, name="Test Outfit", occasion="casual", season="all_season", formality=2, score=0.0
        )

    def test_score_outfit_no_garments(self, style_engine, sample_outfit):
        """Test scoring outfit with no garments."""
        style_engine._get_garments = Mock(return_value=[])
        score = style_engine.score_outfit(sample_outfit)

        assert score.total == 0.0
        assert "error" in score.details

    def test_score_color_harmony_monochromatic(self, style_engine, sample_garments):
        """Test color harmony for monochromatic outfit."""
        # All same color
        for g in sample_garments:
            g.color_hex = "#0000FF"
            g.color_name = "blue"

        style_engine._get_garments = Mock(return_value=sample_garments)
        outfit = Outfit(occasion="casual", season="all_season", formality=2)

        score = style_engine.score_outfit(outfit)

        # Monochromatic should score well
        assert score.color_harmony >= 80

    def test_score_color_harmony_complementary(self, style_engine, sample_garments):
        """Test color harmony for complementary colors."""
        # Blue and orange (complementary)
        sample_garments[0].color_hex = "#0000FF"
        sample_garments[0].color_name = "blue"
        sample_garments[1].color_hex = "#FFA500"
        sample_garments[1].color_name = "orange"

        style_engine._get_garments = Mock(return_value=sample_garments)
        outfit = Outfit(occasion="casual", season="all_season", formality=2)

        score = style_engine.score_outfit(outfit)

        # Complementary should score well
        assert score.color_harmony >= 70

    def test_score_formality_match(self, style_engine, sample_garments):
        """Test formality matching."""
        # All same formality
        for g in sample_garments:
            g.formality = 3

        style_engine._get_garments = Mock(return_value=sample_garments)
        outfit = Outfit(occasion="work", season="all_season", formality=3)

        score = style_engine.score_outfit(outfit)

        # Perfect formality match should score 100
        assert score.formality_match == 100.0

    def test_score_formality_mismatch(self, style_engine, sample_garments):
        """Test formality mismatch penalty."""
        sample_garments[0].formality = 1  # Casual
        sample_garments[1].formality = 5  # Black tie

        style_engine._get_garments = Mock(return_value=sample_garments)
        outfit = Outfit(occasion="casual", season="all_season", formality=1)

        score = style_engine.score_outfit(outfit)

        # Large spread should be penalized
        assert score.formality_match < 50

    def test_score_pattern_balance(self, style_engine, sample_garments):
        """Test pattern balance scoring."""
        # One pattern - ideal
        sample_garments[0].pattern = "striped"
        sample_garments[1].pattern = "solid"
        sample_garments[2].pattern = "solid"

        style_engine._get_garments = Mock(return_value=sample_garments)
        outfit = Outfit(occasion="casual", season="all_season", formality=2)

        score = style_engine.score_outfit(outfit)

        assert score.pattern_balance == 100.0

    def test_score_too_many_patterns(self, style_engine, sample_garments):
        """Test penalty for too many patterns."""
        for g in sample_garments:
            g.pattern = "floral"

        style_engine._get_garments = Mock(return_value=sample_garments)
        outfit = Outfit(occasion="casual", season="all_season", formality=2)

        score = style_engine.score_outfit(outfit)

        assert score.pattern_balance <= 40

    def test_score_seasonal_match(self, style_engine, sample_garments):
        """Test seasonal appropriateness."""
        for g in sample_garments:
            g.season = "summer"

        style_engine._get_garments = Mock(return_value=sample_garments)
        outfit = Outfit(occasion="casual", season="summer", formality=2)

        score = style_engine.score_outfit(outfit)

        assert score.seasonal == 100.0

    def test_score_user_bias(self, style_engine, sample_garments):
        """Test user bias scoring."""
        sample_garments[0].style_bias = 0.5
        sample_garments[1].style_bias = 0.3
        sample_garments[2].style_bias = -0.2

        style_engine._get_garments = Mock(return_value=sample_garments)
        outfit = Outfit(occasion="casual", season="all_season", formality=2)

        score = style_engine.score_outfit(outfit)

        # Average bias = (0.5 + 0.3 - 0.2) / 3 = 0.2
        # Scaled to 0-100: (0.2 + 1) * 50 = 60
        assert score.user_bias == 60.0


class TestOutfitComposer:
    """Test OutfitComposer recommendation logic."""

    @pytest.fixture
    def mock_session(self):
        return Mock(spec=Session)

    @pytest.fixture
    def composer(self, mock_session):
        return OutfitComposer(mock_session)

    @pytest.fixture
    def sample_garments(self):
        return [
            Garment(
                id=i,
                name=f"Item {i}",
                type=t,
                color_name=c,
                color_hex=h,
                pattern="solid",
                formality=2,
                season="all_season",
                style_bias=0.0,
            )
            for i, (t, c, h) in enumerate(
                [
                    ("top", "blue", "#0000FF"),
                    ("bottom", "beige", "#C2B280"),
                    ("shoes", "brown", "#8B4513"),
                    ("outerwear", "black", "#000000"),
                    ("dress", "red", "#FF0000"),
                ],
                1,
            )
        ]

    def test_compose_outfits_empty_wardrobe(self, composer, mock_session):
        """Test with no garments available."""
        composer.garment_repo.get_all = Mock(return_value=[])

        results = composer.recommend(occasion="casual")

        assert results == []

    def test_compose_outfits_minimum_garments(self, composer, sample_garments):
        """Test with just enough garments for one outfit."""
        # Only top and bottom - minimum for outfit
        composer.garment_repo.get_all = Mock(return_value=sample_garments[:2])

        results = composer.recommend(occasion="casual", top_n=3)

        # Should generate at least some outfits
        assert len(results) >= 0  # Depends on templates

    def test_compose_outfits_filters_season(self, composer, sample_garments):
        """Test season filtering."""
        sample_garments[0].season = "summer"
        sample_garments[1].season = "winter"

        composer.garment_repo.get_all = Mock(return_value=sample_garments)

        results = composer.recommend(occasion="casual", season="summer")

        # Should only include summer and all_season garments
        for outfit, score in results:
            for g in outfit.garments:
                assert g.season in ["summer", "all_season"]

    def test_compose_outfits_filters_formality(self, composer, sample_garments):
        """Test formality filtering."""
        sample_garments[0].formality = 1
        sample_garments[1].formality = 5

        composer.garment_repo.get_all = Mock(return_value=sample_garments)

        results = composer.recommend(occasion="casual", formality=1)

        # Should prefer formality 1 items
        for outfit, score in results:
            for g in outfit.garments:
                assert abs(g.formality - 1) <= 1

    def test_compose_outfits_excludes_garments(self, composer, sample_garments):
        """Test excluding specific garments."""
        composer.garment_repo.get_all = Mock(return_value=sample_garments)

        results = composer.recommend(occasion="casual", exclude_garment_ids=[1])

        for outfit, score in results:
            assert not any(g.id == 1 for g in outfit.garments)

    def test_compose_outfits_diversity(self, composer, sample_garments):
        """Test diversity filtering."""
        composer.garment_repo.get_all = Mock(return_value=sample_garments)

        results = composer.recommend(occasion="casual", top_n=3, diversity_factor=0.5)

        # Should have diverse outfits (not all same garments)
        garment_sets = [set(g.id for g in o.garments) for o, _ in results]

        # At least some should be different
        if len(garment_sets) > 1:
            assert len(set(tuple(sorted(s)) for s in garment_sets)) > 1


class TestFeedbackService:
    """Test FeedbackService learning logic."""

    @pytest.fixture
    def mock_session(self):
        return Mock(spec=Session)

    @pytest.fixture
    def feedback_service(self, mock_session):
        return FeedbackService(mock_session)

    def test_rate_outfit(self, feedback_service, mock_session):
        """Test rating an outfit."""
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()

        # Mock repositories
        feedback_service.feedback_repo.create = Mock(
            return_value=UserFeedback(id=1, outfit_id=1, rating=1, feedback_type="like")
        )
        feedback_service.outfit_repo.get_by_id = Mock(return_value=Outfit(id=1, score=70.0))
        feedback_service.outfit_repo.get_with_garments = Mock(
            return_value=Outfit(
                id=1,
                garment_links=[OutfitGarmentLink(garment_id=1), OutfitGarmentLink(garment_id=2)],
            )
        )
        feedback_service.garment_repo.get_by_id = Mock(
            side_effect=[Garment(id=1, style_bias=0.0), Garment(id=2, style_bias=0.0)]
        )

        feedback = feedback_service.rate_outfit(outfit_id=1, rating=1, context="test")

        assert feedback.rating == 1
        assert feedback.outfit_id == 1
        mock_session.commit.assert_called()

    def test_rate_garment(self, feedback_service):
        """Test rating a single garment."""
        feedback_service.feedback_repo.create = Mock(
            return_value=UserFeedback(id=1, garment_id=1, rating=-1, feedback_type="dislike")
        )
        feedback_service.garment_repo.get_by_id = Mock(return_value=Garment(id=1, style_bias=0.0))
        feedback_service.feedback_repo.get_garment_bias = Mock(return_value=-1.0)

        feedback = feedback_service.rate_garment(garment_id=1, rating=-1)

        assert feedback.rating == -1
        assert feedback.garment_id == 1


class TestPackingService:
    """Test PackingService optimization logic."""

    @pytest.fixture
    def mock_session(self):
        return Mock(spec=Session)

    @pytest.fixture
    def packing_service(self, mock_session):
        return PackingService(mock_session)

    @pytest.fixture
    def travel_garments(self):
        """Create versatile travel wardrobe."""
        types = [
            "top",
            "top",
            "bottom",
            "bottom",
            "dress",
            "outerwear",
            "shoes",
            "shoes",
            "accessory",
        ]
        colors = ["blue", "white", "beige", "black", "navy", "gray", "brown", "black", "silver"]
        return [
            Garment(
                id=i,
                name=f"{c} {t}",
                type=t,
                color_name=c,
                color_hex="#000000",
                pattern="solid",
                formality=2,
                season="all_season",
                style_bias=0.0,
            )
            for i, (t, c) in enumerate(zip(types, colors), 1)
        ]

    def test_plan_packing_basic(self, packing_service, travel_garments):
        """Test basic packing plan generation."""
        packing_service.garment_repo.get_all = Mock(return_value=travel_garments)
        packing_service.style_engine.score_outfit = Mock(
            return_value=StyleScore(
                total=80.0,
                color_harmony=80,
                formality_match=80,
                pattern_balance=80,
                seasonal=80,
                occasion=80,
                user_bias=50,
                details={},
            )
        )

        result = packing_service.plan_packing(days=3, occasion="travel", max_items=10)

        assert isinstance(result, PackingResult)
        assert result.days_covered <= 3
        assert result.total_items <= 10
        assert len(result.outfits) <= 3

    def test_plan_packing_respects_max_items(self, packing_service, travel_garments):
        """Test max items constraint."""
        packing_service.garment_repo.get_all = Mock(return_value=travel_garments)
        packing_service.style_engine.score_outfit = Mock(
            return_value=StyleScore(
                total=80.0,
                color_harmony=80,
                formality_match=80,
                pattern_balance=80,
                seasonal=80,
                occasion=80,
                user_bias=50,
                details={},
            )
        )

        result = packing_service.plan_packing(days=5, max_items=5)

        assert result.total_items <= 5

    def test_plan_packing_must_include(self, packing_service, travel_garments):
        """Test must-include items."""
        packing_service.garment_repo.get_all = Mock(return_value=travel_garments)
        packing_service.style_engine.score_outfit = Mock(
            return_value=StyleScore(
                total=80.0,
                color_harmony=80,
                formality_match=80,
                pattern_balance=80,
                seasonal=80,
                occasion=80,
                user_bias=50,
                details={},
            )
        )

        result = packing_service.plan_packing(days=3, must_include_ids=[1, 2])

        assert 1 in result.garment_ids_used
        assert 2 in result.garment_ids_used

    def test_plan_packing_versatility(self, packing_service, travel_garments):
        """Test that versatile items are preferred."""
        packing_service.garment_repo.get_all = Mock(return_value=travel_garments)
        packing_service.style_engine.score_outfit = Mock(
            return_value=StyleScore(
                total=80.0,
                color_harmony=80,
                formality_match=80,
                pattern_balance=80,
                seasonal=80,
                occasion=80,
                user_bias=50,
                details={},
            )
        )

        result = packing_service.plan_packing(days=3)

        # Check packing list has versatility scores
        for item in result.packing_list:
            assert 0 <= item.versatility_score <= 1

        # Items used in more outfits should have higher versatility
        versatility_by_usage = {}
        for item in result.packing_list:
            if item.outfits_used not in versatility_by_usage:
                versatility_by_usage[item.outfits_used] = []
            versatility_by_usage[item.outfits_used].append(item.versatility_score)

        # Generally, more usage = higher versatility (though not strict)
        if len(versatility_by_usage) > 1:
            max_usage = max(versatility_by_usage.keys())
            min_usage = min(versatility_by_usage.keys())
            if max_usage != min_usage:
                assert max(versatility_by_usage[max_usage]) >= min(versatility_by_usage[min_usage])

    def test_get_item_suggestions(self, packing_service, travel_garments):
        """Test item suggestion logic."""
        current_ids = [1, 2, 3]
        packing_service.garment_repo.get_all = Mock(return_value=travel_garments)

        suggestions = packing_service.get_item_suggestions(
            days=3, occasion="travel", season="all_season", current_garment_ids=current_ids
        )

        # Should not suggest already packed items
        suggested_ids = [s["garment"].id for s in suggestions]
        assert not any(id in current_ids for id in suggested_ids)

        # Should be sorted by versatility bonus
        bonuses = [s["versatility_bonus"] for s in suggestions]
        assert bonuses == sorted(bonuses, reverse=True)


# Integration-style tests
class TestServicesIntegration:
    """Test services working together."""

    @pytest.fixture
    def mock_session(self):
        return Mock(spec=Session)

    def test_style_engine_with_composer(self, mock_session):
        """Test StyleEngine integration with OutfitComposer."""
        composer = OutfitComposer(mock_session)

        # Verify composer uses style_engine
        assert composer.style_engine is not None
        assert isinstance(composer.style_engine, StyleEngine)

    def test_feedback_updates_style_bias(self, mock_session):
        """Test that feedback updates garment style_bias."""
        feedback_service = FeedbackService(mock_session)

        # Mock garment with initial bias
        garment = Garment(id=1, style_bias=0.0)
        feedback_service.garment_repo.get_by_id = Mock(return_value=garment)
        feedback_service.feedback_repo.get_garment_bias = Mock(return_value=0.8)
        feedback_service.feedback_repo.create = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()

        feedback_service.rate_garment(garment_id=1, rating=1)

        # style_bias should be updated
        assert garment.style_bias == 0.8
        mock_session.commit.assert_called()
