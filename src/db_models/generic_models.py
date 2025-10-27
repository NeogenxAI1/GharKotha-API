# schemas.py
from pydantic import BaseModel
from sqlalchemy import CheckConstraint, Column, Integer, String, Boolean, Float, func, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from core.database import Base
from sqlalchemy.orm import relationship

class UserProfile(Base):
    __tablename__ = 'user_profile'
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    fcm_token = Column(String, nullable=True)
    phone = Column(String, nullable = True)
    email = Column(String, nullable=False)
    latitude = Column(Numeric, nullable = False)
    longitude = Column(Numeric, nullable = False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user_tracking_pages = relationship("UserTrackingPages", back_populates="userprofile")
    subscription = relationship("Subscription", back_populates="user") 
    invoice = relationship("Invoice", back_populates="user") 
    usernotification = relationship("UserNotification", back_populates="userprofile")
    
    # listings = relationship("Listing", back_populates="user_profile")

class AppMinimumVersion(Base):
    __tablename__ = 'app_minimum_version'
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    version_number = Column(String, nullable=False)
    description = Column(String, nullable=True)
    android_url = Column(String, nullable=True)

class ErrorTable(Base):
    __tablename__ = 'error_table'

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    page = Column(String, nullable=True)      
    message = Column(String, nullable=True)     
    user_id = Column(UUID(as_uuid=True), nullable=True)  
    error_long = Column(String, nullable=True) 


class UserTrackingPages(Base):
    __tablename__ = 'user_tracking_pages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profile.user_id'),nullable=False)
    pages = Column(String, nullable=True)
    
    userprofile = relationship("UserProfile", back_populates="user_tracking_pages")

class TermsAndCondition(Base):
    __tablename__ = 'terms_and_conditions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    description = Column(String, nullable=False)

class SubscriptionDetails(Base):
    __tablename__ = 'subscription_details'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    qr_image = Column(String, nullable=False)
    
class UserProfileUpdate(BaseModel):
    first_name: str 
    last_name: str | None = None
    age: int | None = None
    image_url: str | None = None

    fcm_token: str | None = None


class Plan(Base):
    __tablename__ = 'plan'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    billing_cycle = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    subscription = relationship("Subscription", back_populates="plan")

class Subscription(Base):
    __tablename__ = 'subscription'
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profile.user_id'),nullable=False)
    plan_id = Column(Integer, ForeignKey('plan.id'),nullable=False)
    start_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False)
    trial_end_date = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    user = relationship("UserProfile", back_populates="subscription")
    plan = relationship("Plan", back_populates="subscription")
    # invoice = relationship("Invoice", back_populates="subscription")

class Invoice(Base):
    __tablename__ = 'invoice'

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profile.user_id'),nullable=False)
    plan_name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    invoice_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    paid = Column(Boolean, default=False, nullable=True)

    user = relationship("UserProfile", back_populates="invoice")
    # subscription = relationship("Subscription", back_populates="invoice")

class UserNotification(Base):
    __tablename__ = 'user_notification'
    id = Column(Integer, primary_key = True, autoincrement=True)
    type = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    schedule_datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_already_viewed = Column(Boolean, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profile.user_id'), nullable=False)
    title = Column(String, nullable=True)

    userprofile = relationship('UserProfile', back_populates='usernotification')

class UserNotificationUpdate(BaseModel):
    is_already_viewed: bool | None = None

class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # user_id = Column(UUID(as_uuid=True), ForeignKey("user_profile.user_id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    price = Column(Integer, nullable=False)
    status = Column(String(50), server_default="active", nullable=True)
    views = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    contact_name = Column(String(100), nullable=False)
    contact_number = Column(Integer, nullable=False)
    location = Column(String(255), nullable=False)
    latitude = Column(Numeric, nullable = False)
    longitude = Column(Numeric, nullable = False)
        
    # user_profile = relationship("UserProfile", back_populates="listings")
    spaces = relationship("ListingSpace", back_populates="listing")
    images = relationship("Image", back_populates="listing")

class ListingUpdate(BaseModel):
    views: int | None = None

class ListingSpace(Base):
    __tablename__ = "listing_space"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    space_type = Column(String(50), nullable=False)
    bedroom = Column(Integer, nullable=False)
    bathroom = Column(Integer, nullable=True)
    kitchen = Column(Integer, nullable=True)
    square_feet = Column(Integer, nullable=False)
    living_room = Column(Integer, nullable=True)
    details = Column(String, nullable=True)
    listing = relationship("Listing", back_populates="spaces")# Relationship back to Listing

class Image(Base):
    __tablename__ = "image"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String, nullable=True)

    listing = relationship("Listing", back_populates="images") # Relationship back to Listing

class Country(Base):
    __tablename__ = "country"

    id = Column(Integer, primary_key=True, autoincrement=True)
    country_name = Column(String(100), nullable=False)
    country_code = Column(String, nullable=False)
    country_currency = Column(String, nullable=False)
    country_phone_code = Column(String(10), nullable=False)
    currency_symbol = Column(String, nullable=True)

# Nepal Community Web App User Tracking Models
class UserVisitTracking(Base):
    __tablename__ = "user_visit_tracking"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid_ip = Column(String, unique=True, nullable=False)
    ip = Column(String, nullable=True)
    state = Column(String, nullable=True)
    city = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    logged_counts = Column(Integer, nullable=False)

# Nepal Community Web App familycount Model
class FamilyCounts(Base):
    __tablename__ = "family_counts"
    
    id = Column(Integer, autoincrement=True)
    city = Column(String, primary_key=True)
    state = Column(String, primary_key=True)
    family_count = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    
class ViewsTracking(Base):
    __tablename__ = "views_tracking"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listings_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profile.user_id'),nullable=False)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Favorites(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_profile.user_id'),nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)