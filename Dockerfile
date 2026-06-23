FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json ./
RUN npm install --no-audit --no-fund --loglevel=error

COPY frontend/ ./
RUN npm run build


FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /data \
    && apt-get update \
    && apt-get install -y --no-install-recommends supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

EXPOSE 8000

VOLUME ["/data"]

CMD ["supervisord", "-c", "/app/supervisord.conf"]
