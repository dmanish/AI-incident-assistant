# docker/Dockerfile
FROM python:3.11-slim

# Tools for healthcheck & some wheels; and bash for "bash -c" in compose
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential bash \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (better cache)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source (these are also bind-mounted in dev)
COPY app /app/app
COPY scripts /app/scripts
COPY data /app/data
COPY frontend /app/frontend

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080 8501

# Compose overrides the command per service
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8080"]

