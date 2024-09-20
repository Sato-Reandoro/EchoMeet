# models/user.py
from sqlalchemy import Column, Integer, String, Boolean
from app.database.connection import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    is_admin = Column(Boolean, default=False)  # Define se o usuário é administrador
