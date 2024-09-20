# schemas/group.py
from pydantic import BaseModel
from typing import List

class GroupEmailBase(BaseModel):
    email: str

class GroupEmailCreate(GroupEmailBase):
    pass

class GroupBase(BaseModel):
    name: str

class GroupCreate(GroupBase):
    emails: List[GroupEmailCreate]

class Group(GroupBase):
    id: int
    emails: List[GroupEmailBase]

    class Config:
        from_attributes = True
