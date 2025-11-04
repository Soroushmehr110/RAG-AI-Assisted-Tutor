# backend/app/models.py
from sqlalchemy import Column, Integer, String, Boolean
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    grade_level = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

class AllowedEmail(Base):
    __tablename__ = "allowed_emails"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    note = Column(String, nullable=True)
