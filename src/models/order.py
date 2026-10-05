from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class OrderCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: UUID
    item_id: str = Field(min_length=3, max_length=64)
    quantity: int = Field(gt=0, le=100)
    price: float = Field(gt=0.0)

class OrderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    order_id: UUID
    user_id: UUID
    item_id: str
    quantity: int
    total_amount: float = Field(gt=0.0)
    status: OrderStatus
