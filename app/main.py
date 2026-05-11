from fastapi import FastAPI

from app.core.settings import get_settings
from app.shared.routes import register_routes


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    register_routes(app)
    return app


app = create_app()
