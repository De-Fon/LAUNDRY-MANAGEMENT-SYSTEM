from typing import Annotated

from fastapi import Depends

from app.apps.catalog.repository import CatalogRepository
from app.apps.catalog.service import CatalogService
from app.shared.auth import require_vendor


def provide_catalog_repository() -> CatalogRepository:
    return CatalogRepository()


def provide_catalog_service(
    repository: Annotated[CatalogRepository, Depends(provide_catalog_repository)],
) -> CatalogService:
    return CatalogService(repository)
