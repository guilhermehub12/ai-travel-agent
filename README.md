# Agente de Viagens IA com WhatsApp

Este projeto implementa um agente de IA conversacional para o WhatsApp, capaz de auxiliar usuários na busca de passagens aéreas, configurar alertas de preços e manter uma conversa natural sobre viagens.

## 📜 Sumário
- [Funcionalidades Principais](#-funcionalidades-principais)
- [Arquitetura do Projeto](#-arquitetura-do-projeto)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Pré-requisitos](#-pré-requisitos)
- [⚙️ Configuração do Ambiente](#️-configuração-do-ambiente)
- [🚀 Executando a API Django (Localmente)](#-executando-a-api-django-localmente)
- [📊 Dashboard de Monitoramento](#-dashboard-de-monitoramento)
- [📖 Documentação da API](#-documentação-da-api)
  - [GET /api/v1/search-flights/](#get-apiv1search-flights)
  - [POST /api/v1/create-alert/](#post-apiv1create-alert)
  - [GET /api/v1/check-alerts/](#get-apiv1check-alerts)
- [🤖 Configuração dos Workflows no n8n](#-configuração-dos-workflows-no-n8n)
  - [Workflow 1: Receptor Principal](#workflow-1-receptor-principal)
  - [Workflow 2: Verificador de Alertas](#workflow-2-verificador-de-alertas)
- [☁️ Deploy](#️-deploy)
- [💬 Exemplo de Interação](#-exemplo-de-interação)

## ✨ Funcionalidades Principais

* **Saudação Inteligente:** Recebe mensagens e responde de forma contextual.
* **Consulta de Preços:** Busca passagens aéreas entre cidades usando a API da Amadeus (com suporte a dados mockados para desenvolvimento offline).
* **Alerta de Preços:** Permite que o usuário configure alertas para rotas e preços específicos.
* **Conversação Natural:** Utiliza a API da OpenAI (GPT) para interpretar a linguagem natural do usuário, extraindo intenções e informações relevantes.
* **Dashboard Web:** Uma interface simples para visualizar todos os alertas de preço ativos.
* **Orquestração via n8n:** Gerencia o fluxo da conversa e a lógica de negócios, integrando todas as APIs.

## 🏗️ Arquitetura do Projeto

O sistema é composto por três grandes pilares que se comunicam de forma orquestrada pelo n8n.

`Canal do Usuário (WhatsApp)` ↔️ `Camada de API (Evolution/Oficial)` ↔️ `n8n (Orquestrador)` ↔️ `API Django (Backend)` ↔️ `Serviços Externos (OpenAI, Amadeus)`

O projeto Django também serve uma interface web (`/dashboard/`) para visualização de dados.

## 💻 Tecnologias Utilizadas

* **Orquestração:** [n8n.io](https://n8n.io/)
* **Backend:** Python 3.11+, Django, Django REST Framework
* **Frontend (Dashboard):** Django Templates, Pico.css
* **Inteligência Artificial:** OpenAI API (GPT-3.5-Turbo)
* **Dados de Voos:** Amadeus Self-Service API (com suporte a dados mockados)
* **Integração WhatsApp:** Evolution API ou WhatsApp Business Cloud API
* **Containerização:** Docker

## 📋 Pré-requisitos

Antes de começar, garanta que você tenha as seguintes ferramentas instaladas:
* Python 3.10+ e `pip`
* Docker e Docker Compose (para o deploy e para rodar a Evolution API, se for o caso)
* Uma instância do n8n (local ou na nuvem)
* Acesso às APIs da OpenAI e Amadeus (com as chaves de API)
* [Postman](https://www.postman.com/downloads/) ou similar para testar os endpoints.

## ⚙️ Configuração do Ambiente

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/guilhermehub12/ai-travel-agent
    cd ai-travel-agent
    ```

2.  **Crie o arquivo de ambiente:**
    Copie o arquivo de exemplo `.env.example` para `.env` e preencha com suas chaves e configurações.
    ```bash
    cp .env.example .env
    nano .env
    ```
    **Conteúdo do `.env`:**
    ```env
    # Chave secreta do Django (gere uma nova, ex: [https://djecrety.ir/](https://djecrety.ir/))
    SECRET_KEY="sua-chave-secreta-aqui"

    # Configurações de desenvolvimento
    DEBUG=True
    ALLOWED_HOSTS=127.0.0.1,localhost

    # Chaves da Amadeus
    AMADEUS_API_KEY="SUA_CHAVE_DE_API_AMADEUS"
    AMADEUS_API_SECRET="SEU_SEGREDO_DE_API_AMADEUS"
    # Use 'production' para a API real ou 'test' para o ambiente de teste
    AMADEUS_HOSTNAME=production

    # Chave da OpenAI
    OPENAI_API_KEY="sk-..."

    # Controle de Mock
    # Mude para True para usar o mock_flight_data.json e trabalhar offline
    USE_MOCK_AMADEUS=False

    # Variáveis para banco de dados (PostgreSQL)
    DATABASE_URL='postgresql://user:password@host/database'
    ```

3.  **Crie e ative o ambiente virtual Python:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Aplique as migrações do banco de dados:**
    ```bash
    python manage.py migrate
    ```

## 🚀 Executando a API Django (Localmente)

Com o ambiente configurado, inicie o servidor de desenvolvimento:
```bash
python manage.py runserver
```

A API estará disponível em http://127.0.0.1:8000/api/v1/... e o Dashboard em http://127.0.0.1:8000/dashboard/.

## 📊 Dashboard de Monitoramento
- O projeto inclui uma interface web simples para monitorar todos os alertas de preço que estão atualmente ativos no sistema.

- Acesso: Para acessar o dashboard localmente, inicie o servidor e navegue até:
http://127.0.0.1:8000/dashboard/

- Funcionalidade: A página exibe uma tabela em tempo real com os dados dos alertas, incluindo o ID do usuário, a rota, o preço alvo e a data de criação.

## 📖 Documentação da API
- Todos os endpoints são prefixados com /api/v1/.

### GET /api/v1/search-flights/
Busca por ofertas de voos com base na origem, destino e data.

* **Parâmetros (Query):**
    * `origem` (string, obrigatório): Código IATA da origem (ex: `GRU`).
    * `destino` (string, obrigatório): Código IATA do destino (ex: `FOR`).
    * `data` (string, obrigatório): Data da partida no formato `AAAA-MM-DD`.
* **Exemplo de Requisição:**
    `bash
    curl "http://127.0.0.1:8000/api/v1/search-flights/?origem=FOR&destino=GRU&data=2025-08-07"
    `
* **Resposta de Sucesso (200 OK):**
    `json
    {
        "route": "FOR -> GRU",
        "date": "2025-08-07",
        "flight_options": [
            {
                "origin": "FOR",
                "destination": "GRU",
                "departure_time": "2025-08-07T18:15:00",
                "arrival_time": "2025-08-07T23:05:00",
                "stops": 1,
                "duration": "PT4H50M",
                "carrier": "AZUL LINHAS AEREAS BRASILEIRAS",
                "price": "593.50"
            }
        ]
    }
    `

### POST /api/v1/create-alert/
Cria um novo alerta de preço para um usuário.

* **Corpo da Requisição (JSON):**
    * `user_whatsapp_id` (string, obrigatório): Identificador do usuário no WhatsApp.
    * `origin_code` (string, obrigatório): Código IATA da origem.
    * `destination_code` (string, obrigatório): Código IATA do destino.
    * `target_price` (number, obrigatório): Preço alvo para o alerta.
* **Exemplo de Requisição:**
    `bash
    curl -X POST http://127.0.0.1:8000/api/v1/create-alert/ \
    -H "Content-Type: application/json" \
    -d '{"user_whatsapp_id": "5585999998888", "origin_code": "FOR", "destination_code": "GRU", "target_price": 500.00}'
    `
* **Resposta de Sucesso (201 Created):**
    `json
    {
        "mensagem": "Alerta criado com sucesso!"
    }
    `

### GET /api/v1/check-alerts/
Verifica todos os alertas ativos, busca os preços atuais e retorna uma lista de notificações a serem enviadas.

* **Exemplo de Requisição:**
    `bash
    curl http://127.0.0.1:8000/api/v1/check-alerts/
    `
* **Resposta de Sucesso (200 OK):**
    `json
    {
        "notifications_to_send": [
            {
                "user_whatsapp_id": "5585999998888",
                "origin": "FOR",
                "destination": "GRU",
                "target_price": "500.00",
                "found_price": "480.75"
            }
        ]
    }
    `

## 🤖 Configuração dos Workflows no n8n

### Workflow 1: Receptor Principal
Este workflow é ativado por um **Webhook** que recebe as mensagens do WhatsApp.

1. **Webhook**: Recebe a mensagem.

2. **Audio**: Se a mensagem for um áudio, o áudio é transcrito para texto e enviado para a IA.

2. **IA Agent**: Utiliza o OpenAI Chat Model e Redis Memory para entender a mensagem do usuário, manter o contexto e decidir qual ferramenta usar (search_flight, check_alerts ou create_alert). Se faltar informação, ele gera uma pergunta de esclarecimento.

3. **Tools (HTTP Request Tool)**: Nós separados para search_flight, check_alerts e create_alert são conectados à entrada Tool do Agente. Eles executam as chamadas para a API Django.

4. **Set (Formatar Resposta)**: A saída do IA Agent (seja o resultado de uma ferramenta ou uma pergunta) é formatada em uma responseText.

5. **Nó de Envio (WhatsApp)**: Envia a responseText de volta para o usuário.

### Workflow 2: Verificador de Alertas
Este workflow é ativado por um agendamento ou se for pedido na conversa (ativado pela IA Agent) para verificar os preços periodicamente.

1.  **Schedule:** É o gatilho. Configure para rodar no intervalo desejado (ex: `0 8 * * *` para rodar todo dia às 8h da manhã).
2.  **HTTP Request (`Verificar Alertas`):** Faz uma chamada `GET` para o endpoint `/check-alerts/`.
3.  **SplitInBatches:** Separa a lista de `notifications_to_send` para tratar uma por uma.
4.  **Set (`Montar Notificação`):** Para cada notificação, formata uma mensagem de alerta de preço.
5.  **Nó de Envio (WhatsApp):** Envia a notificação para o `user_whatsapp_id` correspondente.

## ☁️ Deploy

A aplicação está containerizada usando Docker para garantir portabilidade. O `Dockerfile` no repositório cria uma imagem de produção otimizada. O deploy pode ser feito em qualquer plataforma que suporte contêineres, como **Google Cloud Run** ou uma **VM (Compute Engine)** com Docker e Nginx.

## 💬 Exemplo de Interação

> **Usuário:** Oi
>
> **Bot:** Olá! Sou o assistente de viagens da milha.ai! 🛫 Posso te ajudar a encontrar as melhores passagens e criar alertas de preços. O que você gostaria de fazer?
>
> **Usuário:** Quero viajar de Fortaleza para Guarulhos no dia 7 de agosto
>
> **Bot:** Encontrei estas opções para Fortaleza → Guarulhos para o dia 07/08/2025:
> ✈️ AZUL LINHAS AEREAS BRASILEIRAS | Saída: 18:15h | 1 parada(s) | Preço: R$ 593.50
>
> Quer que eu configure um alerta caso o preço baixe?
