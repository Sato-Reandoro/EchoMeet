import os
from google.cloud import speech
from dotenv import load_dotenv  # Importa a biblioteca dotenv

# Carregar as variáveis do arquivo .env
load_dotenv()

def transcrever_audio(arquivo_audio):
    try:
        # Cria um cliente para o serviço de transcrição
        cliente = speech.SpeechClient()

        # Abre o arquivo de áudio para leitura
        with open(arquivo_audio, "rb") as audio_file:
            conteudo_audio = audio_file.read()

        # Configura o áudio e as definições de como será transcrito
        audio = speech.RecognitionAudio(content=conteudo_audio)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,  # Certifique-se do tipo de áudio correto
            sample_rate_hertz=22050,  # Taxa de amostragem do áudio
            language_code="pt-BR",  # Idioma da transcrição
        )

        # Envia o áudio para o serviço e recebe a resposta
        response = cliente.recognize(config=config, audio=audio)

        # Extrai o texto transcrito da resposta
        texto_transcrito = ""
        for resultado in response.results:
            texto_transcrito += resultado.alternatives[0].transcript

        return texto_transcrito
    except Exception as e:
        print(f"Erro ao transcrever áudio: {e}")
        return None

def salvar_transcricao_em_txt(grupo, caminho_completo_arquivo_audio, texto):
    try:
        # Extrai apenas o nome do arquivo sem o caminho e extensão
        nome_arquivo_audio = os.path.basename(caminho_completo_arquivo_audio).split('.')[0]
        
        # Remove caracteres inválidos para nomes de arquivos no Windows
        nome_arquivo_audio = nome_arquivo_audio.replace(":", "").replace("\\", "").replace("/", "")
        
        nome_arquivo_txt = f"{grupo}_{nome_arquivo_audio}.txt"
        caminho_pasta = "pasta_transcricoes"
        
        # Cria a pasta onde os arquivos .txt serão salvos, se não existir
        if not os.path.exists(caminho_pasta):
            os.makedirs(caminho_pasta)
        
        # Salva o texto transcrito em um arquivo .txt
        with open(os.path.join(caminho_pasta, nome_arquivo_txt), "w") as arquivo_txt:
            arquivo_txt.write(texto)

        print(f"Arquivo salvo em: {os.path.join(caminho_pasta, nome_arquivo_txt)}")
    except Exception as e:
        print(f"Erro ao salvar a transcrição: {e}")

# Exemplo de uso:
if __name__ == "__main__":
    # Nome do arquivo de áudio
    nome_arquivo_audio = "C:\\AudiosTeste\\WhatsApp Ptt 2024-09-12 at 11.35.03 (online-audio-converter.com).wav"  # Substitua pelo seu arquivo real

    # Nome do grupo
    grupo = "GrupoX"

    # Transcrever o áudio e salvar em um arquivo .txt
    texto = transcrever_audio(nome_arquivo_audio)
    
    if texto:
        salvar_transcricao_em_txt(grupo, nome_arquivo_audio, texto)

