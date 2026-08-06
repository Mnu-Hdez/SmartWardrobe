# Smart Wardrobe - Data Access Layer
# Repository pattern for database operations

from typing import Any

from backend.models.garment import Garment, Outfit, OutfitItem, StyleRule
from backend.models.schemas import (
    GarmentUpdate,
    StyleRuleUpdate,
)
from sqlalchemy import and_, or_
from sqlmodel import Session, delete, func, select


class GarmentRepository:
    """Data access for Garments"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, garment: Garment) -> Garment:
        self.session.add(garment)
        self.session.commit()
        self.session.refresh(garment)
        return garment

    def get_by_id(self, garment_id: int) -> Garment | None:
        return self.session.get(Garment, garment_id)

    def get_all(
        self, limit: int = 100, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> list[Garment]:
        query = select(Garment).order_by(Garment.created_at.desc())

        if filters:
            conditions = []
            if filters.get("search"):
                search = f"%{filters['search'].lower()}%"
                conditions.append(
                    or_(
                        Garment.name.ilike(search),
                        Garment.color_name.ilike(search),
                        Garment.brand.ilike(search),
                    )
                )
            if filters.get("type"):
                conditions.append(Garment.type == filters["type"])
            if filters.get("season"):
                conditions.append(
                    or_(Garment.season == filters["season"], Garment.season == "all_season")
                )
            if conditions:
                query = query.where(and_(*conditions))

        query = query.offset(offset).limit(limit)
        return list(self.session.exec(query).all())

    def count(self, filters: dict[str, Any] | None = None) -> int:
        query = select(func.count(Garment.id))

        if filters:
            conditions = []
            if filters.get("search"):
                search = f"%{filters['search'].lower()}%"
                conditions.append(
                    or_(
                        Garment.name.ilike(search),
                        Garment.color_name.ilike(search),
                        Garment.brand.ilike(search),
                    )
                )
            if filters.get("type"):
                conditions.append(Garment.type == filters["type"])
            if filters.get("season"):
                conditions.append(
                    or_(Garment.season == filters["season"], Garment.season == "all_season")
                )
            if conditions:
                query = query.where(and_(*conditions))

        return self.session.exec(query).one()

    def update(self, garment_id: int, data: GarmentUpdate) -> Garment | None:
        garment = self.get_by_id(garment_id)
        if not garment:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(garment, key, value)

        from datetime import datetime

        garment.updated_at = datetime.utcnow()

        self.session.add(garment)
        self.session.commit()
        self.session.refresh(garment)
        return garment

    def delete(self, garment_id: int) -> bool:
        garment = self.get_by_id(garment_id)
        if not garment:
            return False
        self.session.delete(garment)
        self.session.commit()
        return True

    def bulk_delete(self, garment_ids: list[int]) -> int:
        if not garment_ids:
            return 0
        statement = delete(Garment).where(Garment.id.in_(garment_ids))
        result = self.session.exec(statement)
        self.session.commit()
        return result.rowcount


class OutfitRepository:
    """Data access for Outfits"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, outfit: Outfit) -> Outfit:
        self.session.add(outfit)
        self.session.commit()
        self.session.refresh(outfit)
        return outfit

    def get_by_id(self, outfit_id: int) -> Outfit | None:
        return self.session.get(Outfit, outfit_id)

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Outfit]:
        query = select(Outfit).order_by(Outfit.created_at.desc())
        query = query.offset(offset).limit(limit)
        return list(self.session.exec(query).all())

    def count(self) -> int:
        return self.session.exec(select(func.count(Outfit.id))).one()

    def delete(self, outfit_id: int) -> bool:
        outfit = self.get_by_id(outfit_id)
        if not outfit:
            return False
        self.session.delete(outfit)
        self.session.commit()
        return True


class OutfitItemRepository:
    """Data access for Outfit Items"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, item: OutfitItem) -> OutfitItem:
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def get_by_outfit(self, outfit_id: int) -> list[OutfitItem]:
        query = (
            select(OutfitItem)
            .where(OutfitItem.outfit_id == outfit_id)
            .order_by(OutfitItem.position)
        )
        return list(self.session.exec(query).all())

    def bulk_create(self, items: list[OutfitItem]) -> list[OutfitItem]:
        self.session.add_all(items)
        self.session.commit()
        for item in items:
            self.session.refresh(item)
        return items

    def delete_by_outfit(self, outfit_id: int) -> int:
        statement = delete(OutfitItem).where(OutfitItem.outfit_id == outfit_id)
        result = self.session.exec(statement)
        self.session.commit()
        return result.rowcount


class StyleRuleRepository:
    """Data access for Style Rules"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, rule: StyleRule) -> StyleRule:
        self.session.add(rule)
        self.session.commit()
        self.session.refresh(rule)
        return rule

    def get_by_id(self, rule_id: int) -> StyleRule | None:
        return self.session.get(StyleRule, rule_id)

    def get_all(
        self, active_only: bool = True, limit: int = 100, offset: int = 0
    ) -> list[StyleRule]:
        query = select(StyleRule).order_by(StyleRule.created_at.desc())
        if active_only:
            query = query.where(StyleRule.is_active)
        query = query.offset(offset).limit(limit)
        return list(self.session.exec(query).all())

    def count(self, active_only: bool = True) -> int:
        query = select(func.count(StyleRule.id))
        if active_only:
            query = query.where(StyleRule.is_active)
        return self.session.exec(query).one()

    def update(self, rule_id: int, data: StyleRuleUpdate) -> StyleRule | None:
        rule = self.get_by_id(rule_id)
        if not rule:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rule, key, value)

        self.session.add(rule)
        self.session.commit()
        self.session.refresh(rule)
        return rule

    def delete(self, rule_id: int) -> bool:
        rule = self.get_by_id(rule_id)
        if not rule:
            return False
        self.session.delete(rule)
        self.session.commit()
        return True
