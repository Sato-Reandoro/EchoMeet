from datetime import timedelta
from typing import List
from fastapi import Depends, FastAPI, File, Form, HTTPException, Path, Query, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.crud import crud_user
from app.api.summary.dashboards import generate_dashboard_by_type, generate_dashboards_for_metrics, get_dashboard_options 
from app.api.summary.summary import salvar_resumo_no_banco
from app.api.transcription.transcription import remover_arquivo_temporario, salvar_arquivo_temporario, transcrever_audio
from app.database.connection import SessionLocal, get_db, init_db
from app.models import models_user
from app.models import models_group
from app.models.models_group import GroupEmail
from app.schemas import schemas_user
from app.schemas.schemas_user import EmailCheck
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal, init_db
from app.api.crud.group import create_group, get_all_groups, get_group_by_id, get_group_by_name, get_groups_by_user_id, update_group_name
from app.schemas.schemas_group import EmailCreate, EmailResponse, GroupCreate, GroupEmailDelete, Group, GroupEmailSearch, GroupUpdate
from app.schemas.summary import SummaryData
from app.utils import auth


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
    
    
@app.post("/users", response_model=schemas_user.User)
def create_user(user_in: schemas_user.UserCreate, db: Session = Depends(get_db), current_user: models_user.User = Depends(auth.admin_user)):
    return crud_user.create_user(db, user_in)

@app.post("/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="nome de usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_type = user.user_type
    user_id = user.id
    
    access_token = auth.create_access_token(
        data={"sub": user.email, "user_type": user_type},
        expires_delta=timedelta(minutes=15)
    )
    
    return {"access_token": access_token, "user_type": user_type, "user_id": user_id}

@app.post("/summaries/")
async def criar_resumo(
    summary_data: SummaryData,
    db: Session = Depends(get_db),
    user_id: int = Depends(auth.get_current_user_id)  # Obtém o user_id
):
    # Extrai os valores do nome
    try:
        nome_grupo, nome_audio = summary_data.nome.split(" ", 1)
        meeting_name = nome_audio  # Define meeting_name a partir de nome_audio
    except ValueError:
        raise HTTPException(status_code=400, detail="O nome deve conter pelo menos um espaço.")

    # Chama a função para salvar o resumo no banco
    resultado = salvar_resumo_no_banco(db, summary_data.nome, user_id, meeting_name)

    # Verifica se o resultado é um dicionário e se contém um erro
    if isinstance(resultado, dict) and "erro" in resultado:
        raise HTTPException(status_code=404, detail=resultado["erro"])

    return {"message": "Resumo salvo com sucesso!", "summary": resultado}



@app.get("/dashboard-options/{summary_id}")
def get_dashboard_options_api(summary_id: int, db: Session = Depends(get_db), current_user: models_user.User = Depends(auth.get_current_user)):
    try:
        options = get_dashboard_options(db, summary_id)
        return options
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint para gerar um gráfico com base no tipo de valor (numérico ou percentual)
@app.get("/generate-dashboard/{summary_id}/{value_type}")
def generate_dashboard_api(summary_id: int, value_type: str, db: Session = Depends(get_db), current_user: models_user.User = Depends(auth.get_current_user)):
    try:
        generate_dashboard_by_type(db, summary_id, value_type)
        return {"message": f"Gráfico de tipo '{value_type}' gerado com sucesso."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Novo endpoint para gerar gráficos a partir de várias métricas
@app.get("/generate-dashboard-by-metrics/{summary_id}")
def generate_dashboard_by_metrics_api(summary_id: int, metrics: list[str] = Query(...), db: Session = Depends(get_db), current_user: models_user.User = Depends(auth.get_current_user)):
    try:
        generate_dashboards_for_metrics(db, summary_id, metrics)
        return {"message": "Gráficos gerados com sucesso para as métricas fornecidas."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/groups/", response_model=Group)
def create_new_group(group: GroupCreate, db: Session = Depends(get_db)):
    return create_group(db=db, group=group)

@app.get("/groups/", response_model=List[Group])
def read_groups(db: Session = Depends(get_db)):
    return get_all_groups(db=db)

@app.get("/groups/{group_name}", response_model=Group)
def read_group_by_name(group_name: str, db: Session = Depends(get_db)):
    return get_group_by_name(db=db, group_name=group_name)

@app.get("/grupos/user", response_model=List[Group])
def get_user_groups(db: Session = Depends(get_db), user_id: int = Depends(auth.get_current_user_id)):
    groups = get_groups_by_user_id(db, user_id)

    if not groups:
        raise HTTPException(status_code=404, detail="Nenhum grupo encontrado para o usuário")

    return groups

@app.get("/grupos/{group_id}/emails", response_model=List[EmailResponse])
async def get_emails_by_group(group_id: int, db: Session = Depends(get_db)):
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")

    emails = db.query(GroupEmail).filter(GroupEmail.group_id == group_id).all()
    return emails


@app.put("/grupos-update-name/{group_id}")
async def update_group_name_endpoint(group_id: int, group_update: GroupUpdate, db: Session = Depends(get_db)):
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")

    # Verifica se o novo nome já está em uso
    existing_group = db.query(models_group.Group).filter(models_group.Group.name == group_update.name).first()
    if existing_group and existing_group.id != group_id:  # Certifique-se de que não é o mesmo grupo
        raise HTTPException(status_code=400, detail="O nome do grupo já está em uso")

    # Atualiza o nome do grupo
    update_group_name(db, group_id, group_update.name)
    return {"detail": "Nome do grupo atualizado com sucesso"}

@app.post("/grupos/{group_id}/emails")
async def add_email_to_group(group_id: int, email: EmailCreate, db: Session = Depends(get_db)):
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")

    # Verifica se o email já existe no sistema
    existing_user = db.query(models_user.User).filter(models_user.User.email == email.email).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="Email não cadastrado no sistema")

    # Verifica se o email já existe no grupo
    existing_email = db.query(GroupEmail).filter(GroupEmail.email == email.email, GroupEmail.group_id == group_id).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email já existe no grupo")

    new_email = GroupEmail(email=email.email, group_id=group_id)
    db.add(new_email)
    db.commit()
    return {"detail": "Email adicionado ao grupo com sucesso"}

@app.delete("/grupos/{group_id}/emails/{email_id}")
async def remove_email_from_group(group_id: int, email_id: int, db: Session = Depends(get_db)):
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")

    email_to_remove = db.query(GroupEmail).filter(GroupEmail.id == email_id, GroupEmail.group_id == group_id).first()
    if not email_to_remove:
        raise HTTPException(status_code=404, detail="Email não encontrado no grupo")

    db.delete(email_to_remove)
    db.commit()
    return {"detail": "Email removido do grupo com sucesso"}

@app.delete("/grupos/{group_id}")
async def delete_group(group_id: int, db: Session = Depends(get_db)):
    # Verifica se o grupo existe
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    
    # Deleta o grupo do banco de dados
    db.delete(group)
    db.commit()
    
    return {"detail": "Grupo deletado com sucesso"}



# Rota para listar todos os usuários
@app.get("/users", response_model=List[schemas_user.User])
def read_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db), current_user: models_user.User = Depends(auth.admin_user)):
    return crud_user.get_all_users(db, skip=skip, limit=limit)
    
