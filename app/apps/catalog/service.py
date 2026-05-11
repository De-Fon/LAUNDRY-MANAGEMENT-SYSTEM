from fastapi import HTTPException, status
from redis import Redis

from app.apps.catalog.repository import CatalogRepository
from app.apps.catalog.schemas import (
    CategoryCatalogResponse,
    CategoryCreate,
    CategoryResponse,
    FullCatalogResponse,
    ServiceItemCreate,
    ServiceItemResponse,
    ServiceItemUpdate,
)
from sqlalchemy.orm import Session


CATALOG_FULL_KEY = "catalog:full"
CATALOG_TTL = 3600


class CatalogService:
    def __init__(self, repository: CatalogRepository) -> None:
        self.repository = repository

    def fetch_full_catalog(self, db: Session, redis_client: Redis) -> FullCatalogResponse:
        cached_catalog = redis_client.get(CATALOG_FULL_KEY)
        if cached_catalog:
            return FullCatalogResponse.model_validate_json(cached_catalog)

        categories = self.repository.get_full_catalog(db)
        catalog = FullCatalogResponse(
            categories=[CategoryCatalogResponse.model_validate(category) for category in categories],
        )
        redis_client.setex(CATALOG_FULL_KEY, CATALOG_TTL, catalog.model_dump_json())
        return catalog

    def fetch_categories(self, db: Session) -> list[CategoryResponse]:
        categories = self.repository.get_all_categories(db)
        return [CategoryResponse.model_validate(category) for category in categories]

    def fetch_items(self, db: Session, category_id: int | None = None) -> list[ServiceItemResponse]:
        items = self.repository.get_all_items(db, category_id)
        return [ServiceItemResponse.model_validate(item) for item in items]

    def fetch_item_by_id(self, db: Session, item_id: int) -> ServiceItemResponse:
        item = self.repository.get_item_by_id(db, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")
        return ServiceItemResponse.model_validate(item)

    def add_category(self, db: Session, redis_client: Redis, data: CategoryCreate) -> CategoryResponse:
        if not data.name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category name cannot be empty")

        if self.repository.get_category_by_name(db, data.name) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category name already exists")

        category = self.repository.create_category(db, data)
        self._invalidate_full_catalog(redis_client)
        return CategoryResponse.model_validate(category)

    def add_item(self, db: Session, redis_client: Redis, data: ServiceItemCreate) -> ServiceItemResponse:
        if data.base_price <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Base price must be greater than 0")

        if self.repository.get_category_by_id(db, data.category_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        if self.repository.get_item_by_name_in_category(db, data.category_id, data.name) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Item name already exists in this category",
            )

        item = self.repository.create_item(db, data)
        self._invalidate_full_catalog(redis_client)
        return ServiceItemResponse.model_validate(item)

    def update_item(
        self,
        db: Session,
        redis_client: Redis,
        item_id: int,
        data: ServiceItemUpdate,
    ) -> ServiceItemResponse:
        existing_item = self.repository.get_item_by_id(db, item_id)
        if existing_item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")

        target_category_id = data.category_id if data.category_id is not None else existing_item.category_id
        target_name = data.name if data.name is not None else existing_item.name

        if data.category_id is not None and self.repository.get_category_by_id(db, data.category_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        matching_item = self.repository.get_item_by_name_in_category(db, target_category_id, target_name)
        if matching_item is not None and matching_item.id != item_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Item name already exists in this category",
            )

        updated_item = self.repository.update_item(db, item_id, data)
        if updated_item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")

        self._invalidate_full_catalog(redis_client)
        return ServiceItemResponse.model_validate(updated_item)

    def remove_item(self, db: Session, redis_client: Redis, item_id: int) -> ServiceItemResponse:
        if self.repository.get_item_by_id(db, item_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")

        deleted_item = self.repository.soft_delete_item(db, item_id)
        if deleted_item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")

        self._invalidate_full_catalog(redis_client)
        return ServiceItemResponse.model_validate(deleted_item)

    def _invalidate_full_catalog(self, redis_client: Redis) -> None:
        redis_client.delete(CATALOG_FULL_KEY)
