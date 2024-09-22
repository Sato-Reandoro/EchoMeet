from datetime import timedelta
from typing import List
from fastapi import Depends, FastAPI, HTTPException, Path, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.crud import crud_user
from app.api.summary.dashboards import generate_dashboard_by_type, generate_dashboards_for_metrics, get_dashboard_options 
from app.api.summary.summary import salvar_resumo_no_banco
from app.database.connection import SessionLocal, get_db, init_db
from app.models.summary import Summary
from app.schemas import schemas_user
from app.schemas.summary import SummaryCreate
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal, init_db
from app.api.crud.group import create_group, get_groups, delete_group
from app.schemas.group import GroupCreate
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
def create_user(user_in: schemas_user.UserCreate, db: Session = Depends(get_db)):
    return crud_user.create_user(db, user_in)

@app.post("/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="nome de usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_type = user.user_type  # Ajuste conforme necessário para obter o tipo de usuário
    user_id = user.id  # Supondo que o ID do usuário está armazenado no atributo 'id'
    
    acesso_token = auth.create_access_token(
        data={"sub": user.email, "user_type": user_type}, expires_delta=timedelta(minutes=15)
    )
    
    return {"access_token": acesso_token, "user_type": user_type, "user_id": user_id}


@app.post("/summaries/")
def criar_resumo(
    summary: SummaryCreate, 
    db: Session = Depends(get_db)
):
    try:
        # Dividir o parâmetro 'nome' em nome_grupo e nome_audio
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