import pandas as pd
import plotly.express as px
from sqlalchemy.orm import Session
from fastapi import HTTPException
import json
from app.models.models_summary import Summary

# Lista de palavras-chave relacionadas a problemas financeiros
keywords = [
    "Perda", "Déficit", "Prejuízo", "Rombo", "Vermelho", "Dívida",
    "Endividamento", "Inadimplência", "Calote", "Atrasos", "Custos",
    "Despesas", "Gastos excessivos", "Custos fixos", "Custos variáveis",
    "Lucratividade negativa", "Margem de lucro negativa", "Fluxo de caixa negativo",
    "Retorno sobre o investimento negativo", "Insolvência", "Falência",
    "Crise financeira", "Situação financeira delicada", "Corte de custos",
    "Reestruturação", "Recuperação de crédito", "Negociação de dívidas",
    "Negativo", "menor que zero", "abaixo de zero", "deficitário",
    "Perda líquida", "prejuízo líquido", "Passivo", "desvalorização",
    "risco financeiro", "incerteza financeira", "Redução", "corte"
]

# Função para contar quantas palavras-chave estão no tipo de valor
def count_negative_keywords(tipo: str) -> int:
    return sum(keyword.lower() in tipo.lower() for keyword in keywords)

# Função para buscar os dados do dashboard no banco de dados
def get_dashboard_data(db: Session, summary_id: int):
    summary = db.query(Summary).filter(Summary.summary_id == summary_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Resumo não encontrado")
    
    if summary.dashboard_data is None or summary.dashboard_data.strip() == "":
        raise HTTPException(status_code=404, detail="Dados do dashboard não encontrados ou estão vazios.")

    try:
        data = json.loads(summary.dashboard_data)
        formatted_data = [{"tipo": item["tipo"], "valor": item["valor"]} for item in data]
        df = pd.DataFrame(formatted_data)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="O DataFrame está vazio. Não há dados para gerar o dashboard.")
        
        # Contar palavras-chave e marcar como problemático se houver
        df['keyword_count'] = df['tipo'].apply(count_negative_keywords)
        df['problematic'] = df['keyword_count'] > 0
        
        return df
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Dados do dashboard estão em um formato inválido.")

# Função para separar os valores numéricos e percentuais
def get_dashboard_options(db: Session, summary_id: int):
    df = get_dashboard_data(db, summary_id)
    
    numeric_values = df[df['valor'].str.contains(r'^[\d,.]+$', regex=True)]
    percent_values = df[df['valor'].str.contains(r'%')]
    problematic_metrics = df[df['problematic']]

    return {
        "numeric": numeric_values['tipo'].tolist(),
        "percent": percent_values['tipo'].tolist(),
        "problematic": problematic_metrics['tipo'].tolist()
    }

# Função para gerar gráfico de valores numéricos
def create_numeric_dashboard(df):
    df['valor'] = pd.to_numeric(df['valor'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce')
    
    # Ajustar os valores com base na contagem de palavras-chave
    for index, row in df.iterrows():
        if row['keyword_count'] >= 2:
            # Se houver duas ou mais palavras-chave negativas, o valor é positivo
            df.at[index, 'valor'] = abs(row['valor'])
        elif row['problematic']:
            # Caso contrário, se for problemático, transforme em negativo
            df.at[index, 'valor'] *= -1

    df = df.dropna(subset=['valor'])

    if df.empty:
        raise ValueError("O DataFrame está vazio após a limpeza dos dados.")

    fig = px.bar(
        df,
        x='tipo',
        y='valor',
        title='Gráfico de Valores Numéricos',
        labels={'tipo': 'Tipo de Dado', 'valor': 'Valor'},
        color='valor',
        text='valor'
    )
    fig.show()

# Função para gerar gráfico de valores percentuais
def create_percent_dashboard(df):
    df['valor'] = df['valor'].str.replace('%', '').astype(float)
    
    # Transformar valores percentuais negativos se forem problemáticos
    df.loc[df['problematic'], 'valor'] *= -1
    
    fig = px.pie(
        df,
        names='tipo',
        values='valor',
        title='Gráfico de Valores Percentuais',
    )
    fig.show()

# Função que permite escolher qual tipo de gráfico gerar (numérico ou percentual)
def generate_dashboard_by_type(db: Session, summary_id: int, value_type: str):
    df = get_dashboard_data(db, summary_id)
    
    if value_type == "numeric":
        numeric_df = df[df['valor'].str.contains(r'^[\d,.]+$', regex=True)]
        create_numeric_dashboard(numeric_df)
    elif value_type == "percent":
        percent_df = df[df['valor'].str.contains(r'%')]
        create_percent_dashboard(percent_df)
    else:
        raise HTTPException(status_code=400, detail="Tipo de valor inválido. Escolha entre 'numeric' ou 'percent'.")

# Função para verificar e gerar gráficos para várias métricas
def generate_dashboards_for_metrics(db: Session, summary_id: int, metrics: list[str]):
    options = get_dashboard_options(db, summary_id)
    
    for metric in metrics:
        if metric not in options["numeric"] and metric not in options["percent"]:
            raise HTTPException(status_code=400, detail=f"Métrica inválida: {metric}")
        
        value_type = "numeric" if metric in options["numeric"] else "percent"
        df = get_dashboard_data(db, summary_id)
        metric_df = df[df['tipo'] == metric]

        if value_type == "numeric":
            create_numeric_dashboard(metric_df)
        else:
            create_percent_dashboard(metric_df)
