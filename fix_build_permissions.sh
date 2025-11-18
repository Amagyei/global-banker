#!/bin/bash
# Fix permissions for frontend build directory

echo "Fixing permissions for /home/banker/global_banker_front/dist..."

# Remove the dist directory if it exists and is causing issues
if [ -d "/home/banker/global_banker_front/dist" ]; then
    echo "Removing existing dist directory..."
    sudo rm -rf /home/banker/global_banker_front/dist
fi

# Ensure banker owns the entire frontend directory
echo "Setting ownership to banker:banker..."
sudo chown -R banker:banker /home/banker/global_banker_front

# Set proper permissions
echo "Setting directory permissions..."
sudo chmod -R 755 /home/banker/global_banker_front

echo "✅ Permissions fixed. You can now run 'npm run build'"

