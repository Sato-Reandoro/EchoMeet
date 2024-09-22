# api/crud/user.py
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import models_user
from app.schemas import schemas_user
from app.utils.auth import get_password_hash

def get_user_by_email(db: Session, email: str):
    return db.query(models_user.User).filter(models_user.User.email == email).first()

def verificar_email(db: Session, email: str):
    db_user = get_user_by_email(db, email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já está em uso"
        )

def create_user(db: Session, user: schemas_user.UserCreate):
    verificar_email(db, user.email)

    hashed_password = get_password_hash(user.password)
    db_user = models_user.User(
        email=user.email,
        name=user.name,
        hashed_password=hashed_password,
        user_type=user.user_type
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_id(db: Session, user_id: int):
    return db.query(models_user.User).filter(models_user.User.id == user_id).first()

def get_all_users(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models_user.User).offset(skip).limit(limit).all()

def update_user(db: Session, user_id: int, user_in: schemas_user.UserUptade):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = user_in.model_dump(exclude_unset=True)
    for key, value in user_data.items():
        setattr(user, key, value)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user_id: int):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return user