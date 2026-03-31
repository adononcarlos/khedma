# Image unique pour Hugging Face Spaces : Postgres + pgvector, API FastAPI, interface Next.js, Chromium (PDF)

# 1. Construction de l'interface
FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npx next build

# 2. Image finale
FROM python:3.12-slim-bookworm
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers FASTEMBED_CACHE_PATH=/opt/fastembed \
    API_URL=http://127.0.0.1:8010 \
    DATABASE_URL=postgresql+psycopg://khedma@127.0.0.1:5432/khedma
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
 && apt-get update && apt-get install -y --no-install-recommends postgresql-17 postgresql-17-pgvector \
 && rm -rf /var/lib/apt/lists/*
ENV PATH=/usr/lib/postgresql/17/bin:$PATH

COPY backend/requirements.txt backend/requirements-local.txt /app/backend/
RUN pip install -r /app/backend/requirements-local.txt \
 && playwright install --with-deps --only-shell chromium \
 && python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='/opt/fastembed')" \
 && chmod -R a+rX /opt/pw-browsers /opt/fastembed

COPY --from=web /usr/local/bin/node /usr/local/bin/node
COPY --from=web /web/.next/standalone /app/frontend
COPY --from=web /web/.next/static /app/frontend/.next/static
COPY --from=web /web/public /app/frontend/public
COPY backend/app /app/backend/app
COPY backend/scripts /app/backend/scripts
COPY deploy/start.sh deploy/khedma.dump /app/deploy/

# Hugging Face exécute le conteneur avec l'utilisateur 1000
RUN useradd -m -u 1000 user && chmod -R a+rX /app && chmod 755 /app/deploy/start.sh
USER user
ENV HOME=/home/user
EXPOSE 7860
CMD ["/app/deploy/start.sh"]
