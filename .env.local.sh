#!/bin/bash
# =============================================================================
# Local environment setup for AI Incident Assistant
# This file sets all environment variables used by the backend and frontend.
# It is sourced automatically when Codespace or devcontainer starts.
# =============================================================================

# -------------------------
# Backend (FastAPI / Flask)
# -------------------------

# Secret key for JWT authentication
# Use `openssl rand -hex 32` to generate a new value
export JWT_SECRET="local_dev_secret_key"

# Directory for Chroma database storage
# Use an absolute path if running outside Codespaces
export CHROMA_DB_DIR="./data/chroma"

# Directory for audit and authentication logs
export AUDIT_DIR="./data/logs"

# Path for DuckDB database file (used for auth logs, queries)
export DUCK_DB_PATH="./data/logs/security.duckdb"

# -------------------------
# OpenAI / Embeddings
# -------------------------

# API key for OpenAI (optional).
# Leave empty to use local CPU embeddings (MiniLM).
# Set if you want to use OpenAI embeddings or LLM.
# Example: export OPENAI_API_KEY="sk-..."
export OPENAI_API_KEY=""

# Embedding backend to use.
# Options:
#   - "cpu" → Use local sentence-transformer model (all-MiniLM-L6-v2)
#   - "openai" → Use OpenAI embeddings (text-embedding-3-small)
export EMBEDDING_BACKEND="cpu"

# -------------------------
# Frontend / Streamlit
# -------------------------

# The backend API base URL (FastAPI service)
# Example for Codespace: "https://<codespace-id>-8080.app.github.dev"
# Example for local: "http://127.0.0.1:8080"
export BACKEND_URL="http://127.0.0.1:8080"

# Optional: default Streamlit port
export STREAMLIT_SERVER_PORT=8501

# =============================================================================
echo "✅ Environment variables loaded successfully."