from typing import Annotated

from fastapi import Depends
from redis import Redis

from app.apps.catalog.repository import CatalogRepository
from app.apps.catalog.service import CatalogService
from app.shared.auth import require_vendor
from app.core.settings import get_settings


def provide_redis() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


def provide_catalog_repository() -> CatalogRepository:
    return CatalogRepository()


def provide_catalog_service(
    repository: Annotated[CatalogRepository, Depends(provide_catalog_repository)],
) -> CatalogService:
    return CatalogService(repository)
