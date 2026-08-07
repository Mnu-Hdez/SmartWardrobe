"""Regression test: /feedback endpoints must actually persist a row.

Previously OutfitService.rate_outfit/rate_garment were stubs that returned
True without writing to the database.
"""

from sqlmodel import Session, SQLModel, create_engine, select

from backend.models.garment import Garment, UserFeedback
from backend.services.outfit_service import OutfitService


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_rate_garment_persists_feedback():
    session = _session()
    garment = Garment(
        name="Test Shirt",
        type="top",
        color_name="blue",
        color_hex="#0000FF",
        pattern="solid",
        formality=1,
        raw_image_path="a.jpg",
        processed_image_path="a.png",
    )
    session.add(garment)
    session.commit()
    session.refresh(garment)

    ok = OutfitService(session).rate_garment(garment.id, rating=1)

    assert ok is True
    saved = list(session.exec(select(UserFeedback)))
    assert len(saved) == 1
    assert saved[0].garment_id == garment.id
    assert saved[0].rating == 1
    assert saved[0].feedback_type == "like"


def test_rate_outfit_unknown_id_returns_false():
    session = _session()
    assert OutfitService(session).rate_outfit(outfit_id=999, rating=-1) is False


if __name__ == "__main__":
    test_rate_garment_persists_feedback()
    test_rate_outfit_unknown_id_returns_false()
    print("OK")
