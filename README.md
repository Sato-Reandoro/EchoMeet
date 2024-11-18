# EchoMeets

EchoMeets é um projeto de extensão desenvolvido em parceria entre a Faculdade Estácio e o Grupo Mônaco. <br>
O objetivo principal é fornecer uma solução inovadora que utiliza inteligência artificial para transformar áudios de reuniões em resumos claros e objetivos.
Neste repositório, você encontrará o back-end completo da aplicação, projetado para garantir eficiência e escalabilidade na gestão de informações corporativas.

## 🛠️ Funcionalidades

- **Gravação e transcrição de reuniões**: Transforma áudios de reuniões em texto automaticamente.
- **Resumo de reuniões**: Gera resumos vinculados a grupos de trabalho.
- **Gerenciamento de usuários e grupos**: Administra grupos e organiza reuniões associadas.
- **Dashboards de análise**: Oferece métricas e análises para tomada de decisão.
- **APIs robustas**: Facilmente integráveis com front-ends e serviços externos.

## ⚙️ Instalação e Execução

### Clonando o repositório

```bash
# Clone o repositório
git clone https://github.com/Sato-Reandoro/echomeets.git

# Acesse o diretório do projeto
cd echomeets

# Baixe todas as dependências necessárias do sistema com 
pip install -r requirements.txt
```

## 🚀 Tecnologias

- **Back-end**: [FastAPI](https://fastapi.tiangolo.com/)
- **Banco de dados**: PostgreSQL
- **Containerização**: Docker e Docker Compose
- **tratamento de áudio**: [FFMPEG](https://www.ffmpeg.org/download.html)

## 📦 Estrutura do Projeto

```bash
📂 EchoMeets
├── main.py            # Arquivo principal com os endpoints da API
├── 📂 api             # Contém a lógica dos endpoints dividida em 3 setores crud, summary e transcription
├── 📂 models          # Modelos do banco de dados
├── 📂 database        # conexão ao banco de dados
├── 📂 schemas         # criação de schemas para ser utilizado na aplicação
├── 📂 utils           # Funções de autorização e segurança da aplicação
└── docker-compose.yml # Configuração do Docker
```
## 🖥️ Pré-requisitos

Para executar o projeto, você precisará dos seguintes componentes instalados e configurados:

- [**Python (>=3.9)**](https://www.python.org/downloads/)  
  Linguagem principal para o desenvolvimento do back-end.  
- [**Docker e Docker Compose**](https://www.docker.com/products/docker-desktop/)  
  Para containerização e execução do ambiente de forma simplificada.  
- [**PostgreSQL**](https://www.postgresql.org/download/)  
  Banco de dados utilizado para armazenamento de informações.  
- [**FFMPEG**](https://www.ffmpeg.org/download.html)  
  Ferramenta para análise e processamento de áudio.  
- [**Token da OpenAI**](https://platform.openai.com/tokenizer)  
  Necessário para acessar os modelos de inteligência artificial responsáveis pela criação dos resumos.  
- [**Google Cloud Speech-to-Text JSON**](https://cloud.google.com/speech-to-text)  
  Credenciais de autenticação para utilizar a API de transcrição de áudios.

Certifique-se de que todas as dependências estejam instaladas antes de configurar o ambiente.

## ⚙️ Configuração do .env

Antes de rodar a aplicação, você precisará configurar o arquivo `.env` com as variáveis de ambiente necessárias. Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
DATABASE_URL=postgresql://<usuário>:<senha>@<host>:<porta>/<nome_do_banco>
SECRET_KEY=<seu_codigo_hash_para_login>
ALGORITHM=<algoritmo_hash_usado>
TRANSCRIPTION_API=<caminho_do_json_da_api_de_transcrição_speech_to_text>
OPENAI_API_KEY=<sua_chave_da_openai>
GOOGLE_CLOUD_PROJECT=<nome_do_seu_projeto_no_google_cloud>
BUCKET_NAME=<nome_do_bucket_para_audio>
```


## 📖 Documentação da API

Antes de acessar a documentação interativa, você precisa rodar a aplicação com o seguinte comando:

```bash
uvicorn app:main.app --reload
``` 

Após iniciar a aplicação, a documentação interativa estará disponível nos seguintes endereços:

- [**Swagger UI**](http://localhost:8000/docs)  
- [**Redoc**](http://localhost:8000/redoc)


## 🤝 Contribuição

Este projeto não teria sido possível sem a colaboração dos meus amigos, que trabalharam comigo no desenvolvimento do back-end.  
Afinal, o verdadeiro back-end são os amigos que a gente fez pelo caminho! 😊  

Um agradecimento especial a:  

- [![Lucas M. Rocha](https://github.com/Mr-Lucas-m.png?size=50)](https://github.com/Mr-Lucas-m)  
  **[Lucas M. Rocha](https://github.com/Mr-Lucas-m)**  
  *Desenvolvimento do ambiente dos grupos na aplicação.*  

- <a href="https://github.com/moises-menezesdev">
    <img src="https://github.com/moises-menezesdev.png" width="50" height="50" alt="moises-menezesdev" style="vertical-align: middle; margin-right: 10px;">
  </a>  
**[moises-menezesdev](https://github.com/moises-menezesdev)** 
 *Integração da API de transcrição ao sistema, além de administrar o ambiente do Google Cloud Speech-to-Text.*



Agradeço imensamente a dedicação, paciência e parceria de cada um de vocês!




