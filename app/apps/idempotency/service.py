from datetime import UTC, datetime

from loguru import logger
from sqlalchemy.orm import Session
from typing import Any, Type

from app.apps.idempotency.repository import IdempotencyRepository


class IdempotencyService:
    def __init__(self, repository: IdempotencyRepository) -> None:
        self.repository = repository

    def find_duplicate(self, db: Session, entity_type: Type[Any], idempotency_key: str) -> Any | None:
        return self.repository.get_entity_by_idempotency_key(db, entity_type, idempotency_key)

    def log_duplicate(self, idempotency_key: str, resource_type: str, resource_owner_id: int) -> None:
        logger.warning(
            "DUPLICATE %s BLOCKED | key=%s owner=%s timestamp=%s",
            resource_type,
            idempotency_key,
            resource_owner_id,
            datetime.now(UTC).isoformat(),
        )
