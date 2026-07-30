#!/bin/bash
set -e

echo "=================================================="
echo "    PERSONAL SERVER - CLOUD RESTORE"
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

echo "⚠️  WARNING: This will overwrite your current server data with the"
echo "data from your Google Drive backup. If you have newer data on this server,"
echo "it will be lost or overwritten!"
echo ""
echo "Are you sure you want to proceed? (Type 'yes' and press Enter to confirm)"
read -r CONFIRMATION

if [ "$CONFIRMATION" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo "🚀 Starting restore from Google Drive..."
echo "Source: Google Drive -> personal_server_database_backup"
echo "Restoring to local data folder... This may take a moment depending on size."

# Note: if you get Permission Denied on some Vaultwarden files, you can run this script with sudo:
# sudo ./rclone_restore.sh
rclone --config "$USER_CONFIG" sync "gdrive:personal_server_database_backup" ./data/ --progress

echo "=================================================="
echo "✅ Restore Complete! Your data has been downloaded."
echo "=================================================="
