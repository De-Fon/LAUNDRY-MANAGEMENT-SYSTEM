from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None


class ServiceItemCreate(BaseModel):
    category_id: int
    name: str = Field(..., min_length=2, max_length=150)
    description: str | None = None
    base_price: float = Field(..., gt=0)


class ServiceItemUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    base_price: float | None = Field(default=None, gt=0)
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: datetime


class ServiceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    base_price: float
    is_active: bool
    category: CategoryResponse


class CategoryCatalogResponse(CategoryResponse):
    items: list[ServiceItemResponse]


class FullCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    categories: list[CategoryCatalogResponse]
