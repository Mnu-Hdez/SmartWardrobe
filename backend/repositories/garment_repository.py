
from sqlmodel import Session, select

from backend.models.garment import Garment, GarmentCreate, GarmentUpdate


class GarmentRepository:
    """Repository for Garment operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, garment: GarmentCreate) -> Garment:
        db_garment = Garment.model_validate(garment)
        self.session.add(db_garment)
        self.session.commit()
        self.session.refresh(db_garment)
        return db_garment

    def get_by_id(self, garment_id: int) -> Garment | None:
        return self.session.get(Garment, garment_id)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Garment]:
        statement = select(Garment).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def get_by_type(self, garment_type: str, skip: int = 0, limit: int = 100) -> list[Garment]:
        statement = select(Garment).where(Garment.type == garment_type).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def get_by_season(self, season: str, skip: int = 0, limit: int = 100) -> list[Garment]:
        statement = select(Garment).where(Garment.season == season).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def search(self, query: str, skip: int = 0, limit: int = 100) -> list[Garment]:
        statement = (
            select(Garment)
            .where(
                Garment.name.contains(query)
                | Garment.brand.contains(query)
                | Garment.color_name.contains(query)
            )
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.exec(statement).all())

    def update(self, garment_id: int, garment: GarmentUpdate) -> Garment | None:
        db_garment = self.get_by_id(garment_id)
        if not db_garment:
            return None

        update_data = garment.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_garment, field, value)

        self.session.add(db_garment)
        self.session.commit()
        self.session.refresh(db_garment)
        return db_garment

    def delete(self, garment_id: int) -> bool:
        db_garment = self.get_by_id(garment_id)
        if not db_garment:
            return False
        self.session.delete(db_garment)
        self.session.commit()
        return True

    def count(self) -> int:
        statement = select(Garment)
        return len(list(self.session.exec(statement).all()))

    def get_with_bias(self, min_bias: float = -1.0, max_bias: float = 1.0) -> list[Garment]:
        statement = select(Garment).where(
            Garment.style_bias >= min_bias, Garment.style_bias <= max_bias
        )
        return list(self.session.exec(statement).all())
