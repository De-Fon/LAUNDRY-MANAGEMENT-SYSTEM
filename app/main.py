from fastapi import FastAPI

from app.core.logger import configure_logger, logger
from app.core.settings import get_settings
from app.shared.routes import register_routes
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.limiter import limiter, rate_limit_exceeded_handler


def create_app() -> FastAPI:
    configure_logger()
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} | env={'development' if settings.debug else 'production'}")
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    # Register limiter on app state — SlowAPI reads from here
    app.state.limiter = limiter

    # Register custom 429 handler
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Add SlowAPI middleware
    app.add_middleware(SlowAPIMiddleware)

    register_routes(app)
    logger.info("All routes registered successfully")
    return app


app = create_app()
