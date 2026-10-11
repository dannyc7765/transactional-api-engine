from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ProductResponse(BaseModel):
    product_id: UUID | str
    name: str
    stock: int
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class PurchaseRequest(BaseModel):
    user_id: UUID
    product_id: str = Field(min_length=1, max_length=100)