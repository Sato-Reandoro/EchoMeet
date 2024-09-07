import os
from fastapi import FastAPI
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Carregar as variáveis do .env
load_dotenv()

# Pegar a URL do banco de dados do .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Configuração do SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import app.models  
    Base.metadata.create_all(bind=engine) 