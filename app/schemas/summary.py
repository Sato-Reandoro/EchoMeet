from pydantic import BaseModel

class SummaryCreate(BaseModel):
    user_id: int
    meeting_name: str
    summary_text: str = ""  # Permitir que o campo seja opcional e ter um valor padrão
    nome: str  # Adicionado

class SummaryResponse(SummaryCreate):
    summary_id: int

    class Config:
        orm_mode = True
