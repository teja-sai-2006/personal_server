#!/bin/bash
set -e

echo "=================================================="
echo "    RCLONE SETUP & AUTHENTICATION"
echo "=================================================="

# Check if rclone is installed
if ! command -v rclone &> /dev/null; then
    echo "⚠️ Rclone is not installed. Installing now..."
    sudo -v ; curl https://rclone.org/install.sh | sudo bash
else
    echo "✅ Rclone is already installed."
fi

echo "=================================================="
echo "🔗 Authenticating with Google Drive..."
echo "=================================================="
echo "This will open your web browser. Please log in to your Google account"
echo "and grant Rclone permission to access your Google Drive."
echo "Press ENTER to continue..."
read -r

# Create the remote named 'gdrive' of type 'drive' (Google Drive)
rclone config create gdrive drive config_is_local true

echo "=================================================="
echo "✅ Authentication Complete!"
echo "You can now run ./rclone_backup.sh to back up your data."
echo "=================================================="
