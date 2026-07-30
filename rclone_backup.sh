#!/bin/bash
set -e

echo "=================================================="
echo "    PERSONAL SERVER - CLOUD BACKUP"
echo "=================================================="

USER_CONFIG="$HOME/.config/rclone/rclone.conf"

# Check if rclone is installed
if ! command -v rclone &> /dev/null; then
    echo "❌ Error: Rclone is not installed. Please run ./rclone_setup.sh first."
    exit 1
fi

# Check if gdrive remote exists
if ! rclone --config "$USER_CONFIG" listremotes | grep -q "^gdrive:$"; then
    echo "❌ Error: Google Drive is not linked. Please run ./rclone_setup.sh first."
    exit 1
fi

echo "🚀 Starting backup to Google Drive..."
echo "Destination: Google Drive -> personal_server_database_backup"
echo "Syncing data folder... This may take a moment depending on size."

# Note: if you get Permission Denied on some Vaultwarden files, you can run this script with sudo:
# sudo ./rclone_backup.sh
rclone --config "$USER_CONFIG" sync ./data/ "gdrive:personal_server_database_backup" --progress

echo "=================================================="
echo "✅ Backup Complete! All your data is safely in the cloud."
echo "=================================================="
