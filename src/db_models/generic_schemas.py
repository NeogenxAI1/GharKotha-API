from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime



class UserProfileOutput(BaseModel):
    first_name: str
    last_name: str
    gender: Optional[str] = Field(None, max_length=20)
    age: int
    own_language_id: int | None = None
    fcm_token: Optional[str] = None
    email: str
    language_learning_to_id: Optional[int] = None
    audio_play_speed: Optional[float] = 1.0

    class Config:
        from_attributes = True


class AppVersionResponse(BaseModel):
    version_number: str
    description: str
    created_at: datetime
    force_update: bool = True
    android_url: str | None = None
    ios_url: str | None = None

    class Config:
        from_attributes = True     
        
        
class TermsAndConditonOutput(BaseModel):
    id : int
    created_at : datetime | None = None
    description : str | None = None

    class Config:
        from_attributes = True

class SubscriptionDetailsOutput(BaseModel):
    id: int
    email: str | None = None
    phone: str | None = None
    qrimage: str | None = None

    class Config:
        from_attributes = True

class SubscriptionOutput(BaseModel):
    id: int
    user_id: UUID
    plan_id: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str  | None = None
    trial_end_date: datetime | None = None
    canceled_at: datetime | None = None
    # created_at: datetime

    class Config:
        from_attributes = True

class PlanOutput(BaseModel):
    id: int
    name: str | None = None
    description: str | None = None
    price: float | None = None
    billing_cycle: str  | None = None
    # created_at: datetime | None = None

    class Config:
        from_attributes = True


        from_attributes  = True 