from typing import Any, Type

from sqlalchemy import select
from sqlalchemy.orm import Session


class IdempotencyRepository:
    def get_entity_by_idempotency_key(self, db: Session, model: Type[Any], key: str) -> Any | None:
        statement = select(model).where(model.idempotency_key == key)
        return db.scalar(statement)
