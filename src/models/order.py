from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class OrderCreateRequest(BaseModel):
    user_id: UUID
    item_id: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0, le=1000)
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    model_config = ConfigDict(extra="forbid")


class OrderResponse(BaseModel):
    order_id: UUID
    user_id: UUID
    item_id: str
    quantity: int
    total_amount: Decimal
    status: OrderStatus

    model_config = ConfigDict(extra="forbid")