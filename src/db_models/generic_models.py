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
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    qrimage = Column(String, nullable=False)
    
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
