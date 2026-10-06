from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ProductResponse(BaseModel):
    product_id: UUID | str
    name: str
    stock: int
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class PurchaseRequest(BaseModel):
    user_id: UUID | str
    product_id: UUID | str