#!/bin/bash
set -e

echo "=================================================="
echo "    PERSONAL SERVER - USER PROVISIONING"
echo "=================================================="

# Prompt for the username if not provided as an argument
if [ -z "$1" ]; then
    read -p "Enter the username to create/invite: " USERNAME
else
    USERNAME="$1"
fi

if [ -z "$USERNAME" ]; then
    echo "❌ Error: Username cannot be empty."
    exit 1
fi

echo ""
echo "Creating invite link for: $USERNAME"

# Navigate to backend and run the python provisioning script
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
    python provision.py "$USERNAME"
    deactivate
else
    echo "❌ Error: Python virtual environment not found in backend/venv."
    echo "Please run ./setup.sh first to set up the environment."
    exit 1
fi

echo "=================================================="
echo "✅ Provisioning complete!"
echo "=================================================="
