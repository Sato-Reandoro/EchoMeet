# schemas/user.py
from pydantic import BaseModel

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    is_admin: bool

    class Config:
        from_attributes = True
