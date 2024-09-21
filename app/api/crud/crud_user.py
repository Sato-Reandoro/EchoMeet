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
