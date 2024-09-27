from datetime import timedelta
from typing import List
from fastapi import Depends, FastAPI, File, HTTPException, Path, Query, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.crud import crud_user
from app.api.summary.dashboards import generate_dashboard_by_type, generate_dashboards_for_metrics, get_dashboard_options 
from app.api.summary.summary import salvar_resumo_no_banco
from app.api.transcription.audio import definir_caminho_arquivo, salvar_no_diretorio, verificar_audio
from app.api.transcription.transcription import remover_arquivo_temporario, salvar_arquivo_temporario, transcrever_audio
from app.database.connection import SessionLocal, get_db, init_db
from app.models import models_user
from app.models.summary import Summary
from app.schemas import schemas_user
from app.schemas.summary import SummaryCreate
from app.schemas.schemas_user import EmailCheck
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal, init_db
from app.api.crud.group import create_group, get_groups, delete_group, delete_email_from_group, get_emails_by_group, get_group_by_name, find_email_in_group
from app.schemas.group import GroupCreate, GroupEmailDelete, Group, GroupEmailSearch
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
def criar_resumo(
    summary: SummaryCreate, 
    db: Session = Depends(get_db)
):
    try:
        nome_grupo, nome_audio = summary.nome.split(maxsplit=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="O campo 'nome' deve conter nome do grupo e nome do áudio separados por espaço.")
    
    return salvar_resumo_no_banco(summary, db, nome_grupo, nome_audio)



@app.get("/dashboard-options/{summary_id}")
def get_dashboard_options_api(summary_id: int, db: Session = Depends(get_db)):
    try:
        options = get_dashboard_options(db, summary_id)
        return options
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint para gerar um gráfico com base no tipo de valor (numérico ou percentual)
@app.get("/generate-dashboard/{summary_id}/{value_type}")
def generate_dashboard_api(summary_id: int, value_type: str, db: Session = Depends(get_db)):
    try:
        generate_dashboard_by_type(db, summary_id, value_type)
        return {"message": f"Gráfico de tipo '{value_type}' gerado com sucesso."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Novo endpoint para gerar gráficos a partir de várias métricas
@app.get("/generate-dashboard-by-metrics/{summary_id}")
def generate_dashboard_by_metrics_api(summary_id: int, metrics: list[str] = Query(...), db: Session = Depends(get_db)):
    try:
        generate_dashboards_for_metrics(db, summary_id, metrics)
        return {"message": "Gráficos gerados com sucesso para as métricas fornecidas."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# rota verificar se o email consta no sistema
@app.post("/check-email/")
def check_email(email_data: EmailCheck, db: Session = Depends(get_db)):
    email = email_data.email
    user = crud_user.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="E-mail não encontrado")
    return {"message": "E-mail válido e existente no sistema."}

# Rota para procurar um email específico dentro de um grupo via corpo da requisição
@app.post("/groups/search-email/")
def find_email_in_group_api(email_search: GroupEmailSearch, db: Session = Depends(get_db)):
    return find_email_in_group(db, email_search.group_id, email_search.email)


#Rota lista de emails de um grupo
@app.get("/groups/{group_id}/emails", response_model=dict)
def get_group_emails(group_id: int, db: Session = Depends(get_db)):
    return get_emails_by_group(db, group_id)

#Rota que remove email de um grupo
@app.delete("/groups/delete-email/")
def remove_email_from_group(data: GroupEmailDelete, db: Session = Depends(get_db)):
    return delete_email_from_group(db=db, group_id=data.group_id, email=data.email)

#Rota de criação de grupo
@app.post("/groups_create/")
def create_new_group(group: GroupCreate, db: Session = Depends(get_db)):
    return create_group(db=db, group=group)

# Rota para obter um grupo pelo nome
@app.get("/groups/name/{group_name}", response_model=Group)
def read_group_by_name(group_name: str, db: Session = Depends(get_db)):
    return get_group_by_name(db=db, group_name=group_name)

#Rota para obter todos os grupos
@app.get("/groups/", response_model=List[Group])
def read_groups(db: Session = Depends(get_db)):
    return get_groups(db)

#Rota para deletar um grupo pelo id 
@app.delete("/groups/{group_id}")
def delete_existing_group(group_id: int, db: Session = Depends(get_db)):
    delete_group(db=db, group_id=group_id)
    return {"msg": "Grupo Deletado!"}


# Rota para listar todos os usuários
@app.get("/users", response_model=List[schemas_user.User])
def read_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud_user.get_all_users(db, skip=skip, limit=limit)
    
# Rota para obter um usuário pelo ID
@app.get("/users/{user_id}", response_model=schemas_user.User)
def read_user(
    user_id: int = Path(..., title="The ID of the user to retrieve"),
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
):
    updated_user = crud_user.update_user(db, user_id, user_in)
    return updated_user

# Rota para excluir um usuário pelo ID
@app.delete("/users/{user_id}", response_model=schemas_user.User)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    deleted_user = crud_user.delete_user(db, user_id)
    return deleted_user

@app.post("/transcrever-audio/")
async def transcrever_audio_endpoint(nome_grupo: str, file: UploadFile = File(...)):
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