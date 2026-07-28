import pytest
from backend.models.schemas import (
    GarmentCreate, GarmentRead, GarmentUpdate,
    OutfitCreate, OutfitRead,
    StyleRuleCreate, StyleRuleRead,
    UserFeedbackCreate,
    OutfitRecommendationRequest,
    PackingRequest,
    EnhanceRequest, EnhanceResponse,
    HealthResponse,
    GarmentType, Season, FormalityLevel, PatternType,
    FeedbackType, AIProviderType
)
from pydantic import ValidationError
from datetime import datetime


class TestGarmentSchemas:
    """Test garment-related Pydantic schemas."""
    
    def test_garment_create_valid(self):
        """Test valid garment creation."""
        garment = GarmentCreate(
            name="Test Shirt",
            type="top",
            color_name="blue",
            dominant_color_hex="#0000FF",
            pattern="solid",
            formality=2,
            season="all_season"
        )
        assert garment.name == "Test Shirt"
        assert garment.type == "top"
        assert garment.dominant_color_hex == "#0000FF"
    
    def test_garment_create_invalid_color_hex(self):
        """Test invalid hex color validation."""
        with pytest.raises(ValidationError) as exc_info:
            GarmentCreate(
                name="Test",
                type="top",
                color_name="red",
                dominant_color_hex="not-a-hex"
            )
        assert "dominant_color_hex" in str(exc_info.value)
    
    def test_garment_create_invalid_formality(self):
        """Test formality level validation."""
        with pytest.raises(ValidationError):
            GarmentCreate(
                name="Test",
                type="top",
                color_name="red",
                dominant_color_hex="#FF0000",
                formality=6  # Max is 5
            )
    
    def test_garment_update_partial(self):
        """Test partial garment update."""
        update = GarmentUpdate(name="New Name", brand="New Brand")
        assert update.name == "New Name"
        assert update.brand == "New Brand"
        assert update.type is None
    
    def test_garment_read_from_attributes(self):
        """Test GarmentRead model with from_attributes."""
        # This would work with actual ORM objects
        pass


class TestOutfitSchemas:
    """Test outfit-related schemas."""
    
    def test_outfit_create_valid(self):
        """Test valid outfit creation."""
        outfit = OutfitCreate(
            name="Work Outfit",
            occasion="work",
            season="all_season",
            garment_ids=[1, 2, 3]
        )
        assert outfit.name == "Work Outfit"
        assert outfit.occasion == "work"
        assert len(outfit.garment_ids) == 3
    
    def test_outfit_create_min_garments(self):
        """Test minimum garment requirement."""
        with pytest.raises(ValidationError):
            OutfitCreate(
                name="Test",
                occasion="casual",
                garment_ids=[1]  # Min 1, but should probably be more
            )
    
    def test_outfit_update(self):
        """Test outfit update."""
        update = OutfitUpdate(score=85.5, name="Updated Name")
        assert update.score == 85.5
        assert update.name == "Updated Name"


class TestStyleRuleSchemas:
    """Test style rule schemas."""
    
    def test_style_rule_create(self):
        """Test style rule creation."""
        rule = StyleRuleCreate(
            name="color_harmony_test",
            description="Test rule",
            rule_type="color_harmony",
            weight=1.5,
            parameters='{"method": "complementary"}'
        )
        assert rule.name == "color_harmony_test"
        assert rule.weight == 1.5
    
    def test_style_rule_update(self):
        """Test style rule update."""
        update = StyleRuleUpdate(weight=2.0, is_active=False)
        assert update.weight == 2.0
        assert update.is_active is False


class TestFeedbackSchemas:
    """Test feedback schemas."""
    
    def test_user_feedback_create_outfit(self):
        """Test outfit feedback creation."""
        feedback = UserFeedbackCreate(
            outfit_id=1,
            rating=1,
            feedback_type="like",
            context="work meeting"
        )
        assert feedback.outfit_id == 1
        assert feedback.rating == 1
        assert feedback.feedback_type == "like"
    
    def test_user_feedback_create_garment(self):
        """Test garment feedback creation."""
        feedback = UserFeedbackCreate(
            garment_id=5,
            rating=-1,
            feedback_type="dislike"
        )
        assert feedback.garment_id == 5
        assert feedback.rating == -1
    
    def test_feedback_rating_validation(self):
        """Test rating must be -1, 0, or 1."""
        with pytest.raises(ValidationError):
            UserFeedbackCreate(
                outfit_id=1,
                rating=2,  # Invalid
                feedback_type="like"
            )


