import os
from fastapi import FastAPI
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Carregar as variáveis do .env
load_dotenv(dotenv_path="C:/Users/lucas/Documents/GitHub/EchoMeet/app/.env")
    
# Pegar a URL do banco de dados do .env
print("DATABASE_URL: ", os.getenv("DATABASE_URL"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("A variável DATABASE_URL não está definida no .env")

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
    import app.models.group
    import app.models.user
    Base.metadata.create_all(bind=engine)  # Cria todas as tabelas no banco de dados
