import os
from pathlib import Path
from fastapi import UploadFile, HTTPException

# Diretório onde os arquivos de áudio serão salvos
UPLOAD_DIRECTORY = "D:/programação/github/EchoMeet/app/api/transcription/audios"

# Criar o diretório caso ele não exista
Path(UPLOAD_DIRECTORY).mkdir(parents=True, exist_ok=True)

def verificar_audio(file: UploadFile):
    """Verifica se o arquivo é de um tipo de áudio suportado."""
    if file.content_type not in ["audio/mpeg", "audio/wav"]:
        raise HTTPException(status_code=400, detail="Invalid audio format. Only mp3 and wav are accepted.")

def definir_caminho_arquivo(file: UploadFile):
    """Define o caminho completo para o arquivo de áudio."""
    return os.path.join(UPLOAD_DIRECTORY, file.filename)

def salvar_no_diretorio(file: UploadFile, file_location: str):
    """Salva o arquivo de áudio no diretório especificado."""
    with open(file_location, "wb") as f:
        f.write(file.file.read())
