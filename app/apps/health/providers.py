from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.apps.health.repository import HealthRepository
from app.apps.health.service import HealthService
from app.core.database import get_db


def get_health_repository(db: Annotated[Session, Depends(get_db)]) -> HealthRepository:
    return HealthRepository(db)


def get_health_service(
    repository: Annotated[HealthRepository, Depends(get_health_repository)],
) -> HealthService:
    return HealthService(repository)
