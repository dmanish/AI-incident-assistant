.PHONY: help codespaces docker clean stop

help:
	@echo "🧠 AI Incident Assistant - Quick Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make codespaces    - Start in Codespaces (one command)"
	@echo "  make docker        - Start with Docker (one command)"
	@echo "  make stop          - Stop Docker containers"
	@echo "  make clean         - Clean up data and stop containers"
	@echo ""

codespaces:
	@chmod +x start-codespaces.sh
	@./start-codespaces.sh

docker:
	@chmod +x start-docker.sh
	@./start-docker.sh

stop:
	@echo "🛑 Stopping Docker containers..."
	@docker compose -f docker/docker-compose.yml down

clean: stop
	@echo "🧹 Cleaning up data..."
	@rm -rf data/chroma/*
	@rm -rf data/logs/*.duckdb
	@echo "✅ Clean complete!"
