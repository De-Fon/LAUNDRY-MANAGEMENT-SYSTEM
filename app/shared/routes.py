from fastapi import FastAPI

from app.apps.analytics.routes import router as analytics_router
from app.apps.auth.routes import router as auth_router
from app.apps.bookings.routes import router as bookings_router
from app.apps.catalog.routes import router as catalog_router
from app.apps.credit_tab.routes import router as credit_tab_router

from app.apps.ledger.routes import router as ledger_router
from app.apps.notifications.routes import router as notifications_router
from app.apps.order_management.routes import router as order_management_router
from app.apps.payments.routes import router as payments_router
from app.apps.pricing.routes import router as pricing_router
from app.apps.users.routes import router as users_router
from app.apps.vendor_dashboard.routes import router as vendor_dashboard_router
from app.apps.waitlist.routes import router as waitlist_router


def register_routes(app: FastAPI) -> None:
    app.include_router(catalog_router)
    app.include_router(pricing_router)
    app.include_router(bookings_router)
    app.include_router(order_management_router)
    app.include_router(credit_tab_router)
    app.include_router(vendor_dashboard_router)
    app.include_router(ledger_router)
    app.include_router(auth_router)
    app.include_router(payments_router)
    app.include_router(notifications_router)
    app.include_router(users_router)
    app.include_router(waitlist_router)
    app.include_router(analytics_router)
