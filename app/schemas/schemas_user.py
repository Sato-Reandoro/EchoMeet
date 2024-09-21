# schemas/user.py
from typing import Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel): 
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str
    user_type: str    

class UserUptade(UserBase):
    name: Optional[str] = None
    email: Optional[str] = None
    Password: Optional[str] = None
    
class User(UserBase):
    id: int
    user_type: str