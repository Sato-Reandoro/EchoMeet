from datetime import timedelta
import json
import os
from typing import List
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.crud import crud_user
from app.api.summary.dashboards import generate_dashboard_by_type, generate_dashboards_for_metrics, get_dashboard_options 
from app.api.summary.summary import gerar_resumo, identificar_dados, ler_conteudo_arquivo, remover_duplicatas, salvar_no_banco
from app.api.transcription.transcription import TEMP_DIRECTORY, TRANSCRIPTION_DIRECTORY,  processar_audio
from app.database.connection import SessionLocal, get_db, init_db
from app.models import models_user
from app.models.models_summary import Summary
from app.models import models_group
from app.models.models_group import GroupEmail
from app.schemas import schemas_user
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal, init_db
from app.api.crud.group import create_group, get_all_groups, get_group_by_id, get_group_by_name, get_groups_by_user_id, id_name, update_group_name
from app.schemas.schemas_group import EmailCreate, EmailResponse, GroupCreate, Group, GroupUpdate
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
async def add_cookie_settings(request: Request, call_next):
    response = await call_next(request)

    # Configura SameSite e Secure para todos os cookies na resposta
    response.set_cookie(
        key="example_cookie",
        value="cookie_value",
        samesite="None",  # Define o SameSite como None
        secure=True       # Define Secure como True
    )
    
    return response


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
    
    # Ajustando o tempo de expiração para 8 horas
    access_token = auth.create_access_token(
        data={"sub": user.email, "user_type": user_type},
        expires_delta=timedelta(hours=8)  # Agora será 8 horas
    )
    
    return {"access_token": access_token, "user_type": user_type, "user_id": user_id}



@app.get("/dashboard-options/{summary_id}")
def get_dashboard_options_api(summary_id: int, db: Session = Depends(get_db)):
    try:
        options = get_dashboard_options(db, summary_id)
        return options
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint para gerar gráfico por tipo de valor (numérico ou percentual)
@app.get("/generate-dashboard/{summary_id}/{value_type}")
def generate_dashboard_api(summary_id: int, value_type: str, db: Session = Depends(get_db)):
    try:
        html_content = generate_dashboard_by_type(db, summary_id, value_type)
        return HTMLResponse(content=html_content, media_type="text/html")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Endpoint para gerar gráficos para várias métricas
@app.get("/generate-dashboard-by-metrics/{summary_id}")
def generate_dashboard_by_metrics_api(summary_id: int, metrics: list[str] = Query(...), db: Session = Depends(get_db)):
    try:
        html_content = generate_dashboards_for_metrics(db, summary_id, metrics)
        return HTMLResponse(content=html_content, media_type="text/html")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/groups/", response_model=Group)
def create_new_group(group: GroupCreate, db: Session = Depends(get_db), current_user: models_user.User = Depends(auth.admin_user)):
    return create_group(db=db, group=group)

@app.get("/groupsonly/", response_model=List[Group])
def read_groups(db: Session = Depends(get_db)):
    return get_all_groups(db=db)

@app.get("/groups/{group_name}", response_model=Group)
def read_group_by_name(group_name: str, db: Session = Depends(get_db), current_user: models_user.User = Depends(auth.admin_user)):
    return get_group_by_name(db=db, group_name=group_name)

@app.get("/grupos/user", response_model=List[Group])
def get_user_groups(db: Session = Depends(get_db), user_id: int = Depends(auth.get_current_user_id)):
    groups = get_groups_by_user_id(db, user_id)

    if not groups:
        raise HTTPException(status_code=404, detail="Nenhum grupo encontrado para o usuário")

    return groups

@app.get("/grupos/{group_id}/emails", response_model=List[EmailResponse])
async def get_emails_by_group(group_id: int, db: Session = Depends(get_db), current_user: models_user.User = Depends(auth.admin_user)):
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
async def add_email_to_group(group_id: int, email: EmailCreate, db: Session = Depends(get_db), current_user: models_user.User = Depends(auth.admin_user)):
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
async def remove_email_from_group(group_id: int, email_id: int, db: Session = Depends(get_db), current_user: models_user.User = Depends(auth.admin_user)):
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")

    email_to_remove = db.query(GroupEmail).filter(GroupEmail.id == email_id, GroupEmail.group_id == group_id).first()
    if not email_to_remove:
        raise HTTPException(status_code=404, detail="Email não encontrado no grupo")

    db.delete(email_to_remove)
    db.commit()
    return {"detail": "Email removido do grupo com sucesso"}

@app.delete("/grupos/{id_group}")
async def delete_group(id_group: int, db: Session = Depends(get_db), current_user: models_user.User = Depends(auth.admin_user)):
    # Verifica se o grupo existe
    group = get_group_by_id(db, id_group)
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    
    # Busca os summaries associados ao grupo, se houver
    summaries = db.query(Summary).filter(Summary.id_group == id_group).all()
    if summaries:
        for summary in summaries:
            db.delete(summary)
    
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

        
@app.post("/transcricao-resumo/{nome_grupo}")
async def transcricao_resumo(
    nome_grupo: str,
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Depends(auth.get_current_user_id)
):
    # Busca o ID do grupo com base no nome
    id_grupo = id_name(nome_grupo, db)

    # Verifica se o grupo existe
    if id_grupo is None:
        raise HTTPException(status_code=404, detail="Grupo não encontrado.")

    # Chama a função processar_audio para transcrever o áudio
    resultado_transcricao = await processar_audio(request, nome_grupo, db, user_id)

    # Verifica se a transcrição foi bem-sucedida
    transcricao_file_path = resultado_transcricao.get("transcription")
    meeting_name = f"{nome_grupo}_{resultado_transcricao.get('meeting_name', '')}"

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

    # Salva o resumo e dados no banco de dados
    novo_resumo = Summary(
        user_id=user_id,
        meeting_name=meeting_name,
        summary_text=resumo_gerado,
        dashboard_data=dados_dashboard_json,
        id_group=id_grupo
    )

    # Salva o resumo no banco e verifica o resultado
    resultado_salvamento = salvar_no_banco(novo_resumo, db)
    if not resultado_salvamento:
        raise HTTPException(status_code=500, detail="Falha ao salvar o resumo no banco.")

    # Remove o arquivo de transcrição após o processamento
    try:
        os.remove(transcricao_file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao remover o arquivo de transcrição: {str(e)}")

    return {
        "group_id": id_grupo,
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

@app.get("/grupos/{group_id}/reunioes")
async def listar_reunioes_por_grupo(group_id: int, db: Session = Depends(get_db), current_user: models_user.User = Depends(auth.get_current_user)):
    # Verifica se o grupo existe
    grupo = get_group_by_id(db, group_id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")

    # Busca todas as reuniões associadas a este grupo
    reunioes = db.query(Summary).filter(Summary.id_group == group_id).all()

    if not reunioes:
        print(f"Debug: Nenhuma reunião encontrada para o group_id {group_id}.")
        return {"detail": "Nenhuma reunião encontrada para este grupo."}

    return reunioes


