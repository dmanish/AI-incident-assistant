FROM python:3.11-slim

WORKDIR /app

# Install deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source (these will be overridden by bind mounts during dev)
COPY app /app/app
COPY scripts /app/scripts

# Expose API port
EXPOSE 8080

# For demo simplicity, run as root to avoid bind-mount permission issues
# (You can switch to a non-root user later once you add chown logic)
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8080"]

