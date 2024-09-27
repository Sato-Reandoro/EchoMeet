from pydantic import BaseModel


class SummaryData(BaseModel):
    nome: str  # Recebe "nome_grupo nome_audio"