class TestRecommendationSchemas:
    """Test recommendation request/response schemas."""
    
    def test_recommendation_request_valid(self):
        """Test valid recommendation request."""
        req = OutfitRecommendationRequest(
            occasion="party",
            season="summer",
            formality=3,
            top_n=5,
            exclude_garment_ids=[1, 2]
        )
        assert req.occasion == "party"
        assert req.top_n == 5
        assert req.exclude_garment_ids == [1, 2]
    
    def test_recommendation_request_defaults(self):
        """Test default values."""
        req = OutfitRecommendationRequest(occasion="casual")
        assert req.season == "all_season"
        assert req.top_n == 5
        assert req.exclude_garment_ids == []


class TestPackingSchemas:
    """Test packing request/response schemas."""
    
    def test_packing_request_valid(self):
        """Test valid packing request."""
        req = PackingRequest(
            days=5,
            occasion="travel",
            season="summer",
            max_items=15
        )
        assert req.days == 5
        assert req.max_items == 15
    
    def test_packing_request_validation(self):
        """Test packing request validation."""
        with pytest.raises(ValidationError):
            PackingRequest(days=0)  # Must be >= 1
        
        with pytest.raises(ValidationError):
            PackingRequest(days=31)  # Must be <= 30
        
        with pytest.raises(ValidationError):
            PackingRequest(max_items=3)  # Must be >= 5


class TestAIProviderSchemas:
    """Test AI provider schemas."""
    
    def test_enhance_request(self):
        """Test enhance request."""
        req = EnhanceRequest(
            outfit=OutfitRead(
                id=1,
                name="Test Outfit",
                occasion="casual",
                season="all_season",
                formality=2,
                score=80.0,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            context="Friday night out",
            user_preferences={"preferred_colors": ["blue", "black"]}
        )
        assert req.context == "Friday night out"
        assert req.user_preferences["preferred_colors"] == ["blue", "black"]
    
    def test_enhance_response(self):
        """Test enhance response."""
        resp = EnhanceResponse(
            enhanced_description="A stylish blue outfit for Friday night",
            style_tips=["Add a watch", "Roll sleeves"],
            confidence=0.9
        )
        assert resp.confidence == 0.9
        assert len(resp.style_tips) == 2


class TestHealthResponse:
    """Test health check response."""
    
    def test_health_response(self):
        """Test health response."""
        resp = HealthResponse(
            status="healthy",
            version="0.1.0",
            timestamp=datetime.now(),
            database="connected",
            ai_provider="local"
        )
        assert resp.status == "healthy"
        assert resp.ai_provider == "local"


class TestEnums:
    """Test enum values."""
    
    def test_garment_type_enum(self):
        """Test garment type enum."""
        assert GarmentType.TOP == "top"
        assert GarmentType.BOTTOM == "bottom"
        assert GarmentType.DRESS == "dress"
    
    def test_season_enum(self):
        """Test season enum."""
        assert Season.SPRING == "spring"
        assert Season.ALL_SEASON == "all_season"
    
    def test_formality_enum(self):
        """Test formality enum."""
        assert FormalityLevel.CASUAL == 1
        assert FormalityLevel.FORMAL == 4
        assert FormalityLevel.BLACK_TIE == 5
    
    def test_pattern_enum(self):
        """Test pattern enum."""
        assert PatternType.SOLID == "solid"
        assert PatternType.STRIPED == "striped"
        assert PatternType.FLORAL == "floral"
    
    def test_feedback_type_enum(self):
        """Test feedback type enum."""
        assert FeedbackType.LIKE == "like"
        assert FeedbackType.DISLIKE == "dislike"
    
    def test_ai_provider_enum(self):
        """Test AI provider enum."""
        assert AIProviderType.LOCAL == "local"
        assert AIProviderType.NIM == "nim"