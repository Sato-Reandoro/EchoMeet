from datetime import timedelta
import json
import os
import subprocess
from typing import List
from fastapi import Depends, FastAPI, File, Form, HTTPException, Path, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.crud import crud_user
from app.api.summary.dashboards import generate_dashboard_by_type, generate_dashboards_for_metrics, get_dashboard_options 
from app.api.summary.summary import  criar_resumo_model, gerar_resumo, identificar_dados, ler_conteudo_arquivo, remover_duplicatas, salvar_no_banco, salvar_resumo_no_banco
from app.api.transcription.transcription import TEMP_DIRECTORY, TRANSCRIPTION_DIRECTORY,  processar_audio, transcrever_audio
from app.database.connection import SessionLocal, get_db, init_db
from app.models import models_user
from app.models.summary import Summary
from app.schemas import schemas_user
from app.schemas.schemas_user import EmailCheck
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal, init_db
from app.api.crud.group import create_group, get_groups, delete_group, delete_email_from_group, get_emails_by_group, get_group_by_name, find_email_in_group
from app.schemas.group import GroupCreate, GroupEmailDelete, Group, GroupEmailSearch
from app.schemas.summary import SummaryData
from app.utils import auth
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

# Middleware para permitir uploads maiores
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    # Limitar o tamanho do corpo da requisição
    body = await request.body()
    if len(body) > 1000000000:  # Limite de 1GB
        return JSONResponse(status_code=400, content={"detail": "O arquivo de áudio ultrapassa o tamanho máximo permitido."})
    response = await call_next(request)
    return response


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

        
@app.post("/transcricao-resumo/{nome_grupo}")
async def transcricao_resumo(
    nome_grupo: str,
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(auth.get_current_user_id)
):
    # Chama a função processar_audio para transcrever o áudio
    resultado_transcricao = await processar_audio(request, nome_grupo, db, user_id)

    # Verifica se a transcrição foi bem-sucedida
    transcricao_file_path = resultado_transcricao.get("transcription")
    meeting_name = resultado_transcricao.get("meeting_name", "")

    if not transcricao_file_path:
        raise HTTPException(status_code=404, detail="Transcrição falhou.")

    # Lê o conteúdo do arquivo de transcrição
    conteudo_transcricao = ler_conteudo_arquivo(transcricao_file_path)
    if "Arquivo não encontrado" in conteudo_transcricao:
        raise HTTPException(status_code=404, detail=conteudo_transcricao)

    # Gera o resumo a partir da transcrição
    resumo_gerado = await gerar_resumo(conteudo_transcricao)

    # Identifica dados relevantes no texto da transcrição para o dashboard
    dados_dashboard = identificar_dados(conteudo_transcricao)
    dados_dashboard_sem_duplicatas = remover_duplicatas(dados_dashboard)
    dados_dashboard_json = json.dumps(dados_dashboard_sem_duplicatas)

    # Salva o resumo e dados no banco de dados com o nome do áudio como meeting_name
    novo_resumo = criar_resumo_model(user_id, meeting_name, resumo_gerado, dados_dashboard_json)
    resultado_salvamento = salvar_no_banco(novo_resumo, db)

    if not resultado_salvamento:
        raise HTTPException(status_code=500, detail="Falha ao salvar o resumo no banco.")

    # Remove o arquivo de transcrição após o processamento
    try:
        os.remove(transcricao_file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao remover o arquivo de transcrição: {str(e)}")

    return {
        "transcription": transcricao_file_path,
        "summary": resumo_gerado,
        "dashboard_data": dados_dashboard_json
    }
    
@app.get("/resumo/{summary_id}")
async def obter_resumo(summary_id: int, db: Session = Depends(get_db), user_id: int = Depends(auth.get_current_user_id)):
    # Busca o resumo específico no banco de dados pelo ID
    resumo = db.query(Summary).filter(Summary.summary_id == summary_id, Summary.user_id == user_id).first()

    if not resumo:
        raise HTTPException(status_code=404, detail="Resumo não encontrado.")

    # Retorna o meeting_name e o summary_text
    return {
        "meeting_name": resumo.meeting_name,
        "summary_text": resumo.summary_text
    }