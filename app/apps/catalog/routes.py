from typing import Annotated

from fastapi import APIRouter, Depends, Query
from redis import Redis
from sqlalchemy.orm import Session

from app.apps.catalog.providers import provide_catalog_service, provide_redis, require_vendor
from app.apps.catalog.schemas import (
    CategoryCreate,
    CategoryResponse,
    FullCatalogResponse,
    ServiceItemCreate,
    ServiceItemResponse,
    ServiceItemUpdate,
)
from app.apps.catalog.service import CatalogService
from app.core.database import get_db


router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get("/full", response_model=FullCatalogResponse)
def get_full_catalog(
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[Redis, Depends(provide_redis)],
    service: Annotated[CatalogService, Depends(provide_catalog_service)],
) -> FullCatalogResponse:
    return service.fetch_full_catalog(db, redis_client)


@router.get("/categories", response_model=list[CategoryResponse])
def get_categories(
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[CatalogService, Depends(provide_catalog_service)],
) -> list[CategoryResponse]:
    return service.fetch_categories(db)


@router.get("/items", response_model=list[ServiceItemResponse])
def get_items(
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[CatalogService, Depends(provide_catalog_service)],
    category_id: Annotated[int | None, Query()] = None,
) -> list[ServiceItemResponse]:
    return service.fetch_items(db, category_id)


@router.get("/items/{item_id}", response_model=ServiceItemResponse)
def get_item(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[CatalogService, Depends(provide_catalog_service)],
) -> ServiceItemResponse:
    return service.fetch_item_by_id(db, item_id)


@router.post("/categories", response_model=CategoryResponse, dependencies=[Depends(require_vendor)])
def create_category(
    data: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[Redis, Depends(provide_redis)],
    service: Annotated[CatalogService, Depends(provide_catalog_service)],
) -> CategoryResponse:
    return service.add_category(db, redis_client, data)


@router.post("/items", response_model=ServiceItemResponse, dependencies=[Depends(require_vendor)])
def create_item(
    data: ServiceItemCreate,
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[Redis, Depends(provide_redis)],
    service: Annotated[CatalogService, Depends(provide_catalog_service)],
) -> ServiceItemResponse:
    return service.add_item(db, redis_client, data)


@router.put("/items/{item_id}", response_model=ServiceItemResponse, dependencies=[Depends(require_vendor)])
def update_item(
    item_id: int,
    data: ServiceItemUpdate,
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[Redis, Depends(provide_redis)],
    service: Annotated[CatalogService, Depends(provide_catalog_service)],
) -> ServiceItemResponse:
    return service.update_item(db, redis_client, item_id, data)


@router.delete("/items/{item_id}", response_model=ServiceItemResponse, dependencies=[Depends(require_vendor)])
def delete_item(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[Redis, Depends(provide_redis)],
    service: Annotated[CatalogService, Depends(provide_catalog_service)],
) -> ServiceItemResponse:
    return service.remove_item(db, redis_client, item_id)
