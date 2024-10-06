import os
import json
import re
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.models.summary import Summary
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from app.schemas.summary import SummaryData

load_dotenv()
chave_openai = os.getenv("OPENAI_API_KEY")

def concatenar_nome_arquivo(nome_grupo: str, nome_audio: str) -> str:
    """Concatena o nome do grupo e do áudio para formar o nome do arquivo."""
    # Garantir que a extensão .txt seja adicionada apenas uma vez
    nome_audio = nome_audio.rstrip('.txt')  # Remove .txt se estiver presente
    return f"{nome_grupo}_{nome_audio}.txt" 

def construir_caminho_arquivo(nome_arquivo: str, pasta: str = "D:/programação/github/EchoMeet/app/api/transcription/pasta_de_transcrições") -> str:
    return os.path.join(pasta, nome_arquivo)


def verificar_existencia_arquivo(caminho_arquivo: str) -> bool:
    return os.path.exists(caminho_arquivo)

def procurar_arquivo_txt(nome: str, pasta: str = "D:/programação/github/EchoMeet/app/api/transcription/pasta_de_transcrições") -> str:
    nome_arquivo = concatenar_nome_arquivo(*nome.split(' ', 1))
    caminho_completo = construir_caminho_arquivo(nome_arquivo, pasta)
    
    if verificar_existencia_arquivo(caminho_completo):
        return caminho_completo
    else:
        return f"Arquivo '{nome_arquivo}' não encontrado na pasta '{pasta}'"

def ler_conteudo_arquivo(caminho_arquivo: str) -> str:
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return f"Arquivo não encontrado: {caminho_arquivo}"
    except Exception as e:
        return f"Erro ao ler o arquivo: {str(e)}"

llm = ChatOpenAI(openai_api_key=chave_openai, temperature=0.9, model_name="gpt-3.5-turbo")

async def gerar_resumo(texto: str) -> str:
    mensagem = HumanMessage(content=f"Você é um assistente de IA projetado para analisar e resumir discussões de reuniões. Sua tarefa é revisar o texto abaixo e criar um resumo que capture os principais pontos discutidos, incluindo qualquer decisão e ação a ser tomada. Se não encontrar nenhum dado relevante, retorne apenas a mensagem 'Nenhum dado foi encontrado'. Crie o resumo no formato de texto em parágrafos:\n\n{texto}")
    
    resposta = await asyncio.to_thread(llm.invoke, [mensagem])
    return resposta.content

def identificar_dados(texto: str):
    if not texto.strip():
        return []
    
    mensagem = HumanMessage(content=f"""
    Você é um assistente de IA especializado em analisar discussões de reuniões. Sua tarefa é revisar o texto abaixo e identificar informações relevantes que contenham números, métricas, datas, valores monetários ou qualquer outro dado mensurável. Cada dado deve ser classificado com clareza, no formato 'Tipo de Dado: [tipo], Valor: [valor]'. Certifique-se de:
    1. Converter números por extenso, como '500 milhões', para sua forma numérica '500.000.000'.
    2. Especificar o tipo de dado, como por exemplo 'Faturamento anual' em vez de apenas 'Faturamento'.
    3. Se não encontrar nenhum dado relevante, retorne apenas a mensagem 'Nenhum dado foi encontrado'.

    Aqui está o texto para análise:\n\n{texto}
    """)

    resposta = llm.invoke([mensagem])
    
    # Debug: Verifique a resposta do LLM
    print("Resposta do LLM:", resposta.content)
    
    # Regex para capturar os dados formatados
    pattern = r'Tipo de Dado:\s*(.*?),\s*Valor:\s*(.*?)(?=\s*Tipo de Dado:|$)'
    matches = re.findall(pattern, resposta.content)

    # Converte as correspondências em uma lista de dicionários
    dados_identificados = [{"tipo": tipo.strip(), "valor": valor.strip()} for tipo, valor in matches]
    
    return dados_identificados

def processar_dados(dados: str):
    # Converte a string JSON em um objeto Python
    dados_list = json.loads(dados)
    
    # Filtra e organiza os dados
    dados_processados = []
    for item in dados_list:
        tipo = item["tipo"].replace("- ", "").strip()
        valor = item["valor"].strip()
        if valor:  # Apenas adiciona se houver valor
            dados_processados.append({"tipo": tipo, "valor": valor})
    
    return dados_processados

def remover_duplicatas(dados: list) -> list:
    vistos = set()
    dados_unicos = []
    
    for item in dados:
        if isinstance(item, dict):  # Certifica-se de que item é um dicionário
            tupla = (item['tipo'], item['valor'])
            if tupla not in vistos:
                dados_unicos.append(item)
                vistos.add(tupla)
    
    return dados_unicos

def criar_resumo_model(user_id: int, meeting_name: str, resumo_gerado: str, dados_dashboard: str) -> Summary:
    return Summary(
        user_id=user_id,
        meeting_name=meeting_name,
        summary_text=resumo_gerado,
        dashboard_data=dados_dashboard
    )

def salvar_no_banco(novo_resumo: Summary, db: Session) -> Summary:
    db.add(novo_resumo)
    db.commit()
    db.refresh(novo_resumo)
    return novo_resumo

import asyncio

async def salvar_resumo_no_banco(db: Session, nome: str, user_id: int, meeting_name: str, pasta: str = "D:/programação/github/EchoMeet/app/api/transcription/pasta_de_transcrições"):
    nome_grupo, nome_audio = nome.split(' ', 1)  # Divide o nome em grupo e áudio
    nome_completo = concatenar_nome_arquivo(nome_grupo, nome_audio)

    # Adiciona um delay para dar tempo de criar o arquivo
    await asyncio.sleep(2)  # Ajuste o tempo conforme necessário

    caminho_arquivo = procurar_arquivo_txt(nome_completo, pasta)

    if "não encontrado" in caminho_arquivo:
        return {"erro": caminho_arquivo}  # Retorna um dicionário com o erro

    conteudo_txt = ler_conteudo_arquivo(caminho_arquivo)
    resumo_gerado = await gerar_resumo(conteudo_txt)  # Aguarda a geração do resumo
    dados_dashboard = identificar_dados(conteudo_txt)
    dados_dashboard_sem_duplicatas = remover_duplicatas(dados_dashboard)
    dados_dashboard_json = json.dumps(dados_dashboard_sem_duplicatas)

    novo_resumo = criar_resumo_model(user_id, meeting_name, resumo_gerado, dados_dashboard_json)
    
    # Salva o resumo no banco
    resultado_salvamento = salvar_no_banco(novo_resumo, db)  # Função que salva no banco
    if resultado_salvamento is None:  # Se o salvamento falhar, pode retornar um erro
        return {"erro": "Falha ao salvar o resumo no banco."}
    
    return resultado_salvamento 