# api/crud/group.py
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.group import Group, GroupEmail
from app.schemas.group import GroupCreate

# função que cria grupo e os emails devem ser listados
def create_group(db: Session, group: GroupCreate):
    db_group = Group(name=group.name)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    
    for email in group.emails:
        # Verifica se o email ja foi cadastrado no grupo e retorna o emaail
        existing_email = db.query(GroupEmail).filter(GroupEmail.email == email.email, GroupEmail.group_id == db_group.id).first()
        if existing_email:
            raise HTTPException(status_code=400, detail=f"O e-mail {email.email} já está registrado no grupo.")
        db_group_email = GroupEmail(email=email.email, group_id=db_group.id)
        db.add(db_group_email)
    
    db.commit()
    return db_group


def get_groups(db: Session):
    return db.query(Group).all()


def get_group_by_id(db: Session, group_id: int):
    return db.query(Group).filter(Group.id == group_id).first()

# função que deleta um grupo
def delete_group(db: Session, group_id: int):
    group = db.query(Group).filter(Group.id == group_id).first()
    db.delete(group)
    db.commit()

# função que deleta um email expecifico de um grupo
def delete_email_from_group(db: Session, group_id: int, email: str):
    group_email = db.query(GroupEmail).filter(GroupEmail.group_id == group_id, GroupEmail.email == email).first()
    
    if not group_email:
        raise HTTPException(status_code=404, detail="E-mail não encontrado no grupo.")
    
    db.delete(group_email)
    db.commit()
    return {"msg": "E-mail removido do grupo com sucesso."}

# função que puxa emails de um grupo
def get_emails_by_group(db: Session, group_id: int):
    group = db.query(Group).filter_by(id=group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    emails = [email.email for email in group.emails]
    
    return {"group_id": group_id, "emails": emails}

# função que puxa um grupo pelo nome
def get_group_by_name(db: Session, group_name: str):
    group = db.query(Group).filter(Group.name == group_name).first()
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    return group


# função que encontra email especifico cadastrado em um grupo  
def find_email_in_group(db: Session, group_id: int, email: str):
    # Verificar se o grupo existe
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")

    # Procurar o email no grupo
    group_email = db.query(GroupEmail).filter(GroupEmail.group_id == group_id, GroupEmail.email == email).first()
    if not group_email:
        raise HTTPException(status_code=404, detail="E-mail não cadastrado no sistema")
    
    return {"group_id": group_id, "email": group_email.email, "message": "E-mail encontrado no grupo"}