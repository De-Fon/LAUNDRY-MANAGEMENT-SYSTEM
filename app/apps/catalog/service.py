from fastapi import HTTPException, status
from redis import Redis
from sqlalchemy.orm import Session

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
from app.core.logger import logger

CATALOG_FULL_KEY = "catalog:full"
CATALOG_ITEMS_KEY = "catalog:items"
CATALOG_CATEGORIES_KEY = "catalog:categories"
CATALOG_TTL = 3600  # 1 hour

class CatalogService:
    def __init__(self, repository: CatalogRepository) -> None:
        self.repository = repository

    def _invalidate_cache(self, redis: Redis) -> None:
        keys = [CATALOG_FULL_KEY, CATALOG_ITEMS_KEY, CATALOG_CATEGORIES_KEY]
        for key in keys:
            redis.delete(key)
        logger.info("Catalog cache invalidated")

    def fetch_full_catalog(self, db: Session, redis: Redis) -> tuple[FullCatalogResponse, bool]:
        cached = redis.get(CATALOG_FULL_KEY)
        if cached:
            logger.info("catalog:full served from Redis cache | cache=HIT")
            return FullCatalogResponse.model_validate_json(cached), True

        logger.info("catalog:full fetched from database | cache=MISS")
        result = FullCatalogResponse(
            categories=[
                CategoryCatalogResponse.model_validate(category)
                for category in self.repository.get_full_catalog(db)
            ]
        )
        redis.setex(CATALOG_FULL_KEY, CATALOG_TTL, result.model_dump_json())
        return result, False

    def fetch_categories(self, db: Session) -> list[CategoryResponse]:
        return [CategoryResponse.model_validate(category) for category in self.repository.get_all_categories(db)]

    def fetch_items(self, db: Session, category_id: int | None = None) -> list[ServiceItemResponse]:
        return [ServiceItemResponse.model_validate(item) for item in self.repository.get_all_items(db, category_id)]

    def fetch_item_by_id(self, db: Session, item_id: int) -> ServiceItemResponse:
        item = self.repository.get_item_by_id(db, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")
        return ServiceItemResponse.model_validate(item)

    def add_category(self, db: Session, data: CategoryCreate, redis: Redis) -> CategoryResponse:
        if not data.name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category name cannot be empty")
        if self.repository.get_category_by_name(db, data.name) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category name already exists")

        category = self.repository.create_category(db, data)
        self._invalidate_cache(redis)
        return CategoryResponse.model_validate(category)

    def add_item(self, db: Session, data: ServiceItemCreate, redis: Redis) -> ServiceItemResponse:
        if data.base_price <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Base price must be greater than 0")
        if self.repository.get_category_by_id(db, data.category_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        item_check = self.repository.get_item_by_name_in_category(db, data.category_id, data.name)
        if item_check is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Item name already exists in this category")

        item = self.repository.create_item(db, data)
        self._invalidate_cache(redis)
        return ServiceItemResponse.model_validate(item)

    def update_item(
        self,
        db: Session,
        item_id: int,
        data: ServiceItemUpdate,
        redis: Redis,
    ) -> ServiceItemResponse:
        item = self.repository.get_item_by_id(db, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")

        category_id = data.category_id if data.category_id is not None else item.category_id
        name = data.name if data.name is not None else item.name

        if data.category_id is not None and self.repository.get_category_by_id(db, data.category_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        item_check = self.repository.get_item_by_name_in_category(db, category_id, name)
        if item_check is not None and item_check.id != item_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Item name already exists in this category")

        updated_item = self.repository.update_item(db, item_id, data)
        if updated_item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")

        self._invalidate_cache(redis)
        return ServiceItemResponse.model_validate(updated_item)

    def remove_item(self, db: Session, item_id: int, redis: Redis) -> ServiceItemResponse:
        item = self.repository.get_item_by_id(db, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")

        deleted_item = self.repository.soft_delete_item(db, item_id)
        if deleted_item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")

        self._invalidate_cache(redis)
        return ServiceItemResponse.model_validate(deleted_item)
