from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from backend.ai_providers import AIProviderFactory
from backend.ai_providers.local import LocalRulesProvider
from backend.ai_providers.nim import NVIDIANIMProvider
from backend.models.schemas import (
    EnhanceRequest,
    GarmentRead,
    OutfitRead,
)


class TestAIProviderInterface:
    """Test AI Provider abstract interface and contract."""

    @pytest.fixture
    def mock_outfit(self):
        """Create a mock outfit for testing."""
        garments = [
            GarmentRead(
                id=1,
                name="Blue Shirt",
                type="top",
                color_name="blue",
                dominant_color_hex="#0000FF",
                pattern="solid",
                formality=2,
                season="all_season",
                is_favorite=False,
                wear_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            GarmentRead(
                id=2,
                name="Khaki Pants",
                type="bottom",
                color_name="beige",
                dominant_color_hex="#F5F5DC",
                pattern="solid",
                formality=2,
                season="all_season",
                is_favorite=False,
                wear_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        return OutfitRead(
            id=1,
            name="Work Outfit",
            occasion="work",
            season="all_season",
            formality=2,
            score=75.0,
            is_packing=False,
            notes=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            garments=garments,
        )

    @pytest.fixture
    def enhance_request(self, mock_outfit):
        """Create an enhance request."""
        return EnhanceRequest(
            outfit=mock_outfit,
            context="important meeting",
            user_preferences={"preferred_colors": ["blue", "navy"]},
        )


class TestLocalRulesProvider:
    """Test LocalRulesProvider implementation."""

    @pytest.fixture
    def provider(self):
        return LocalRulesProvider()

    @pytest.mark.asyncio
    async def test_health_check(self, provider):
        """Test health check returns True."""
        result = await provider.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_provider_name(self, provider):
        """Test provider name."""
        assert provider.get_provider_name() == "local"

    @pytest.mark.asyncio
    async def test_enhance_recommendation_basic(self, provider, enhance_request):
        """Test basic recommendation enhancement."""
        result = await provider.enhance_recommendation(
            outfit=enhance_request.outfit,
            context=enhance_request.context,
            user_preferences=enhance_request.user_preferences,
        )

        assert "enhanced_description" in result
        assert "style_tips" in result
        assert "confidence" in result
        assert isinstance(result["style_tips"], list)
        assert 0 <= result["confidence"] <= 1
        assert len(result["enhanced_description"]) > 0

    @pytest.mark.asyncio
    async def test_enhance_recommendation_with_garments(self, provider):
        """Test enhancement with multiple garment types."""
        garments = [
            GarmentRead(
                id=1,
                name="Red Dress",
                type="dress",
                color_name="red",
                dominant_color_hex="#FF0000",
                pattern="solid",
                formality=3,
                season="summer",
                is_favorite=False,
                wear_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            GarmentRead(
                id=2,
                name="White Sneakers",
                type="shoes",
                color_name="white",
                dominant_color_hex="#FFFFFF",
                pattern="solid",
                formality=1,
                season="all_season",
                is_favorite=False,
                wear_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        outfit = OutfitRead(
            id=1,
            name="Summer Look",
            occasion="party",
            season="summer",
            formality=2,
            score=80.0,
            is_packing=False,
            notes=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            garments=garments,
        )

        result = await provider.enhance_recommendation(outfit=outfit, context="summer party")

        assert (
            "summer" in result["enhanced_description"].lower()
            or "party" in result["enhanced_description"].lower()
        )
        assert len(result["style_tips"]) > 0

    @pytest.mark.asyncio
    async def test_generate_outfit_description(self, provider):
        """Test outfit description generation."""
        garments = [
            GarmentRead(
                id=1,
                name="Navy Blazer",
                type="outerwear",
                color_name="navy",
                dominant_color_hex="#000080",
                pattern="solid",
                formality=4,
                season="all_season",
                is_favorite=False,
                wear_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]

        desc = await provider.generate_outfit_description(garments=garments, occasion="wedding")

        assert "navy" in desc.lower() or "outerwear" in desc.lower()
        assert "wedding" in desc.lower()

    @pytest.mark.asyncio
    async def test_monochromatic_outfit_tips(self, provider):
        """Test style tips for monochromatic outfits."""
        garments = [
            GarmentRead(
                id=i,
                name=f"Black {t}",
                type=t,
                color_name="black",
                dominant_color_hex="#000000",
                pattern="solid",
                formality=2,
                season="all_season",
                is_favorite=False,
                wear_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            for i, t in enumerate(["top", "bottom", "shoes"], 1)
        ]

        outfit = OutfitRead(
            id=1,
            name="All Black",
            occasion="formal",
            season="all_season",
            formality=2,
            score=85.0,
            is_packing=False,
            notes=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            garments=garments,
        )

        result = await provider.enhance_recommendation(outfit=outfit)

        # Should mention monochromatic
        tips_text = " ".join(result["style_tips"]).lower()
        assert "monochrome" in tips_text or "black" in tips_text

    @pytest.mark.asyncio
    async def test_pattern_balance_tips(self, provider):
        """Test style tips for pattern balance."""
        garments = [
            GarmentRead(
                id=1,
                name="Striped Shirt",
                type="top",
                color_name="blue",
                dominant_color_hex="#0000FF",
                pattern="striped",
                formality=2,
                season="all_season",
                is_favorite=False,
                wear_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            GarmentRead(
                id=2,
                name="Checked Pants",
                type="bottom",
                color_name="gray",
                dominant_color_hex="#808080",
                pattern="checked",
                formality=2,
                season="all_season",
                is_favorite=False,
                wear_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        outfit = OutfitRead(
            id=1,
            name="Pattern Mix",
            occasion="casual",
            season="all_season",
            formality=2,
            score=65.0,
            is_packing=False,
            notes=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            garments=garments,
        )

        result = await provider.enhance_recommendation(outfit=outfit)

        tips_text = " ".join(result["style_tips"]).lower()
        assert "pattern" in tips_text or "scale" in tips_text

    @pytest.mark.asyncio
    async def test_formality_consistency_tips(self, provider):
        """Test style tips for formality consistency."""
        garments = [
            GarmentRead(
                id=1,
                name="T-shirt",
                type="top",
                color_name="white",
                dominant_color_hex="#FFFFFF",
                pattern="solid",
                formality=1,
                season="all_season",
                is_favorite=False,
                wear_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            GarmentRead(
                id=2,
                name="Tuxedo Pants",
                type="bottom",
                color_name="black",
                dominant_color_hex="#000000",
                pattern="solid",
                formality=5,
                season="all_season",
                is_favorite=False,
                wear_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        outfit = OutfitRead(
            id=1,
            name="Mixed Formality",
            occasion="date",
            season="all_season",
            formality=3,
            score=50.0,
            is_packing=False,
            notes=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            garments=garments,
        )

        result = await provider.enhance_recommendation(outfit=outfit)

        tips_text = " ".join(result["style_tips"]).lower()
        assert "formal" in tips_text or "casual" in tips_text


class TestNVIDIANIMProvider:
    """Test NVIDIA NIM Provider implementation."""

    @pytest.fixture
    def provider(self):
        with patch("backend.ai_providers.nim.get_settings") as mock_settings:
            mock_settings.return_value.nim_api_key = "test-key"
            mock_settings.return_value.nim_api_url = "https://test.api.nvidia.com/v1"
            mock_settings.return_value.nim_model = "test-model"
            return NVIDIANIMProvider()

    def test_provider_name(self, provider):
        assert provider.get_provider_name() == "nim"

    @pytest.mark.asyncio
    async def test_health_check_no_key(self):
        """Test health check without API key."""
        with patch("backend.ai_providers.nim.get_settings") as mock_settings:
            mock_settings.return_value.nim_api_key = ""
            provider = NVIDIANIMProvider()
            result = await provider.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_enhance_recommendation_fallback(self, provider, enhance_request):
        """Test fallback to local provider on error."""
        # Mock the client to raise an exception
        provider._client = AsyncMock()
        provider._client.post.side_effect = Exception("API Error")

        # Should fall back to local provider
        result = await provider.enhance_recommendation(
            outfit=enhance_request.outfit,
            context=enhance_request.context,
            user_preferences=enhance_request.user_preferences,
        )

        assert "enhanced_description" in result
        assert "style_tips" in result

    @pytest.mark.asyncio
    async def test_enhance_recommendation_success(self, provider, enhance_request):
        """Test successful NIM enhancement."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"description": "Elegant work outfit", "tips": ["Tip 1", "Tip 2"], "confidence": 0.9}'
                    }
                }
            ]
        }

        provider._client = AsyncMock()
        provider._client.post.return_value = mock_response

        result = await provider.enhance_recommendation(
            outfit=enhance_request.outfit, context=enhance_request.context
        )

        assert result["enhanced_description"] == "Elegant work outfit"
        assert result["style_tips"] == ["Tip 1", "Tip 2"]
        assert result["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_generate_outfit_description(self, provider):
        """Test outfit description generation."""
        provider._client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "A stylish navy and beige combination for work."}}]
        }
        provider._client.post.return_value = mock_response

        garments = [
            GarmentRead(
                id=1,
                name="Navy Blazer",
                type="outerwear",
                color_name="navy",
                dominant_color_hex="#000080",
                pattern="solid",
                formality=4,
                season="all_season",
                is_favorite=False,
                wear_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ]

        desc = await provider.generate_outfit_description(garments=garments, occasion="wedding")

        assert "navy" in desc.lower() or "beige" in desc.lower()


class TestAIProviderFactory:
    """Test AI Provider Factory."""

    def test_create_local_provider(self):
        """Test creating local provider."""
        with patch("backend.ai_providers.factory.get_settings") as mock_settings:
            mock_settings.return_value.ai_provider = "local"

            provider = AIProviderFactory.create("local")

            assert isinstance(provider, LocalRulesProvider)
            assert provider.get_provider_name() == "local"

    def test_create_nim_provider(self):
        """Test creating NIM provider."""
        with patch("backend.ai_providers.factory.get_settings") as mock_settings:
            mock_settings.return_value.ai_provider = "nim"
            mock_settings.return_value.nim_api_key = "test-key"

            provider = AIProviderFactory.create("nim")

            assert isinstance(provider, NVIDIANIMProvider)
            assert provider.get_provider_name() == "nim"

    def test_get_available_provider_prefers_nim(self):
        """Test that factory prefers NIM when available."""
        with patch("backend.ai_providers.factory.get_settings") as mock_settings:
            mock_settings.return_value.ai_provider = "nim"
            mock_settings.return_value.nim_api_key = "test-key"

            # Mock NIM health check to succeed
            with patch.object(NVIDIANIMProvider, "health_check", return_value=True):
                provider = AIProviderFactory.get_available_provider()
                assert isinstance(provider, NVIDIANIMProvider)

    def test_get_available_provider_falls_back_to_local(self):
        """Test fallback to local when NIM unavailable."""
        with patch("backend.ai_providers.factory.get_settings") as mock_settings:
            mock_settings.return_value.ai_provider = "nim"
            mock_settings.return_value.nim_api_key = "test-key"

            # Mock NIM health check to fail
            with patch.object(NVIDIANIMProvider, "health_check", return_value=False):
                provider = AIProviderFactory.get_available_provider()
                assert isinstance(provider, LocalRulesProvider)

    def test_caching(self):
        """Test provider instance caching."""
        with patch("backend.ai_providers.factory.get_settings") as mock_settings:
            mock_settings.return_value.ai_provider = "local"

            provider1 = AIProviderFactory.get_provider()
            provider2 = AIProviderFactory.get_provider()

            assert provider1 is provider2  # Same instance

    def test_cache_cleared_on_type_change(self):
        """Test cache cleared when provider type changes."""
        with patch("backend.ai_providers.factory.get_settings") as mock_settings:
            mock_settings.return_value.ai_provider = "local"
            provider1 = AIProviderFactory.get_provider()

            mock_settings.return_value.ai_provider = "nim"
            mock_settings.return_value.nim_api_key = "test-key"

            with patch.object(NVIDIANIMProvider, "health_check", return_value=True):
                provider2 = AIProviderFactory.get_provider()

            assert provider1 is not provider2
            assert isinstance(provider1, LocalRulesProvider)
            assert isinstance(provider2, NVIDIANIMProvider)


class TestAIProviderContract:
    """Contract tests ensuring all providers implement the interface."""

    @pytest.fixture(params=[LocalRulesProvider, NVIDIANIMProvider])
    def provider_class(self, request):
        return request.param

    @pytest.mark.asyncio
    async def test_all_providers_implement_interface(self, provider_class):
        """Test all providers implement required methods."""
        if provider_class == NVIDIANIMProvider:
            with patch("backend.ai_providers.nim.get_settings") as mock_settings:
                mock_settings.return_value.nim_api_key = "test-key"
                provider = provider_class()
        else:
            provider = provider_class()

        # Check required methods exist
        assert hasattr(provider, "get_provider_name")
        assert hasattr(provider, "health_check")
        assert hasattr(provider, "enhance_recommendation")
        assert hasattr(provider, "generate_outfit_description")

        # Check methods are callable
        assert callable(provider.get_provider_name)
        assert callable(provider.health_check)
        assert callable(provider.enhance_recommendation)
        assert callable(provider.generate_outfit_description)

        # Check return types
        name = provider.get_provider_name()
        assert isinstance(name, str)
        assert len(name) > 0


# Fixtures
@pytest.fixture
def enhance_request():
    """Create a sample enhance request."""
    garments = [
        GarmentRead(
            id=1,
            name="Blue Shirt",
            type="top",
            color_name="blue",
            dominant_color_hex="#0000FF",
            pattern="solid",
            formality=2,
            season="all_season",
            is_favorite=False,
            wear_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    ]

    outfit = OutfitRead(
        id=1,
        name="Test Outfit",
        occasion="casual",
        season="all_season",
        formality=2,
        score=70.0,
        is_packing=False,
        notes=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        garments=garments,
    )

    return EnhanceRequest(outfit=outfit, context="weekend brunch", user_preferences={})
