# Usar uma imagem Python oficial como base
FROM python:3.11-slim

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED True
ENV APP_HOME /app
WORKDIR $APP_HOME

# Instalar as dependências de sistema (pandoc e poppler para pdfunite)
RUN apt-get update && apt-get install -y pandoc poppler-utils && rm -rf /var/lib/apt/lists/*

# Copiar o arquivo de dependências Python para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código da aplicação para o contêiner
COPY . .

# Expor a porta em que o app vai rodar (usando um padrão caso a variável PORT não seja definida)
EXPOSE 8080

# Comando para iniciar a aplicação em produção com Gunicorn
# O shell é usado para substituir a variável de ambiente ${PORT}
CMD ["/bin/sh", "-c", "gunicorn --workers 1 --threads 8 --timeout 0 --bind 0.0.0.0:${PORT:-8080} app:app"]
