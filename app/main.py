from fastapi import Depends, FastAPI
from requests import Session
from app.api.summary.summary import salvar_resumo_no_banco
from app.database.connection import SessionLocal, get_db, init_db
from app.schemas.summary import SummaryCreate


app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    init_db()

