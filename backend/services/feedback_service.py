from datetime import datetime
from typing import Any

from sqlmodel import Session

from backend.models.garment import UserFeedback
from backend.models.schemas import UserFeedbackCreate
from backend.repositories import GarmentRepository, OutfitRepository, UserFeedbackRepository
from backend.services.style_engine import StyleEngine


class FeedbackService:
    """Service for handling user feedback and learning."""

    def __init__(self, session: Session):
        self.session = session
        self.garment_repo = GarmentRepository(session)
        self.outfit_repo = OutfitRepository(session)
        self.feedback_repo = UserFeedbackRepository(session)
        self.style_engine = StyleEngine(session)

    def rate_outfit(
        self,
        outfit_id: int,
        rating: int,
        comment: str | None = None,
        context: str | None = None,
    ) -> UserFeedback:
        """Record feedback for an outfit."""
        feedback = self.feedback_repo.create(
            UserFeedbackCreate(
                outfit_id=outfit_id, rating=rating, feedback_type="outfit", context=context
            )
        )

        # Update outfit score based on feedback
        self._update_outfit_score(outfit_id)

        # Update garment biases
        self._update_garment_biases_from_outfit(outfit_id, rating)

        return feedback

    def rate_garment(
        self,
        garment_id: int,
        rating: int,
        comment: str | None = None,
        context: str | None = None,
    ) -> UserFeedback:
        """Record feedback for a single garment."""
        feedback = self.feedback_repo.create(
            UserFeedbackCreate(
                garment_id=garment_id, rating=rating, feedback_type="garment", context=context
            )
        )

        # Update garment bias
        self._update_garment_bias(garment_id)

        return feedback

    def get_outfit_feedback(self, outfit_id: int) -> list[UserFeedback]:
        """Get all feedback for an outfit."""
        return self.feedback_repo.get_by_outfit(outfit_id)

    def get_garment_feedback(self, garment_id: int) -> list[UserFeedback]:
        """Get all feedback for a garment."""
        return self.feedback_repo.get_by_garment(garment_id)

    def get_outfit_rating_summary(self, outfit_id: int) -> dict[str, Any]:
        """Get rating summary for an outfit."""
        feedbacks = self.get_outfit_feedback(outfit_id)

        if not feedbacks:
            return {"average": 0, "count": 0, "likes": 0, "dislikes": 0, "neutral": 0}

        likes = sum(1 for f in feedbacks if f.rating > 0)
        dislikes = sum(1 for f in feedbacks if f.rating < 0)
        neutral = sum(1 for f in feedbacks if f.rating == 0)

        return {
            "average": sum(f.rating for f in feedbacks) / len(feedbacks),
            "count": len(feedbacks),
            "likes": likes,
            "dislikes": dislikes,
            "neutral": neutral,
        }

    def get_garment_bias(self, garment_id: int) -> float:
        """Get learned bias for a garment (-1 to 1)."""
        return self.feedback_repo.get_garment_bias(garment_id)

    def _update_outfit_score(self, outfit_id: int):
        """Update outfit score based on feedback."""
        summary = self.get_outfit_rating_summary(outfit_id)
        outfit = self.outfit_repo.get_by_id(outfit_id)

        if outfit and summary["count"] > 0:
            # Blend original score with feedback (70% original, 30% feedback)
            feedback_score = (summary["average"] + 1) / 2 * 100  # Convert -1..1 to 0..100
            outfit.score = outfit.score * 0.7 + feedback_score * 0.3
            outfit.updated_at = datetime.utcnow()
            self.session.add(outfit)
            self.session.commit()

    def _update_garment_bias(self, garment_id: int):
        """Update garment style bias from feedback."""
        bias = self.get_garment_bias(garment_id)
        garment = self.garment_repo.get_by_id(garment_id)

        if garment:
            garment.style_bias = max(-1.0, min(1.0, bias))
            garment.updated_at = datetime.utcnow()
            self.session.add(garment)
            self.session.commit()

    def _update_garment_biases_from_outfit(self, outfit_id: int, rating: int):
        """Update biases for all garments in an outfit."""
        outfit = self.outfit_repo.get_with_garments(outfit_id)
        if outfit and outfit.garment_links:
            for link in outfit.garment_links:
                self._update_garment_bias(link.garment_id)

    def get_personalized_recommendations(
        self, occasion: str, season: str = "all_season", top_n: int = 5
    ) -> list[dict[str, Any]]:
        """Get recommendations biased by user feedback."""
        # This would integrate with OutfitComposer but bias the scoring
        # based on learned preferences
        pass
