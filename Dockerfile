# imagem Python
FROM python:3.11-slim as builder

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# RUN apt-get update && apt-get install -y ...

# Copia o arquivo de requerimentos e instala as dependências do Python
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


FROM python:3.11-slim

RUN useradd --create-home appuser
ENV PATH="/home/appuser/.local/bin:${PATH}"
WORKDIR /home/appuser/app
USER appuser

COPY --from=builder /wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

COPY . .

# Expõe a porta que o Gunicorn irá usar
EXPOSE 8080

# Comando para iniciar a aplicação quando o contêiner rodar
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "config.wsgi:application"]