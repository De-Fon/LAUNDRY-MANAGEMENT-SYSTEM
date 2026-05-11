from typing import Annotated

from fastapi import APIRouter, Depends

from app.apps.health.providers import get_health_service
from app.apps.health.schemas import HealthCheckSchema
from app.apps.health.service import HealthService


router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthCheckSchema)
def health_check(service: Annotated[HealthService, Depends(get_health_service)]) -> HealthCheckSchema:
    return service.check()
