from app.apps.health.repository import HealthRepository
from app.apps.health.schemas import HealthCheckSchema


class HealthService:
    def __init__(self, repository: HealthRepository) -> None:
        self.repository = repository

    def check(self) -> HealthCheckSchema:
        database_status = "ok" if self.repository.database_is_available() else "unavailable"
        app_status = "ok" if database_status == "ok" else "degraded"
        return HealthCheckSchema(status=app_status, database=database_status)
