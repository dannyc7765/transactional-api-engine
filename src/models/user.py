from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    initial_deposit: float = Field(gt=0.0)

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: UUID
    username: str
    email: EmailStr
    wallet_balance: float = Field(ge=0.0)
