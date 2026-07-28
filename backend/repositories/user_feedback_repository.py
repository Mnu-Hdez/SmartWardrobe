from datetime import datetime

from sqlmodel import Session, select

from backend.models.garment import UserFeedback
from backend.models.schemas import UserFeedbackCreate


class UserFeedbackRepository:
    """Repository for UserFeedback operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, feedback: UserFeedbackCreate) -> UserFeedback:
        db_feedback = UserFeedback(
            garment_id=feedback.garment_id,
            outfit_id=feedback.outfit_id,
            rating=feedback.rating,
            feedback_type=feedback.feedback_type,
            context=feedback.context,
        )
        self.session.add(db_feedback)
        self.session.commit()
        self.session.refresh(db_feedback)
        return db_feedback

    def get_by_id(self, feedback_id: int) -> UserFeedback | None:
        return self.session.get(UserFeedback, feedback_id)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[UserFeedback]:
        statement = (
            select(UserFeedback).offset(skip).limit(limit).order_by(UserFeedback.created_at.desc())
        )
        return list(self.session.exec(statement).all())

    def get_by_garment(self, garment_id: int) -> list[UserFeedback]:
        statement = select(UserFeedback).where(UserFeedback.garment_id == garment_id)
        return list(self.session.exec(statement).all())

    def get_by_outfit(self, outfit_id: int) -> list[UserFeedback]:
        statement = select(UserFeedback).where(UserFeedback.outfit_id == outfit_id)
        return list(self.session.exec(statement).all())

    def get_recent(self, days: int = 30, limit: int = 100) -> list[UserFeedback]:
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        statement = (
            select(UserFeedback)
            .where(UserFeedback.created_at >= cutoff)
            .order_by(UserFeedback.created_at.desc())
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    def get_garment_bias(self, garment_id: int) -> float:
        """Calculate average bias for a garment from feedback."""
        feedbacks = self.get_by_garment(garment_id)
        if not feedbacks:
            return 0.0
        return sum(f.rating for f in feedbacks) / len(feedbacks)

    def get_outfit_rating(self, outfit_id: int) -> float:
        """Calculate average rating for an outfit."""
        feedbacks = self.get_by_outfit(outfit_id)
        if not feedbacks:
            return 0.0
        return sum(f.rating for f in feedbacks) / len(feedbacks)

    def delete(self, feedback_id: int) -> bool:
        db_feedback = self.get_by_id(feedback_id)
        if not db_feedback:
            return False
        self.session.delete(db_feedback)
        self.session.commit()
        return True
