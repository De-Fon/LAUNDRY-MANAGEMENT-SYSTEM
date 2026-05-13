from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.apps.catalog.models import ServiceItem
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


class CatalogService:
    def __init__(self, repository: CatalogRepository) -> None:
        self.repository = repository

    def fetch_full_catalog(self, db: Session) -> FullCatalogResponse:
        return FullCatalogResponse(
            categories=[
                CategoryCatalogResponse.model_validate(category)
                for category in self.repository.get_full_catalog(db)
            ]
        )

    def fetch_categories(self, db: Session) -> list[CategoryResponse]:
        return [CategoryResponse.model_validate(category) for category in self.repository.get_all_categories(db)]

    def fetch_items(self, db: Session, category_id: int | None = None) -> list[ServiceItemResponse]:
        return [ServiceItemResponse.model_validate(item) for item in self.repository.get_all_items(db, category_id)]

    def fetch_item_by_id(self, db: Session, item_id: int) -> ServiceItemResponse:
        return ServiceItemResponse.model_validate(self._get_item_or_404(db, item_id))

    def add_category(self, db: Session, data: CategoryCreate) -> CategoryResponse:
        self._validate_category_create(db, data)
        category = self.repository.create_category(db, data)
        return CategoryResponse.model_validate(category)

    def add_item(self, db: Session, data: ServiceItemCreate) -> ServiceItemResponse:
        self._validate_item_create(db, data)
        item = self.repository.create_item(db, data)
        return ServiceItemResponse.model_validate(item)

    def update_item(
        self,
        db: Session,
        item_id: int,
        data: ServiceItemUpdate,
    ) -> ServiceItemResponse:
        item = self._get_item_or_404(db, item_id)
        self._validate_item_update(db, item.id, item.category_id, item.name, data)

        updated_item = self.repository.update_item(db, item_id, data)
        if updated_item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")

        return ServiceItemResponse.model_validate(updated_item)

    def remove_item(self, db: Session, item_id: int) -> ServiceItemResponse:
        self._get_item_or_404(db, item_id)
        deleted_item = self.repository.soft_delete_item(db, item_id)
        if deleted_item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")

        return ServiceItemResponse.model_validate(deleted_item)

    def _get_item_or_404(self, db: Session, item_id: int) -> ServiceItem:
        item = self.repository.get_item_by_id(db, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")
        return item

    def _validate_category_create(self, db: Session, data: CategoryCreate) -> None:
        if not data.name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category name cannot be empty")
        if self.repository.get_category_by_name(db, data.name) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category name already exists")

    def _validate_item_create(self, db: Session, data: ServiceItemCreate) -> None:
        if data.base_price <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Base price must be greater than 0")
        if self.repository.get_category_by_id(db, data.category_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        self._ensure_item_name_available(db, data.category_id, data.name)

    def _validate_item_update(
        self,
        db: Session,
        item_id: int,
        current_category_id: int,
        current_name: str,
        data: ServiceItemUpdate,
    ) -> None:
        category_id = data.category_id if data.category_id is not None else current_category_id
        name = data.name if data.name is not None else current_name

        if data.category_id is not None and self.repository.get_category_by_id(db, data.category_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        self._ensure_item_name_available(db, category_id, name, excluded_item_id=item_id)

    def _ensure_item_name_available(
        self,
        db: Session,
        category_id: int,
        name: str,
        excluded_item_id: int | None = None,
    ) -> None:
        item = self.repository.get_item_by_name_in_category(db, category_id, name)
        if item is not None and item.id != excluded_item_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Item name already exists in this category",
            )
