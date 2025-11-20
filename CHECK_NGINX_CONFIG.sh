#!/bin/bash

# Script to check Nginx configuration for frontend and backend

echo "=========================================="
echo "Nginx Configuration Checker"
echo "=========================================="
echo ""

# Check if Nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "❌ Nginx is not installed"
    exit 1
fi

echo "✅ Nginx is installed"
echo ""

# Check Nginx status
echo "=========================================="
echo "1. Nginx Service Status"
echo "=========================================="
sudo systemctl status nginx --no-pager -l | head -20
echo ""

# Find Nginx config files
echo "=========================================="
echo "2. Nginx Configuration Files"
echo "=========================================="
echo "Main config: /etc/nginx/nginx.conf"
echo "Sites available: /etc/nginx/sites-available/"
echo "Sites enabled: /etc/nginx/sites-enabled/"
echo ""

# List available sites
echo "=========================================="
echo "3. Available Site Configurations"
echo "=========================================="
if [ -d "/etc/nginx/sites-available" ]; then
    echo "Available sites:"
    ls -la /etc/nginx/sites-available/ 2>/dev/null || echo "   Directory not found"
else
    echo "   /etc/nginx/sites-available/ not found"
fi
echo ""

# List enabled sites
echo "=========================================="
echo "4. Enabled Site Configurations"
echo "=========================================="
if [ -d "/etc/nginx/sites-enabled" ]; then
    echo "Enabled sites:"
    ls -la /etc/nginx/sites-enabled/ 2>/dev/null || echo "   Directory not found"
else
    echo "   /etc/nginx/sites-enabled/ not found"
fi
echo ""

# Show main config
echo "=========================================="
echo "5. Main Nginx Configuration"
echo "=========================================="
if [ -f "/etc/nginx/nginx.conf" ]; then
    echo "First 50 lines of /etc/nginx/nginx.conf:"
    head -50 /etc/nginx/nginx.conf
else
    echo "   /etc/nginx/nginx.conf not found"
fi
echo ""

# Show default site config
echo "=========================================="
echo "6. Default Site Configuration"
echo "=========================================="
if [ -f "/etc/nginx/sites-enabled/default" ]; then
    echo "Contents of /etc/nginx/sites-enabled/default:"
    cat /etc/nginx/sites-enabled/default
elif [ -f "/etc/nginx/nginx.conf" ]; then
    echo "Checking if config is in main file..."
    grep -A 50 "server {" /etc/nginx/nginx.conf | head -100
else
    echo "   No default site configuration found"
fi
echo ""

# Test Nginx configuration
echo "=========================================="
echo "7. Test Nginx Configuration"
echo "=========================================="
sudo nginx -t
echo ""

# Show active server blocks
echo "=========================================="
echo "8. Active Server Blocks (from nginx -T)"
echo "=========================================="
sudo nginx -T 2>/dev/null | grep -E "^(server|listen|server_name|location|proxy_pass|root)" | head -50
echo ""

# Check frontend location
echo "=========================================="
echo "9. Frontend Configuration (location /)"
echo "=========================================="
sudo nginx -T 2>/dev/null | grep -A 10 "location /" | head -20
echo ""

# Check backend API location
echo "=========================================="
echo "10. Backend API Configuration (location /api/)"
echo "=========================================="
sudo nginx -T 2>/dev/null | grep -A 15 "location /api" | head -30
echo ""

# Check admin location
echo "=========================================="
echo "11. Admin Configuration (location /admin/)"
echo "=========================================="
sudo nginx -T 2>/dev/null | grep -A 10 "location /admin" | head -20 || echo "   No /admin/ location found"
echo ""

# Check static files location
echo "=========================================="
echo "12. Static Files Configuration (location /static/)"
echo "=========================================="
sudo nginx -T 2>/dev/null | grep -A 10 "location /static" | head -20 || echo "   No /static/ location found"
echo ""

# Check what ports Nginx is listening on
echo "=========================================="
echo "13. Nginx Listening Ports"
echo "=========================================="
sudo netstat -tlnp 2>/dev/null | grep nginx || sudo ss -tlnp 2>/dev/null | grep nginx || echo "   Could not determine listening ports"
echo ""

# Check Gunicorn status (backend)
echo "=========================================="
echo "14. Backend (Gunicorn) Status"
echo "=========================================="
if systemctl is-active --quiet gunicorn 2>/dev/null; then
    echo "✅ Gunicorn service is running"
    sudo systemctl status gunicorn --no-pager -l | head -10
elif pgrep -f gunicorn > /dev/null; then
    echo "⚠️  Gunicorn process is running but not as a service"
    ps aux | grep gunicorn | grep -v grep | head -5
else
    echo "❌ Gunicorn is not running"
fi
echo ""

# Check if backend port is accessible
echo "=========================================="
echo "15. Backend Port Check (127.0.0.1:8000)"
echo "=========================================="
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/admin/ | grep -q "200\|302\|404"; then
    echo "✅ Backend is responding on port 8000"
    curl -I http://127.0.0.1:8000/admin/ 2>/dev/null | head -5
else
    echo "❌ Backend is not responding on port 8000"
fi
echo ""

# Summary
echo "=========================================="
echo "Summary"
echo "=========================================="
echo "To view full config: sudo nginx -T"
echo "To edit config: sudo nano /etc/nginx/sites-available/default"
echo "To test config: sudo nginx -t"
echo "To reload: sudo systemctl reload nginx"
echo ""

