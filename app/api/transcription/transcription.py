import os
import re
from google.cloud import speech
from dotenv import load_dotenv
from pathlib import Path
from pydub.utils import mediainfo
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

# Carregar variáveis de ambiente
load_dotenv()

app = FastAPI()

# Diretório onde as transcrições serão salvas
TRANSCRIPTION_DIRECTORY = "D:/programação/github/EchoMeet/app/api/transcription/pasta_de_transcrições"
Path(TRANSCRIPTION_DIRECTORY).mkdir(parents=True, exist_ok=True)

# Diretório temporário para salvar arquivos de áudio
TEMP_DIRECTORY = "D:/programação/github/EchoMeet/app/api/transcription/audios/temp"
Path(TEMP_DIRECTORY).mkdir(parents=True, exist_ok=True)


def salvar_arquivo_temporario(audio: UploadFile) -> str:
    """Salva o arquivo de áudio temporariamente para processamento."""
    file_location = os.path.join(TEMP_DIRECTORY, audio.filename)
    with open(file_location, "wb") as buffer:
        buffer.write(audio.file.read())
    return file_location


def obter_taxa_amostragem(file_path: str) -> int:
    """Obtém a taxa de amostragem do arquivo de áudio."""
    info = mediainfo(file_path)
    return int(info['sample_rate'])


def limpar_nome_arquivo(nome: str) -> str:
    """Remove caracteres inválidos do nome do arquivo."""
    nome = re.sub(r'[<>:"/\\|?*]', '', nome)  # Remove caracteres inválidos
    return nome.replace('\n', ' ').replace('\r', ' ')  # Substitui nova linha por espaço


def transcrever_audio(file_path: str, nome_grupo: str, nome_original: str) -> str:
    """Transcreve o áudio usando o Google Speech-to-Text e salva a transcrição em um arquivo .txt."""
    
    # Define a variável de ambiente para a API
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("TRANSCRIPTION_API")
    client = speech.SpeechClient()

    # Obtém a taxa de amostragem do arquivo de áudio
    sample_rate = obter_taxa_amostragem(file_path)

    # Configurações de transcrição
    with open(file_path, "rb") as audio_file:
        content = audio_file.read()
    
    audio = speech.RecognitionAudio(content=content)
    
    # Verifica o formato do arquivo de áudio e define o encoding
    if file_path.endswith(".mp3"):
        encoding = speech.RecognitionConfig.AudioEncoding.MP3
    elif file_path.endswith(".wav"):
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
    else:
        raise ValueError("Formato de áudio não suportado. Use MP3 ou WAV.")

    config = speech.RecognitionConfig(
        encoding=encoding,
        sample_rate_hertz=sample_rate,
        language_code="pt-BR",
    )

    # Chama a API de transcrição
    response = client.recognize(config=config, audio=audio)

    # Combina as transcrições
    transcricao = "\n".join([result.alternatives[0].transcript for result in response.results])
    
    # Define o nome do arquivo de transcrição com um único espaço
    nome_transcricao = f"{limpar_nome_arquivo(nome_grupo).strip()} {limpar_nome_arquivo(os.path.splitext(nome_original)[0]).strip()}.txt"
    nome_transcricao = re.sub(r'\s+', ' ', nome_transcricao)  # Substitui múltiplos espaços por um único espaço
    transcricao_path = os.path.join(TRANSCRIPTION_DIRECTORY, nome_transcricao)

    # Salva a transcrição em um arquivo .txt
    with open(transcricao_path, "w", encoding="utf-8") as txt_file:
        txt_file.write(transcricao)
    
    return transcricao


def remover_arquivo_temporario(file_path: str):
    """Remove o arquivo de áudio temporário após o processamento."""
    if os.path.exists(file_path):
        os.remove(file_path)

