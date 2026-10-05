from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

class OrderCreateRequest(BaseModel):
    user_id: UUID | str
    item_id: str
    quantity: int = Field(gt=0)
    price: float = Field(gt=0.0)

class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    order_id: UUID | str
    user_id: UUID | str
    item_id: str
    quantity: int
    total_amount: float
    status: OrderStatus
