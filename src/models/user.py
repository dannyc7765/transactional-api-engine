from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class UserCreateRequest(BaseModel):
    username: str
    email: str
    initial_deposit: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID | str
    username: str
    email: str
    wallet_balance: Decimal