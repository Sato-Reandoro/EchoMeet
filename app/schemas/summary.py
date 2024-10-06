from fastapi import UploadFile
from pydantic import BaseModel, Field


class SummaryData(BaseModel):
    nome: str  # Recebe "nome_grupo nome_audio"
    

class TranscricaoResumoRequest(BaseModel):
    nome_grupo: str
    audio_file: UploadFile 