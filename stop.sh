#!/bin/bash

echo "=================================================="
echo "🛑 STOPPING PERSONAL SERVER SERVICES..."
echo "=================================================="

# 1. Stop Caddy
if pgrep -f "caddy run" > /dev/null; then
    echo "Stopping Caddy..."
    pkill -f "caddy run" || true
else
    echo "Caddy is not running."
fi

# 2. Stop Ollama & llama-server
if pgrep -f "ollama serve" > /dev/null || pgrep -f "llama-server" > /dev/null; then
    echo "Stopping Ollama AI..."
    pkill -f "ollama serve" || true
    pkill -f "llama-server" || true
else
    echo "Ollama is not running."
fi

# 3. Stop FastAPI (Uvicorn)
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "Stopping FastAPI Backend..."
    pkill -f "uvicorn app.main:app" || true
else
    echo "FastAPI is not running."
fi

# 4. Stop Vaultwarden Docker containers
if command -v docker &> /dev/null; then
    echo "Stopping Vaultwarden containers..."
    # Attempt to remove both the old possible name and the local name without throwing errors
    docker rm -f vaultwarden vaultwarden-local 2>/dev/null || sudo docker rm -f vaultwarden vaultwarden-local 2>/dev/null || true
fi

echo "=================================================="
echo "✅ ALL SERVICES STOPPED!"
echo "=================================================="
