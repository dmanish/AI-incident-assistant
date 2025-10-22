FROM python:3.10-slim

WORKDIR /app
COPY ../requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# App source
COPY ../app /app/app

# Non-root for safety
RUN useradd -m appuser
USER appuser

EXPOSE 8080
CMD ["python", "app/main.py"]


