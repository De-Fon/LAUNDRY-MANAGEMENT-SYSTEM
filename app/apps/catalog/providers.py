from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis import Redis

from app.apps.catalog.repository import CatalogRepository
from app.apps.catalog.service import CatalogService
from app.core.settings import get_settings
from app.shared.auth import require_vendor


@lru_cache
def get_redis_client(redis_url: str) -> Redis:
    return Redis.from_url(redis_url, decode_responses=True)


def provide_redis() -> Redis:
    settings = get_settings()
    return get_redis_client(settings.redis_url)


def provide_catalog_repository() -> CatalogRepository:
    return CatalogRepository()


def provide_catalog_service(
    repository: Annotated[CatalogRepository, Depends(provide_catalog_repository)],
) -> CatalogService:
    return CatalogService(repository)
