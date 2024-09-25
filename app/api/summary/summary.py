import os
import json
import re
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.models.summary import Summary
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage


load_dotenv()
chave_openai = os.getenv("OPENAI_API_KEY")

def concatenar_nome_arquivo(nome_grupo: str, nome_audio: str) -> str:
    return f"{nome_grupo} {nome_audio}.txt"

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

def gerar_resumo(texto: str) -> str:
    mensagem = HumanMessage(content=f"Você é um assistente de IA projetado para analisar e resumir discussões de reuniões. Sua tarefa é revisar o texto abaixo e criar um resumo que capture os principais pontos discutidos, incluindo qualquer decisão e ação a ser tomada. Crie o resumo no formato de texto em parágrafos:\n\n{texto}")
    
    resposta = llm.invoke([mensagem])
    return resposta.content

def identificar_dados(texto: str):
    if not texto.strip():
        return []
    
    mensagem = HumanMessage(content=f"Você é um assistente de IA projetado para analisar discussões de reuniões. Sua tarefa é revisar o texto abaixo e identificar dados relevantes, como números, métricas, datas ou qualquer outro tipo de informação mensurável. Cada item deve ser apresentado no formato: 'Tipo de Dado: [tipo], Valor: [valor]', especifique o tipo de dado que irá sair, se for faturamento, seria faturamento do que? E caso um valor esteja escrito como exemplo'500 milhões' você deve escrever o numero em algarismos assim passando de '500 milhões' para '500.000.000'. Aqui está o texto:\n\n{texto}")
    
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


def criar_resumo_model(summary_data, resumo_gerado: str, dados_dashboard: str) -> Summary:
    return Summary(
        user_id=summary_data.user_id,
        meeting_name=summary_data.meeting_name,
        summary_text=resumo_gerado,
        dashboard_data=dados_dashboard
    )

def salvar_no_banco(novo_resumo: Summary, db: Session) -> Summary:
    db.add(novo_resumo)
    db.commit()
    db.refresh(novo_resumo)
    return novo_resumo

def salvar_resumo_no_banco(summary_data, db: Session, nome_grupo: str, nome_audio: str, pasta: str = "D:/programação/github/EchoMeet/app/api/transcription/pasta_de_transcrições"):
    nome_completo = f"{nome_grupo} {nome_audio}"
    caminho_arquivo = procurar_arquivo_txt(nome_completo, pasta)

    if "não encontrado" in caminho_arquivo:
        return {"erro": caminho_arquivo}
    
    conteudo_txt = ler_conteudo_arquivo(caminho_arquivo)
    resumo_gerado = gerar_resumo(conteudo_txt)
    dados_dashboard = identificar_dados(conteudo_txt)
    dados_dashboard_sem_duplicatas = remover_duplicatas(dados_dashboard)

    dados_dashboard_json = json.dumps(dados_dashboard_sem_duplicatas)
    
    novo_resumo = criar_resumo_model(summary_data, resumo_gerado, dados_dashboard_json)
    return salvar_no_banco(novo_resumo, db)
