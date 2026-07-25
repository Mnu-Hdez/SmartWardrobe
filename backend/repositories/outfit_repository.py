from typing import List, Optional
from sqlmodel import Session, select
from backend.models.garment import Outfit, OutfitCreate, OutfitUpdate, OutfitGarmentLink
from backend.database.connection import get_db_session


class OutfitRepository:
    """Repository for Outfit operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, outfit: OutfitCreate) -> Outfit:
        # Create outfit
        db_outfit = Outfit(
            name=outfit.name,
            occasion=outfit.occasion,
            season=outfit.season,
            formality=outfit.formality,
            is_packing=outfit.is_packing,
            packing_days=outfit.packing_days
        )
        self.session.add(db_outfit)
        self.session.commit()
        self.session.refresh(db_outfit)
        
        # Add garment links
        for position, garment_id in enumerate(outfit.garment_ids):
            link = OutfitGarmentLink(
                outfit_id=db_outfit.id,
                garment_id=garment_id,
                position=position
            )
            self.session.add(link)
        
        self.session.commit()
        self.session.refresh(db_outfit)
        return db_outfit
    
    def get_by_id(self, outfit_id: int) -> Optional[Outfit]:
        return self.session.get(Outfit, outfit_id)
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Outfit]:
        statement = select(Outfit).offset(skip).limit(limit).order_by(Outfit.created_at.desc())
        return list(self.session.exec(statement).all())
    
    def get_by_occasion(self, occasion: str, skip: int = 0, limit: int = 100) -> List[Outfit]:
        statement = select(Outfit).where(Outfit.occasion == occasion).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())
    
    def get_by_season(self, season: str, skip: int = 0, limit: int = 100) -> List[Outfit]:
        statement = select(Outfit).where(Outfit.season == season).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())
    
    def get_packing_outfits(self, days: int = None) -> List[Outfit]:
        statement = select(Outfit).where(Outfit.is_packing == True)
        if days:
            statement = statement.where(Outfit.packing_days == days)
        return list(self.session.exec(statement).all())
    
    def update(self, outfit_id: int, outfit: OutfitUpdate) -> Optional[Outfit]:
        db_outfit = self.get_by_id(outfit_id)
        if not db_outfit:
            return None
        
        update_data = outfit.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_outfit, field, value)
        
        self.session.add(db_outfit)
        self.session.commit()
        self.session.refresh(db_outfit)
        return db_outfit
    
    def delete(self, outfit_id: int) -> bool:
        db_outfit = self.get_by_id(outfit_id)
        if not db_outfit:
            return False
        
        # Delete garment links first
        links_statement = select(OutfitGarmentLink).where(OutfitGarmentLink.outfit_id == outfit_id)
        for link in self.session.exec(links_statement).all():
            self.session.delete(link)
        
        self.session.delete(db_outfit)
        self.session.commit()
        return True
    
    def get_garments_for_outfit(self, outfit_id: int) -> List[int]:
        """Get garment IDs for an outfit."""
        statement = select(OutfitGarmentLink).where(OutfitGarmentLink.outfit_id == outfit_id).order_by(OutfitGarmentLink.position)
        links = self.session.exec(statement).all()
        return [link.garment_id for link in links]
    
    def add_garment_to_outfit(self, outfit_id: int, garment_id: int, position: int = None) -> bool:
        outfit = self.get_by_id(outfit_id)
        if not outfit:
            return False
        
        # Check if already exists
        existing = self.session.exec(
            select(OutfitGarmentLink).where(
                OutfitGarmentLink.outfit_id == outfit_id,
                OutfitGarmentLink.garment_id == garment_id
            )
        ).first()
        if existing:
            return False
        
        if position is None:
            # Get max position
            max_pos = self.session.exec(
                select(OutfitGarmentLink.position).where(OutfitGarmentLink.outfit_id == outfit_id)
            ).all()
            position = max(max_pos, default=-1) + 1
        
        link = OutfitGarmentLink(outfit_id=outfit_id, garment_id=garment_id, position=position)
        self.session.add(link)
        self.session.commit()
        return True
    
    def remove_garment_from_outfit(self, outfit_id: int, garment_id: int) -> bool:
        link = self.session.exec(
            select(OutfitGarmentLink).where(
                OutfitGarmentLink.outfit_id == outfit_id,
                OutfitGarmentLink.garment_id == garment_id
            )
        ).first()
        if not link:
            return False
        self.session.delete(link)
        self.session.commit()
        return True