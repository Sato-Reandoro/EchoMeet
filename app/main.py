import json
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.summary.dashboards import generate_dashboard_by_type, generate_dashboards_for_metrics, get_dashboard_options 
from app.api.summary.summary import salvar_resumo_no_banco
from app.database.connection import SessionLocal, get_db, init_db
from app.models.summary import Summary
from app.schemas.summary import SummaryCreate
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
