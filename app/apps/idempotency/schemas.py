from pydantic import BaseModel, Field


class IdempotencyKeySchema(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=255)
