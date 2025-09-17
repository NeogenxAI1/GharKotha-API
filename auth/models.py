from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from core.database import Base
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship


class UserLog(Base):
    __tablename__ = 'user_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    event = Column(String, nullable=False)  # e.g., "login", "signup", "delete"
    timestamp = Column(DateTime, default=datetime.now)
    details = Column(String, nullable=True)  # optional context
    ip_address = Column(String, nullable=True)  # ➕ New column
    # user = relationship("User", back_populates="logs", foreign_keys=[user_id])
