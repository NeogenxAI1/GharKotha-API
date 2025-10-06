from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime



class UserProfileOutput(BaseModel):
    first_name: str
    last_name: str
    fcm_token: Optional[str] = None
    email: str
    phone: str | None = None
    latitude: float | None = None
    longitude: float | None = None

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

class ListingsOutput(BaseModel):
    id: int
    title: str
    description: str
    price: int
    status: str | None = None
    views: int | None = None
    created_at: datetime | None = None

    contact_name: str | None = None
    contact_number: int | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    
    class Config:
        from_attributes = True
    
class ListingSpaceOutput(BaseModel):
    id: int
    listing_id: int
    space_type: str | None = None
    bedroom: int | None = None
    bathroom: int | None = None
    kitchen: int | None = None
    square_feet: int
    living_room: int | None = None

    class Config:
        from_attributes = True

class ImageOutput(BaseModel):
    id: int
    listing_id: int
    image_url: str | None = None

    class Config:
        from_attributes = True


class ListingOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    price: float
    status: str
    views: Optional[int] = None
    created_at: datetime
    contact_name: str
    contact_number: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    square_feet: Optional[int] = None
    bedrooms: Optional[int] = None
    bathroom: Optional[int] = None
    kitchen: Optional[int] = None
    living_room: Optional[int] = None
    space_type: Optional[str] = None
    images: List[Optional[str]] = []
    distance_km: Optional[float] = None

    class Config:
        from_attributes = True