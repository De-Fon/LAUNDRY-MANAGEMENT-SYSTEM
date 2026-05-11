from fastapi import FastAPI

from app.apps.catalog.routes import router as catalog_router
from app.apps.health.routes import router as health_router
from app.apps.pricing.routes import router as pricing_router


def register_routes(app: FastAPI) -> None:
    app.include_router(health_router)
    app.include_router(catalog_router)
    app.include_router(pricing_router)
