#!/usr/bin/env bash
set -e

echo "🐳 Starting AI Incident Assistant with Docker..."

# Check if .env exists, if not create from example
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY if needed"
fi

# Detect Codespaces and set VITE_BACKEND_URL
if [ -n "$CODESPACE_NAME" ]; then
    export VITE_BACKEND_URL="https://${CODESPACE_NAME}-8080.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    echo "🌐 Detected Codespaces - Setting VITE_BACKEND_URL=$VITE_BACKEND_URL"
else
    export VITE_BACKEND_URL="http://localhost:8080"
    echo "🖥️  Local mode - Setting VITE_BACKEND_URL=$VITE_BACKEND_URL"
fi

# Build and start containers
echo "🔨 Building and starting containers..."
docker compose -f docker/docker-compose.yml up --build

# Note: Ctrl+C to stop
