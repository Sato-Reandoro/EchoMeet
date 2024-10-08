import asyncio
from datetime import datetime
import os
import re
import subprocess
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from google.cloud import speech
from pydub import AudioSegment  # Importa a biblioteca para manipular áudio
from pydub.utils import mediainfo
from app.api.summary.summary import concatenar_nome_arquivo, gerar_resumo, salvar_resumo_no_banco
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from google.cloud import storage

# Carregar variáveis de ambiente
load_dotenv()

# Nome do bucket e o arquivo de credenciais do .env
BUCKET_NAME = os.getenv("BUCKET_NAME", "transcricao-audioechomeet")  # Nome do bucket padronizado
TRANSCRIPTION_API = os.getenv("TRANSCRIPTION_API")
app = FastAPI()

# Diretório onde as transcrições serão salvas
TRANSCRIPTION_DIRECTORY = "D:/programação/github/EchoMeet/app/api/transcription/pasta_de_transcrições"
Path(TRANSCRIPTION_DIRECTORY).mkdir(parents=True, exist_ok=True)

# Diretório temporário para salvar arquivos de áudio
TEMP_DIRECTORY = "D:/programação/github/EchoMeet/app/api/transcription/audios/temp"
Path(TEMP_DIRECTORY).mkdir(parents=True, exist_ok=True)

def verificar_duracao_audio(arquivo_audio: str) -> float:
    """Verifica a duração do áudio em segundos."""    
    audio = AudioSegment.from_file(arquivo_audio)
    return len(audio) / 1000  # Retorna a duração em segundos

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

def obter_formato_audio(file_path: str) -> str:
    """Obtém o formato do arquivo de áudio.""" 
    info = mediainfo(file_path)
    return info['codec_name']

def limpar_nome_arquivo(nome: str) -> str:
    """Remove caracteres inválidos do nome do arquivo."""    
    nome = re.sub(r'[<>:"/\\|?*]', '', nome)  # Remove caracteres inválidos
    return nome.replace('\n', ' ').replace('\r', ' ')  # Substitui nova linha por espaço

def verificar_tamanho_arquivo(file_path: str) -> int:
    """Verifica o tamanho do arquivo em bytes."""    
    return os.path.getsize(file_path)

async def transcrever_audio(arquivo_audio: str, nome_grupo: str, meeting_name: str) -> str:
    """Transcreve o áudio utilizando a API do Google Cloud e salva em um arquivo .txt."""
    client = speech.SpeechClient()
    storage_client = storage.Client()

    try:
        # Envia o arquivo de áudio para o Google Cloud Storage
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(f'audios/{os.path.basename(arquivo_audio)}')
        blob.upload_from_filename(arquivo_audio)

        gcs_uri = f'gs://{BUCKET_NAME}/audios/{os.path.basename(arquivo_audio)}'

        # Obter o formato e a taxa de amostragem do áudio
        formato_audio = obter_formato_audio(arquivo_audio)
        taxa_amostragem = obter_taxa_amostragem(arquivo_audio)

        # Configuração da transcrição
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16  # Valor padrão

        # Ajusta a codificação com base no formato do áudio
        if formato_audio == 'mp3':
            encoding = speech.RecognitionConfig.AudioEncoding.MP3
        elif formato_audio == 'wav':
            encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
        elif formato_audio == 'flac':
            encoding = speech.RecognitionConfig.AudioEncoding.FLAC
        else:
            raise HTTPException(status_code=400, detail="Formato de áudio não suportado.")

        config = speech.RecognitionConfig(
            language_code="pt-BR",
            encoding=encoding,
            sample_rate_hertz=taxa_amostragem,
        )

        audio = speech.RecognitionAudio(uri=gcs_uri)

        # Usando LongRunningRecognize
        operation = client.long_running_recognize(config=config, audio=audio)

        # Aguarda a conclusão da operação
        response = operation.result(timeout=90)  # Espera pela conclusão da operação

        # Extrai a transcrição da resposta
        transcricoes = []
        for result in response.results:
            transcricoes.append(result.alternatives[0].transcript)

        # Combine as transcrições em uma única string
        transcricao_final = "\n".join(transcricoes)

        # Salva a transcrição em um arquivo .txt
        transcricao_file_name = f"{nome_grupo}_{meeting_name}.txt"
        transcricao_file_path = os.path.join(TRANSCRIPTION_DIRECTORY, transcricao_file_name)

        with open(transcricao_file_path, "w", encoding="utf-8") as f:
            f.write(transcricao_final)

        return transcricao_file_path  # Retorna o caminho do arquivo de transcrição

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao transcrever áudio: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao transcrever áudio: {str(e)}")

