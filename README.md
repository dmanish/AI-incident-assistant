# AI-incident-assistant
1. How to RUN
        This project supports two ways to run — a simple direct launch (for GitHub Codespaces) and a Dockerized deployment (for local reproducibility).
        Option 1 – Run Directly in GitHub Codespaces (Recommended for Demo)

        This is the fastest way to get started — no Docker needed.

        Steps:
        # 1. Install dependencies
        pip install -r requirements.txt

        # 2. Run the app
        python app/main.py
        Option 2 – Run Locally with Docker (Production-Style)

        This option uses the provided Dockerfile and docker-compose.yml for a reproducible environment.

        Steps:
        # 1. Build and start the container
        docker compose -f docker/docker-compose.yml up --build

        # 2. Access the app
        http://localhost:8080
        This mirrors how the app would be deployed in a production microservice setup.

