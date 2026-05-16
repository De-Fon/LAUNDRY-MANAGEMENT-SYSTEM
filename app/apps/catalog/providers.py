from typing import Annotated

from fastapi import Depends
from redis import Redis

from app.apps.catalog.repository import CatalogRepository
from app.apps.catalog.service import CatalogService
from app.core.redis import get_redis


def provide_catalog_repository() -> CatalogRepository:
    return CatalogRepository()


def provide_redis() -> Redis:
    return get_redis()


def provide_catalog_service(
    repository: Annotated[CatalogRepository, Depends(provide_catalog_repository)],
) -> CatalogService:
    return CatalogService(repository)
