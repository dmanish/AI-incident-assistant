#!/usr/bin/env bash
set -e

echo "🚀 Starting AI Incident Assistant in Codespaces..."

# Check if .env exists, if not create from example
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY if needed"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -q -r requirements.txt

# Install Node dependencies for React UI
echo "📦 Installing Node dependencies..."
cd frontend
npm install
cd ..

# Bootstrap data
echo "🔧 Bootstrapping data..."
python scripts/bootstrap.py

# Run initial ingest synchronously (so backend has data ready)
echo "📚 Running initial document ingestion..."
python scripts/ingest.py

# Start the ingest guard in background (to watch for changes)
echo "📊 Starting ingest guard to watch for changes..."
python scripts/ingest_guard.py &
INGEST_PID=$!

# Start backend in background
echo "🔌 Starting backend API on port 8080..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8080/healthz > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    sleep 1
done

# Start React frontend
echo "🎨 Starting React UI on port 3000..."
cd frontend

# Detect Codespaces and construct the correct backend URL
if [ -n "$CODESPACE_NAME" ]; then
    # In Codespaces, use the public forwarded URL
    BACKEND_URL="https://${CODESPACE_NAME}-8080.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    echo "🌐 Detected Codespaces - Backend URL: $BACKEND_URL"

    # Update frontend/.env file for Vite to pick up
    echo "# Frontend reads this at build-time (Vite requires VITE_ prefix)" > .env
    echo "VITE_BACKEND_URL=$BACKEND_URL" >> .env
    echo "" >> .env
else
    # Local dev or Docker - use localhost
    BACKEND_URL="http://localhost:8080"
    echo "🖥️  Local mode - Backend URL: $BACKEND_URL"

    # Ensure frontend/.env has localhost
    echo "# Frontend reads this at build-time (Vite requires VITE_ prefix)" > .env
    echo "VITE_BACKEND_URL=$BACKEND_URL" >> .env
    echo "" >> .env
fi

npm run dev

# Cleanup on exit
trap "kill $BACKEND_PID $INGEST_PID 2>/dev/null" EXIT
