from pydantic import BaseModel


class HealthCheckSchema(BaseModel):
    status: str
    database: str
