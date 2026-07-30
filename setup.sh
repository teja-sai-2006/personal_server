#!/bin/bash
set -e

echo "=================================================="
echo "    PERSONAL SERVER - AUTOMATED SETUP SCRIPT"
echo "=================================================="

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install Python 3."
    exit 1
fi

# 1. Setup Python Virtual Environment
echo "📦 Setting up Python Virtual Environment..."
if [ ! -d "backend/venv" ]; then
    python3 -m venv backend/venv
    echo "✅ Virtual environment created at backend/venv"
else
    echo "✅ Virtual environment already exists."
fi

# 2. Install Python Requirements
echo "📦 Installing Python dependencies..."
source backend/venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Python dependencies installed."
else
    echo "❌ Error: requirements.txt not found!"
    exit 1
fi
deactivate

# 3. Pull Vaultwarden Docker Image (if docker is installed)
if command -v docker &> /dev/null; then
    echo "🐳 Docker is installed. Pulling Vaultwarden image..."
    sudo docker pull vaultwarden/server:latest || docker pull vaultwarden/server:latest
    echo "✅ Vaultwarden image pulled successfully."
else
    echo "⚠️ Warning: Docker is not installed. Vaultwarden will not run. See requirements-user.txt."
fi

# 4. Check for Caddy
if ! command -v caddy &> /dev/null; then
    echo "⚠️ Warning: Caddy is not installed. The reverse proxy will not run. See requirements-user.txt."
else
    echo "✅ Caddy is installed."
fi

# 5. Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "⚠️ Warning: Ollama is not installed. Local AI features will not run. See requirements-user.txt."
else
    echo "✅ Ollama is installed."
fi

echo "=================================================="
echo "🎉 SETUP COMPLETE 🎉"
echo "=================================================="
echo "To provision a user, run: cd backend && source venv/bin/activate && python provision.py <username>"
echo "To start the system, run: ./start.sh"
echo "=================================================="
