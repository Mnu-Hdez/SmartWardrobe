import json

from sqlmodel import Session, select

from backend.models.garment import StyleRule
from backend.models.schemas import StyleRuleCreate, StyleRuleUpdate


class StyleRuleRepository:
    """Repository for StyleRule operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, rule: StyleRuleCreate) -> StyleRule:
        db_rule = StyleRule(
            name=rule.name,
            description=rule.description,
            rule_type=rule.rule_type,
            weight=rule.weight,
            is_active=rule.is_active,
            parameters=json.dumps(rule.parameters) if rule.parameters else "{}",
        )
        self.session.add(db_rule)
        self.session.commit()
        self.session.refresh(db_rule)
        return db_rule

    def get_by_id(self, rule_id: int) -> StyleRule | None:
        return self.session.get(StyleRule, rule_id)

    def get_by_name(self, name: str) -> StyleRule | None:
        statement = select(StyleRule).where(StyleRule.name == name)
        return self.session.exec(statement).first()

    def get_all(self, active_only: bool = True) -> list[StyleRule]:
        statement = select(StyleRule)
        if active_only:
            statement = statement.where(StyleRule.is_active)
        return list(self.session.exec(statement).all())

    def get_by_type(self, rule_type: str) -> list[StyleRule]:
        statement = select(StyleRule).where(StyleRule.rule_type == rule_type, StyleRule.is_active)
        return list(self.session.exec(statement).all())

    def update(self, rule_id: int, rule: StyleRuleUpdate) -> StyleRule | None:
        db_rule = self.get_by_id(rule_id)
        if not db_rule:
            return None

        update_data = rule.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "parameters" and value is not None:
                setattr(db_rule, field, json.dumps(value))
            else:
                setattr(db_rule, field, value)

        self.session.add(db_rule)
        self.session.commit()
        self.session.refresh(db_rule)
        return db_rule

    def delete(self, rule_id: int) -> bool:
        db_rule = self.get_by_id(rule_id)
        if not db_rule:
            return False
        self.session.delete(db_rule)
        self.session.commit()
        return True
