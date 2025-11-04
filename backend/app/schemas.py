# backend/app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    grade_level: Optional[str]

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    grade_level: Optional[str]
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class OCRResult(BaseModel):
    extracted_text: str
    analysis: dict
