# crud/crud_user.py
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.models import models_user
from app.models import models_group
from app.models.models_group import Group, GroupEmail
from app.models.models_user import User
from app.schemas.schemas_group import GroupCreate

def email_exists(db: Session, email: str) -> bool:
    return db.query(User).filter(User.email == email).first() is not None

def get_group_by_id(db: Session, group_id: int):
    return db.query(models_group.Group).filter(models_group.Group.id == group_id).first()

def create_group(db: Session, group: GroupCreate):
    # Verificar se o nome do grupo já existe
    existing_group = db.query(Group).filter(Group.name == group.name).first()
    if existing_group:
        raise HTTPException(status_code=400, detail="O nome do grupo já está em uso.")
    
    # Verificar se ao menos um dos emails existe no sistema de usuários
    valid_emails = []
    for email in group.emails:
        user = db.query(User).filter(User.email == email.email).first()
        if user:
            valid_emails.append(email)
    
    if not valid_emails:
        raise HTTPException(status_code=400, detail="Nenhum dos e-mails fornecidos é válido.")
    
    # Criar o grupo
    db_group = Group(name=group.name)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)

    # Adicionar apenas os emails válidos ao grupo
    for email in valid_emails:
        db_group_email = GroupEmail(email=email.email, group_id=db_group.id)
        db.add(db_group_email)

    db.commit()
    return db_group


def get_all_groups(db: Session):
    return db.query(Group).all()

def get_group_by_name(db: Session, group_name: str):
    group = db.query(Group).filter(Group.name == group_name).first()
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    return group

def get_user_groups_by_email(db: Session, email: str):
    return db.query(models_group.Group).join(models_group.GroupEmail).filter(models_group.GroupEmail.email == email).all()

# Função para listar os grupos do usuário autenticado
def get_groups_by_user_id(db: Session, user_id: int):
    # Pegar o email do usuário pelo ID
    user = db.query(models_user.User).filter(models_user.User.id == user_id).first()

    if user is None:
        return []

    # Buscar todos os grupos relacionados ao email do usuário
    return get_user_groups_by_email(db, user.email)

# Função para atualizar o nome do grupo
def update_group_name(db: Session, group_id: int, new_name: str):
    group = db.query(models_group.Group).filter(models_group.Group.id == group_id).first()
    if group:
        group.name = new_name
        db.commit()
        db.refresh(group)

def add_email_to_group(db: Session, group_id: int, email: str):
    group_email = models_group.GroupEmail(email=email, group_id=group_id)
    db.add(group_email)
    db.commit()

def remove_email_from_group(db: Session, group_id: int, email: str):
    group_email = db.query(models_group.GroupEmail).filter(models_group.GroupEmail.group_id == group_id, models_group.GroupEmail.email == email).first()
    if group_email:
        db.delete(group_email)
        db.commit()


def get_group_id(db: Session, nome_grupo: str):
    return db.query(Group).filter(Group.name == nome_grupo).first()


def id_name(nome_grupo: str, db: Session):
    grupo = db.query(Group).filter(Group.name == nome_grupo).first()
    return grupo.id if grupo else None