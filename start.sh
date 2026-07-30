#!/bin/bash
set -e

echo "=================================================="
echo "    PERSONAL SERVER - STARTUP"
echo "=================================================="

# Function to clean up all background processes on exit
cleanup() {
    echo ""
    bash stop.sh
    exit 0
}

# Trap SIGINT (Ctrl+C) to run the cleanup function
trap cleanup SIGINT SIGTERM

# 1. Start Ollama (if installed)
if command -v ollama &> /dev/null; then
    echo "🚀 Starting Ollama..."
    ollama serve &
    OLLAMA_PID=$!
else
    echo "⚠️ Ollama is not installed. Skipping."
fi

# 2. Start Vaultwarden (via Docker)
if command -v docker &> /dev/null; then
    echo "🚀 Starting Vaultwarden..."
    # Create vaultwarden data directory if missing
    mkdir -p data/db/vaultwarden
    # Run container in background, remove old one if exists
    sudo docker rm -f vaultwarden-local 2>/dev/null || docker rm -f vaultwarden-local 2>/dev/null || true
    # Use sudo if docker requires it, else normal docker
    if sudo -n docker info &> /dev/null; then
        sudo docker run -d --name vaultwarden-local -e WEBSOCKET_ENABLED=true -v $(pwd)/data/db/vaultwarden:/data -p 8001:80 vaultwarden/server:latest
    else
        docker run -d --name vaultwarden-local -e WEBSOCKET_ENABLED=true -v $(pwd)/data/db/vaultwarden:/data -p 8001:80 vaultwarden/server:latest
    fi
else
    echo "⚠️ Docker is not installed. Skipping Vaultwarden."
fi

# 3. Start Caddy
if command -v caddy &> /dev/null; then
    echo "🚀 Starting Caddy Reverse Proxy..."
    caddy run --config caddy/Caddyfile &
    CADDY_PID=$!
else
    echo "❌ Error: Caddy is not installed. Please install Caddy (see requirements-user.txt)."
    exit 1
fi

# 4. Start FastAPI Backend
echo "🚀 Starting FastAPI Backend..."
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
    uvicorn app.main:app --host 127.0.0.1 --port 8000 &
    BACKEND_PID=$!
else
    echo "❌ Error: Virtual environment not found. Did you run setup.sh?"
    kill $(jobs -p) 2>/dev/null || true
    exit 1
fi
cd ..

echo "=================================================="
echo "✅ SYSTEM IS RUNNING!"
echo "🌐 Access the application at: http://localhost:8081"
echo "🛑 Press Ctrl+C to stop all services."
echo "=================================================="

# Wait for all background processes indefinitely
wait
