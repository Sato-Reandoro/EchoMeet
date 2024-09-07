from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database.connection import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executa a inicialização do banco de dados na inicialização da aplicação
    init_db()
    yield
    # Aqui você pode adicionar qualquer código que deve ser executado no final

# Inicializa a aplicação FastAPI com o evento lifespan
app = FastAPI(lifespan=lifespan)