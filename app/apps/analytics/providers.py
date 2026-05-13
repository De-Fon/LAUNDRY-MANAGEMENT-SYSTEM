from typing import Annotated

from fastapi import Depends

from app.apps.analytics.repository import AnalyticsRepository
from app.apps.analytics.service import AnalyticsService


def provide_analytics_repository() -> AnalyticsRepository:
    return AnalyticsRepository()


def provide_analytics_service(
    repository: Annotated[AnalyticsRepository, Depends(provide_analytics_repository)],
) -> AnalyticsService:
    return AnalyticsService(repository)