# Rota para obter um usuário pelo ID
@app.get("/users/{user_id}", response_model=schemas_user.User)
def read_user(
    user_id: int = Path(..., title="The ID of the user to retrieve"),
    db: Session = Depends(get_db),
    current_user: models_user.User = Depends(auth.admin_user)  # Adicionando a verificação de admin
):
    user = crud_user.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Rota para atualizar as informações de um usuário pelo ID
@app.put("/users/{user_id}", response_model=schemas_user.User)
def update_user(
    user_id: int,
    user_in: schemas_user.UserUptade,
    db: Session = Depends(get_db),
    current_user: models_user.User = Depends(auth.admin_user)  # Adicionando a verificação de admin
):
    updated_user = crud_user.update_user(db, user_id, user_in)
    return updated_user

# Rota para excluir um usuário pelo ID
@app.delete("/users/{user_id}", response_model=schemas_user.User)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models_user.User = Depends(auth.admin_user)  # Adicionando a verificação de admin
):
    deleted_user = crud_user.delete_user(db, user_id)
    return deleted_user

@app.post("/transcrever-audio/")
async def transcrever_audio_endpoint(nome_grupo: str = Form(...), file: UploadFile = File(...), current_user: models_user.User = Depends(auth.get_current_user)):
    """Endpoint para transcrever áudio enviado e retornar a transcrição."""
    # Salvar o arquivo de áudio temporariamente
    file_location = salvar_arquivo_temporario(file)

    try:
        # Chamar a função de transcrição
        transcricao = transcrever_audio(file_location, nome_grupo, file.filename)
        return JSONResponse(content={"transcricao": transcricao})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Remover o arquivo temporário
        remover_arquivo_temporario(file_location)