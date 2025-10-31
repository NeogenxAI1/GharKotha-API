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
    qr_image: str | None = None

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
    details:str | None = None

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
    # description: Optional[str] = None
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
    details: Optional[str] = None
    distance_km: Optional[float] = None
    # for favorite feature
    is_favorite: bool = False
    favorite_id: Optional[int] = None
    favorite_created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CountryOutput(BaseModel):
    id: int
    country_name: str
    country_code: str
    country_currency: str
    country_phone_code: str
    currency_symbol: str | None = None

    class Config:
        from_attributes = True

# For Nepal Community Web App Outputs
class UserVisitTrackingOutput(BaseModel):
    uuid_ip: str
    ip: str | None = None
    state: str | None = None
    city: str | None = None
    created_at: datetime | None = None
    logged_counts: int 
    lat: float | None = None
    lon: float | None = None

    class Config:
        from_attributes = True

# For Nepal Community Web App Outputs
class FamilyCountsOutput(BaseModel):
    city: str
    state: str
    family_count: int | None = None
    is_active: bool | None = None

    class Config:
        from_attributes = True

# For Nepal Community Web App Outputs
class CommunityInfoOutput(BaseModel):
    id: int
    state: str
    title: str 
    description: str 
    url: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None
    is_verified: bool | None = None
    email: str 
    post_type_id: int | None = None
    is_email_sent: bool | None = None
    is_promote: bool | None = None

    class Config:
        from_attributes = True

# For Nepal Community Web App Outputs
class FamilyNumberSubmittedOutput(BaseModel):
    id: int
    uuid_ip: str
    state: str | None = None
    city: str | None = None
    is_verified: bool | None = None
    family_number: int 
    created_at: datetime | None = None

    class Config:
        from_attributes = True

# For Nepal Community Web App Outputs
class CityStateOutput(BaseModel):
    id: int
    city: str
    state_abbr: str
    state_name: str
    county_fips: str | None = None
    lat: str | None = None
    lon: str | None = None
    county_name: str | None = None

    class Config:
        from_attributes = True

# For Nepal Community Web App Outputs
class UserDeviceInfoOutput(BaseModel):
    id: int
    ip_uuid: str
    device: str | None = None
    os: str | None = None
    browser: str | None = None
    engine: str | None = None
    cpu: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True

# For Nepal Community Web App Outputs
class PostTypeOutput(BaseModel):
    id: int
    post_type: str
    is_active: bool | None = None

    class Config:
        from_attributes = True


class FavoritesOutput(BaseModel):
    id: int
    user_id: UUID
    listing_id: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True

class CityStateOutput(BaseModel):
    id: int
    city_state: str  # Combined city + state string
    city:str
    state_abbr:str
    class Config:
        from_attributes = True
    
class MyListingsOutput(BaseModel):
    id: int
    user_id: UUID
    listing_id: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True

