
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UsageEventInput(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    customer_id: int = Field(gt=0)
    event_type: Literal["voice", "sms", "data"]
    quantity: float = Field(gt=0, allow_inf_nan=False)
    timestamp: datetime


class UsageEventResponse(BaseModel):
    event_id: str
    customer_id: int
    event_type: Literal["voice", "sms", "data"]
    quantity: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)



from pydantic import field_validator


class UsageEventBatch(BaseModel):
    events: list[UsageEventInput] = Field(min_length=1, max_length=1000)
