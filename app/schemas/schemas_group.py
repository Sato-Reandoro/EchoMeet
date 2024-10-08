# schemas/group.py
from pydantic import BaseModel
from typing import List

class GroupEmailBase(BaseModel):
    email: str

class GroupEmailCreate(GroupEmailBase):
    pass

class GroupUpdate(BaseModel):
    name: str

class GroupBase(BaseModel):
    name: str

class GroupCreate(GroupBase):
    emails: List[GroupEmailCreate]

class Group(GroupBase):
    id: int
    emails: List[GroupEmailBase]

    class Config:
        from_attributes = True

class GroupEmailDelete(BaseModel):
    group_id: int
    email: str

class GroupEmailSearch(BaseModel):
    group_id: int
    email: str
    
class EmailCreate(BaseModel):
    email: str
    
class EmailResponse(BaseModel):
    email: str