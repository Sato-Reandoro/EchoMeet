# models/group.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Group(Base):
    __tablename__ = 'groups'
    
    id = Column(Integer, primary_key=True, index=True)  # ID automático
    name = Column(String, nullable=False, unique=True)
    emails = relationship("GroupEmail", back_populates="group")
    summaries = relationship("Summary", back_populates="group")
class GroupEmail(Base):
    __tablename__ = 'group_emails'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)  # Removido unique=True para permitir o mesmo email em grupos diferentes
    group_id = Column(Integer, ForeignKey('groups.id'))
    group = relationship("Group", back_populates="emails")
