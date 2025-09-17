# from sqlalchemy import TIMESTAMP, Column, Integer, String, ForeignKey, text
# from sqlalchemy.dialects.postgresql import UUID
# import uuid
# from core.database import Base


# class UserProfile(Base):
#     __tablename__ = 'user_profile'
#     user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     first_name = Column(String(50), nullable=False)
#     last_name = Column(String(50), nullable=False)
#     # CHECK constraint is not directly set here, but can be via SQL or validation
#     age = Column(Integer, nullable=False)
#     college = Column(String(100))
#     field_id = Column(Integer, ForeignKey('field_of_study.id'))
#     create_date = Column(TIMESTAMP(timezone=True),
#                          server_default=text('NOW()'))
