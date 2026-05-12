from fastapi import FastAPI

from app.apps.catalog.routes import router as catalog_router
from app.apps.credit_tab.routes import router as credit_tab_router
from app.apps.health.routes import router as health_router
from app.apps.order_management.routes import router as order_management_router
from app.apps.pricing.routes import router as pricing_router
from app.apps.vendor_dashboard.routes import router as vendor_dashboard_router


def register_routes(app: FastAPI) -> None:
    app.include_router(health_router)
    app.include_router(catalog_router)
    app.include_router(pricing_router)
    app.include_router(order_management_router)
    app.include_router(credit_tab_router)
    app.include_router(vendor_dashboard_router)
