from pydantic import BaseModel, ConfigDict, Field


class WashTypeCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    price_multiplier: float = Field(default=1.0, gt=0)
    duration_hours: int = Field(..., gt=0)


class WashTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price_multiplier: float
    duration_hours: int
    description: str | None


class PriceCalculationResponse(BaseModel):
    base_price: float
    multiplier: float
    final_price: float
