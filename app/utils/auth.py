import datetime
import os
from typing import Optional
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status

from app.database.connection import get_db
from app.models import models_user

# Carregar variáveis do .env
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES= 90

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(passowrd):
    return pwd_context.hash(passowrd)

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models_user.User).filter(models_user.User.email == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire + datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm= ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="credenciais não são válidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="suas credenciais não são validas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)  # Use decode_token aqui
        user = db.query(models_user.User).filter(models_user.User.email == payload.get("sub")).first()
        if user is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    
    return user


def admin_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
):
    # Reutilizar a função para obter o usuário atual
    current_user = get_current_user(token, db)
    
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não tem privilégios de administrador.",
        )
    
    return current_user


def get_current_user_id(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Suas credenciais não são válidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)  # Use decode_token aqui
        user = db.query(models_user.User).filter(models_user.User.email == payload.get("sub")).first()
        if user is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    
    return user.id