import asyncio
import os
import re
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, HTTPException
from google.cloud import speech
from pydub import AudioSegment  # Para manipulação de áudio
from pydub.utils import mediainfo
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
TRANSCRIPTION_DIRECTORY = "pasta_de_transcrições"
Path(TRANSCRIPTION_DIRECTORY).mkdir(parents=True, exist_ok=True)

# Diretório temporário para salvar arquivos de áudio
TEMP_DIRECTORY = "audios\temp"
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

def limpar_texto(transcricao: str) -> str:
    # Remover falantes repetidos consecutivos
    transcricao_limpa = re.sub(r'(Falante \d+:)\s*(\1)+', r'\1', transcricao)
    
    # Remover fala genérica irrelevante, se necessário
    transcricao_limpa = re.sub(r'fala\s+sem\s+sentido', '', transcricao_limpa, flags=re.IGNORECASE)
    
    # Remover múltiplos espaços em branco
    transcricao_limpa = re.sub(r'\s+', ' ', transcricao_limpa).strip()
    
    return transcricao_limpa

# Função para identificar falantes e agrupar falas por falante
def identificar_falantes_com_diarizacao(words_info):
    falantes = []
    falante_atual = None
    texto_atual = []

    for word_info in words_info:
        falante = word_info.speaker_tag
        texto = word_info.word

        # Se for o primeiro falante ou mudança de falante
        if falante_atual is None or falante != falante_atual:
            # Se houver texto acumulado do falante anterior, salva ele
            if texto_atual:
                falantes.append(f"Falante {falante_atual}: {' '.join(texto_atual)}")
            # Começa um novo falante
            falante_atual = falante
            texto_atual = [texto]
        else:
            # O mesmo falante continua, adiciona ao texto atual
            texto_atual.append(texto)

    # Adiciona o texto do último falante
    if texto_atual:
        falantes.append(f"Falante {falante_atual}: {' '.join(texto_atual)}")

    return " ".join(falantes)


async def transcrever_audio(arquivo_audio: str, nome_grupo: str, meeting_name: str) -> str:
    client = speech.SpeechClient()
    storage_client = storage.Client()

    try:
        # Envia o arquivo de áudio para o Google Cloud Storage
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(f'audios/{os.path.basename(arquivo_audio)}')
        await asyncio.to_thread(blob.upload_from_filename, arquivo_audio)  # Usar asyncio.to_thread para operações síncronas

        print(f"Arquivo {arquivo_audio} enviado para o Google Cloud Storage com sucesso.")
        
        gcs_uri = f'gs://{BUCKET_NAME}/audios/{os.path.basename(arquivo_audio)}'

        # Obter o formato e a taxa de amostragem do áudio
        formato_audio = obter_formato_audio(arquivo_audio)
        taxa_amostragem = obter_taxa_amostragem(arquivo_audio)

        # Configuração da transcrição
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16  # Valor padrão
        if formato_audio == 'mp3':
            encoding = speech.RecognitionConfig.AudioEncoding.MP3
        elif formato_audio == 'wav':
            encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
        elif formato_audio == 'flac':
            encoding = speech.RecognitionConfig.AudioEncoding.FLAC
        else:
            raise HTTPException(status_code=400, detail="Formato de áudio não suportado.")

        # Configuração do reconhecimento com diarização
        diarization_config = speech.SpeakerDiarizationConfig(
            enable_speaker_diarization=True,  # Ativa a diarização de falantes
            min_speaker_count=2,  # Número mínimo estimado de falantes
            max_speaker_count=10  # Número máximo estimado de falantes
        )

        config = speech.RecognitionConfig(
            language_code="pt-BR",
            encoding=encoding,
            sample_rate_hertz=taxa_amostragem,
            diarization_config=diarization_config  # Adiciona a configuração de diarização
        )

        audio = speech.RecognitionAudio(uri=gcs_uri)

        # Usando LongRunningRecognize para longas gravações
        operation = client.long_running_recognize(config=config, audio=audio)

        # Espera pela conclusão da operação
        response = await asyncio.to_thread(operation.result, timeout=3600)

        # Extrai a transcrição da resposta e as informações da diarização
        transcricoes = []
        for result in response.results:
            alternative = result.alternatives[0]
            words_info = alternative.words  # Obter todas as palavras e informações de diarização

            # Monta a transcrição com tags dos falantes
            transcricao_completa = identificar_falantes_com_diarizacao(words_info)
            transcricoes.append(transcricao_completa)

        # Combine as transcrições em uma única string
        transcricao_final = "\n".join(transcricoes)

        # Limpa o texto, removendo falantes repetidos ou desnecessários
        transcricao_limpa = limpar_texto(transcricao_final)

        # Salva a transcrição limpa em um arquivo .txt
        transcricao_file_name = f"{nome_grupo}_{meeting_name}.txt"
        transcricao_file_path = os.path.join(TRANSCRIPTION_DIRECTORY, transcricao_file_name)

        with open(transcricao_file_path, "w", encoding="utf-8") as f:
            f.write(transcricao_limpa)

        return transcricao_file_path

    except Exception as e:
        print(f"Erro na transcrição: {str(e)}")  # Log detalhado de erro
        raise HTTPException(status_code=500, detail=f"Erro ao transcrever áudio: {str(e)}")

def remover_arquivo_temporario(file_path: str):
    """Remove o arquivo de áudio temporário após o processamento."""    
    if os.path.exists(file_path):
        os.remove(file_path)

async def processar_audio(request: Request, nome_grupo: str, db: Session, user_id: int):
    """Processa o áudio e transcreve."""    
    form = await request.form()
    audio_file = form.get('audio_file')

    if not audio_file or not hasattr(audio_file, 'filename'):
        raise HTTPException(status_code=400, detail="Arquivo de áudio inválido ou ausente.")

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

        # Converte o áudio para .wav
        audio_convertido_path = os.path.join(TEMP_DIRECTORY, f"convertido_{audio_filename.rsplit('.', 1)[0]}.wav")
        converter_audio(audio_path, audio_convertido_path)

        # Converte o arquivo de áudio para MP3
        audio_mp3_path = os.path.join(TEMP_DIRECTORY, f"convertido_{audio_filename.rsplit('.', 1)[0]}.mp3")
        converter_audio(audio_convertido_path, audio_mp3_path)

        # Transcreve o áudio
        transcricao_file_path = await transcrever_audio(audio_mp3_path, nome_grupo, audio_filename.rsplit('.', 1)[0])

        # Verifica se o arquivo de transcrição foi gerado corretamente
        if not os.path.exists(transcricao_file_path):
            raise HTTPException(status_code=404, detail=f"Arquivo de transcrição '{transcricao_file_path}' não encontrado.")

        return {"transcription": transcricao_file_path, "meeting_name": audio_filename.rsplit('.', 1)[0]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")
    finally:
        # Remove os arquivos temporários
        remover_arquivo_temporario(audio_path)
        remover_arquivo_temporario(audio_convertido_path)
        remover_arquivo_temporario(audio_mp3_path)