def remover_arquivo_temporario(file_path: str):
    """Remove o arquivo de áudio temporário após o processamento."""    
    if os.path.exists(file_path):
        os.remove(file_path)

def salvar_mono_audio_file(mono_audio_file: str, filename: str) -> str:
    """Salva o arquivo mono_audio_file no diretório de transcrições."""    
    file_path = os.path.join(TEMP_DIRECTORY, filename)
    # Usamos o FFmpeg para salvar o arquivo, mas também podemos usar a biblioteca soundfile se necessário.
    subprocess.run(['ffmpeg', '-i', mono_audio_file, file_path], check=True)
    return file_path

def converter_audio_para_mono(caminho_entrada: str, caminho_saida: str):
    """Converte um arquivo de áudio para mono usando FFmpeg."""    
    comando = [
        'ffmpeg',
        '-i', caminho_entrada,
        '-ac', '1',  # Define 1 canal (mono)
        caminho_saida,
        '-y'  # Sobrescreve o arquivo de saída se já existir
    ]
    subprocess.run(comando, check=True)

async def salvar_transcricao_em_txt(nome_grupo: str, meeting_name: str, transcricoes: list):
    """Salva a transcrição em um arquivo .txt."""    
    transcricao_final = "\n".join(transcricoes)
    transcricao_file_name = f"{nome_grupo} {meeting_name}.txt"
    transcricao_file_path = os.path.join(TEMP_DIRECTORY, transcricao_file_name)

    # Salva a transcrição em um arquivo .txt
    with open(transcricao_file_path, "w", encoding="utf-8") as f:
        f.write(transcricao_final)

    return transcricao_file_path

async def processar_audio(request: Request, nome_grupo: str, db: Session, user_id: int):
    """Processa o áudio e transcreve."""
    form = await request.form()
    audio_file = form.get('audio_file')

    if not audio_file or not hasattr(audio_file, 'filename'):
        raise HTTPException(status_code=400, detail="Arquivo de áudio inválido ou ausente.")

    # Mantém o nome original do arquivo
    audio_filename = audio_file.filename
    audio_path = os.path.join(TEMP_DIRECTORY, audio_filename)

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

        # Converte o áudio para mono
        audio_mono_path = os.path.join(TEMP_DIRECTORY, f"mono_{audio_filename}")
        converter_audio_para_mono(audio_path, audio_mono_path)

        # Transcreve o áudio e retorna o nome do áudio no resultado
        transcricao_file_path = await transcrever_audio(audio_mono_path, nome_grupo, audio_filename.rsplit('.', 1)[0])

        # Verifica se o arquivo de transcrição foi gerado corretamente
        if not os.path.exists(transcricao_file_path):
            raise HTTPException(status_code=404, detail=f"Arquivo de transcrição '{transcricao_file_path}' não encontrado.")

        return {"transcription": transcricao_file_path, "meeting_name": audio_filename.rsplit('.', 1)[0]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")
    finally:
        # Remove os arquivos temporários
        remover_arquivo_temporario(audio_path)
        remover_arquivo_temporario(audio_mono_path)