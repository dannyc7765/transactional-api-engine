from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class UserCreateRequest(BaseModel):
    username: str
    email: str
    initial_deposit: float = Field(default=0.0, ge=0.0)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    user_id: UUID | str
    username: str
    email: str
    wallet_balance: float
