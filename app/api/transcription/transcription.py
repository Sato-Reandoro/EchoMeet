import os
import re
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, HTTPException
from pydub import AudioSegment  # Para manipulação de áudio
from pydub.utils import mediainfo
from dotenv import load_dotenv
from requests import Session
import whisper  # Biblioteca do Whisper da OpenAI

# Carregar variáveis de ambiente
load_dotenv()

app = FastAPI()

# Diretório onde as transcrições serão salvas
TRANSCRIPTION_DIRECTORY = "pasta_de_transcrições"
Path(TRANSCRIPTION_DIRECTORY).mkdir(parents=True, exist_ok=True)

# Diretório temporário para salvar arquivos de áudio
TEMP_DIRECTORY = "audios/temp"
Path(TEMP_DIRECTORY).mkdir(parents=True, exist_ok=True)

def verificar_duracao_audio(arquivo_audio: str) -> float:
    """Verifica a duração do áudio em segundos."""    
    audio = AudioSegment.from_file(arquivo_audio)
    return len(audio) / 1000  # Retorna a duração em segundos

def converter_audio(input_file, output_file):
    """Converte o áudio para MP3."""    
    audio = AudioSegment.from_file(input_file)
    audio.export(output_file, format="mp3")  # Converte para MP3

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

def verificar_tamanho_arquivo(file_path: str) -> int:
    """Verifica o tamanho do arquivo em bytes."""    
    return os.path.getsize(file_path)

async def transcrever_audio_whisper(arquivo_audio: str, nome_grupo: str, meeting_name: str) -> str:
    """Transcreve o áudio utilizando o modelo Whisper da OpenAI e salva em um arquivo .txt."""
    try:
        # Carrega o modelo Whisper
        model = whisper.load_model("base")  # Modelos disponíveis: tiny, base, small, medium, large

        # Realiza a transcrição
        result = model.transcribe(arquivo_audio, language="pt")

        # Extrai a transcrição
        transcricao_final = result.get("text", "")

        # Salva a transcrição em um arquivo .txt
        transcricao_file_name = f"{nome_grupo}_{meeting_name}.txt"
        transcricao_file_path = os.path.join(TRANSCRIPTION_DIRECTORY, transcricao_file_name)

        with open(transcricao_file_path, "w", encoding="utf-8") as f:
            f.write(transcricao_final)

        return transcricao_file_path

    except Exception as e:
        print(f"Erro na transcrição: {str(e)}")  # Log detalhado de erro
        raise HTTPException(status_code=500, detail=f"Erro ao transcrever áudio: {str(e)}")

def remover_arquivo_temporario(file_path: str):
    """Remove o arquivo de áudio temporário após o processamento."""    
    if os.path.exists(file_path):
        os.remove(file_path)

async def processar_audio(request: Request, nome_grupo: str, db: Session, user_id: int):
    """Processa o áudio e transcreve usando Whisper."""
    form = await request.form()
    audio_file = form.get('audio_file')

    if not audio_file or not hasattr(audio_file, 'filename'):
        raise HTTPException(status_code=400, detail="Arquivo de áudio inválido ou ausente.")

    # Mantém o nome original do arquivo
    audio_filename = audio_file.filename
    audio_path = os.path.join(TEMP_DIRECTORY, audio_filename)
    audio_convertido_path = None  # <-- Inicialize aqui!

    try:
        # Salva o arquivo de áudio
        with open(audio_path, "wb") as f:
            f.write(await audio_file.read())

        # Verifica o tamanho do arquivo
        tamanho = verificar_tamanho_arquivo(audio_path)
        limite_tamanho_mb = 100  # Define o limite de tamanho em MB
        if tamanho > limite_tamanho_mb * 1024 * 1024:
            os.remove(audio_path)
            raise HTTPException(status_code=400, detail="Arquivo de áudio muito grande.")

        # Converte o áudio para .wav
        audio_convertido_path = os.path.join(TEMP_DIRECTORY, f"convertido_{audio_filename.rsplit('.', 1)[0]}.wav")
        converter_audio(audio_path, audio_convertido_path)

        # Transcreve o áudio usando Whisper
        transcricao_file_path = await transcrever_audio_whisper(audio_convertido_path, nome_grupo, audio_filename.rsplit('.', 1)[0])

        # Verifica se o arquivo de transcrição foi gerado corretamente
        if not os.path.exists(transcricao_file_path):
            raise HTTPException(status_code=404, detail=f"Arquivo de transcrição '{transcricao_file_path}' não encontrado.")

        return {"transcription": transcricao_file_path, "meeting_name": audio_filename.rsplit('.', 1)[0]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")
    finally:
        # Remove os arquivos temporários se existirem
        if audio_path and os.path.exists(audio_path):
            remover_arquivo_temporario(audio_path)
        if audio_convertido_path and os.path.exists(audio_convertido_path):
            remover_arquivo_temporario(audio_convertido_path)

