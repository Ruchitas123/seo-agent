# syntax=docker/dockerfile:1
# One URL: Flask API + static React UI (frontend/dist)

FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-bookworm-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-docker.txt /app/backend/requirements-docker.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/backend/requirements-docker.txt

COPY backend/ /app/backend/
COPY --from=frontend-build /build/dist /app/frontend/dist

WORKDIR /app/backend
EXPOSE 8000

# PORT is set by Render/Fly/Railway. One worker + threads suits SSE /analyze.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 8 --timeout 600 --access-logfile - api:app"]
