# api/crud/group.py
from sqlalchemy.orm import Session
from app.models.group import Group, GroupEmail
from app.schemas.group import GroupCreate

def create_group(db: Session, group: GroupCreate):
    db_group = Group(name=group.name)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    
    for email in group.emails:
        db_group_email = GroupEmail(email=email.email, group_id=db_group.id)
        db.add(db_group_email)
    
    db.commit()
    return db_group

def get_groups(db: Session):
    return db.query(Group).all()

def get_group_by_id(db: Session, group_id: int):
    return db.query(Group).filter(Group.id == group_id).first()

def delete_group(db: Session, group_id: int):
    group = db.query(Group).filter(Group.id == group_id).first()
    db.delete(group)
    db.commit()
