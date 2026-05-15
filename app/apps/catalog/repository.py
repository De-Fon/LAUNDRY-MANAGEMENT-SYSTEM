from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, with_loader_criteria

from app.apps.catalog.models import Category, ServiceItem
from app.apps.catalog.schemas import CategoryCreate, ServiceItemCreate, ServiceItemUpdate


class CatalogRepository:
    def get_all_categories(self, db: Session) -> list[Category]:
        statement = select(Category).where(Category.is_active.is_(True)).order_by(Category.name)
        return list(db.scalars(statement).all())

    def get_category_by_id(self, db: Session, category_id: int) -> Category | None:
        statement = select(Category).where(Category.id == category_id, Category.is_active.is_(True))
        return db.scalar(statement)

    def get_category_by_name(self, db: Session, name: str) -> Category | None:
        statement = select(Category).where(Category.name == name)
        return db.scalar(statement)

    def get_all_items(self, db: Session, category_id: int | None = None) -> list[ServiceItem]:
        statement = (
            select(ServiceItem)
            .options(joinedload(ServiceItem.category))
            .where(ServiceItem.is_active.is_(True))
            .order_by(ServiceItem.name)
        )

        if category_id is not None:
            statement = statement.where(ServiceItem.category_id == category_id)

        return list(db.scalars(statement).all())

    def get_item_by_id(self, db: Session, item_id: int) -> ServiceItem | None:
        statement = (
            select(ServiceItem)
            .options(joinedload(ServiceItem.category))
            .where(ServiceItem.id == item_id, ServiceItem.is_active.is_(True))
        )
        return db.scalar(statement)

    def get_item_by_name_in_category(self, db: Session, category_id: int, name: str) -> ServiceItem | None:
        statement = select(ServiceItem).where(ServiceItem.category_id == category_id, ServiceItem.name == name)
        return db.scalar(statement)

    def create_category(self, db: Session, data: CategoryCreate) -> Category:
        category = Category(**data.model_dump())
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    def create_item(self, db: Session, data: ServiceItemCreate) -> ServiceItem:
        item = ServiceItem(**data.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return self.get_item_by_id(db, item.id) or item

    def soft_delete_item(self, db: Session, item_id: int) -> ServiceItem | None:
        item = self.get_item_by_id(db, item_id)
        if item is None:
            return None

        item.is_active = False
        db.commit()
        db.refresh(item)
        return item

    def update_item(self, db: Session, item_id: int, data: ServiceItemUpdate) -> ServiceItem | None:
        item = self.get_item_by_id(db, item_id)
        if item is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)

        db.commit()
        db.refresh(item)
        return self.get_item_by_id(db, item.id) or item

    def get_full_catalog(self, db: Session) -> list[Category]:
        categories_statement = (
            select(Category)
            .options(
                joinedload(Category.items),
                with_loader_criteria(ServiceItem, ServiceItem.is_active.is_(True)),
            )
            .where(Category.is_active.is_(True))
            .order_by(Category.name)
        )
        return list(db.scalars(categories_statement).unique().all())
