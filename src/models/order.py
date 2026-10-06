from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class OrderCreateRequest(BaseModel):
    user_id: UUID | str
    item_id: str
    quantity: int
    price: float

    model_config = ConfigDict(extra="forbid")


class OrderResponse(BaseModel):
    order_id: UUID | str
    user_id: UUID | str
    item_id: str
    quantity: int
    total_amount: float
    status: OrderStatus

    model_config = ConfigDict(extra="forbid")