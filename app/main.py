from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal, init_db
from app.api.crud.group import create_group, get_groups, delete_group
from app.schemas.group import GroupCreate


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

@app.post("/groups/")
def create_new_group(group: GroupCreate, db: Session = Depends(get_db)):
    return create_group(db=db, group=group)

@app.get("/groups/")
def read_groups(db: Session = Depends(get_db)):
    return get_groups(db)

@app.delete("/groups/{group_id}")
def delete_existing_group(group_id: int, db: Session = Depends(get_db)):
    delete_group(db=db, group_id=group_id)
    return {"msg": "Grupo Deletado!"}
