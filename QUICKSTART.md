# ⚡ Quick Start Guide

## One Command Setup

### For GitHub Codespaces
```bash
./start-codespaces.sh
```

### For Docker (Local)
```bash
./start-docker.sh
```

## What Happens Automatically

✅ Creates `.env` from `.env.example` (if needed)
✅ Installs Python and Node dependencies
✅ Bootstraps sample security data
✅ Starts Backend API on port 8080
✅ Starts React UI on port 3000

## Access URLs

### Codespaces
- Backend: `https://<codespace-id>-8080.app.github.dev/healthz`
- Frontend: `https://<codespace-id>-3000.app.github.dev/`

### Local Docker
- Backend: http://localhost:8080/healthz
- Frontend: http://localhost:3000

## Configuration (Optional)

Edit `.env` file to configure:
- `OPENAI_API_KEY` - Your OpenAI API key (optional, uses local embeddings if not set)
- `EMBED_BACKEND` - Choose `openai` or `local` (default: local)
- `JWT_SECRET` - Secret for JWT tokens

## Test Users

After starting, you can login with these test accounts:

| Email | Password | Role |
|-------|----------|------|
| alice@company | pass1 | security |
| bob@company | pass2 | engineering |
| charlie@company | pass3 | sales |

## Example Queries

Try asking the assistant:

1. "Show me today's failed login attempts for user jdoe"
2. "How should I handle a suspected phishing email?"
3. "What's the escalation path for a production outage?"

## Troubleshooting

### Port already in use
```bash
# Stop existing containers
docker compose -f docker/docker-compose.yml down
```

### Permission denied on scripts
```bash
chmod +x start-codespaces.sh start-docker.sh
```

### Need to reset data
```bash
# Remove data and restart
rm -rf data/chroma/* data/logs/*.duckdb
./start-docker.sh  # or ./start-codespaces.sh
```

### Frontend not connecting to backend
Make sure:
- Backend is running and healthy: `curl http://localhost:8080/healthz`
- `VITE_BACKEND_URL` is set correctly (automatically handled by scripts)
- In Codespaces: Port 8080 is set to "Public" visibility

---

📚 For detailed documentation, see [README.md](README.md)
