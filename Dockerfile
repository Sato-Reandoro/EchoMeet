FROM python:3.11.10-slim-bullseye

RUN apt-get update && apt-get install -y ffmpeg

# Instalar as dependências do sistema necessárias para o psycopg2
RUN apt-get update && \
    apt-get install -y gcc libpq-dev musl-dev && \
    rm -rf /var/lib/apt/lists/*


COPY .env .env
COPY ./app ./app

COPY requirements.txt .

# Instalar as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

# Comando para iniciar a aplicação
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
