#!/usr/bin/env bash
set -e

echo "🐳 Starting AI Incident Assistant with Docker..."

# Check if .env exists, if not create from example
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY if needed"
fi

# Build and start containers
echo "🔨 Building and starting containers..."
docker compose -f docker/docker-compose.yml up --build

# Note: Ctrl+C to stop
