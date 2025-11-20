#!/bin/bash
# Script to check Gunicorn status and view logs

echo "=== Checking Gunicorn Process ==="
echo ""

# Check if Gunicorn is running
echo "1. Running Gunicorn processes:"
ps aux | grep gunicorn | grep -v grep || echo "   No Gunicorn processes found"
echo ""

# Check for systemd service (common names)
echo "2. Checking for systemd services:"
for service in gunicorn gunicorn.service global-banker banker-django django; do
    if systemctl list-units --type=service | grep -q "$service"; then
        echo "   Found service: $service"
        systemctl status "$service" --no-pager -l | head -20
    fi
done
echo ""

# Check what's listening on port 8000
echo "3. Processes listening on port 8000:"
sudo lsof -i :8000 2>/dev/null || sudo netstat -tlnp | grep :8000 || echo "   Nothing listening on port 8000"
echo ""

# Check Nginx configuration for backend proxy
echo "4. Nginx backend proxy configuration:"
sudo nginx -T 2>/dev/null | grep -A 10 "location /api" || echo "   No /api location found in Nginx config"
echo ""

# Check for Gunicorn socket file
echo "5. Gunicorn socket files:"
find /home/banker -name "*.sock" 2>/dev/null | head -5 || echo "   No socket files found"
echo ""

# Check for Gunicorn PID file
echo "6. Gunicorn PID files:"
find /home/banker -name "gunicorn.pid" -o -name "*.pid" 2>/dev/null | head -5 || echo "   No PID files found"
echo ""

# Check common log locations
echo "7. Common log locations:"
for log in /var/log/gunicorn/error.log /var/log/gunicorn/access.log /home/banker/logs/*.log; do
    if [ -f "$log" ]; then
        echo "   Found: $log"
        echo "   Last 5 lines:"
        tail -5 "$log" 2>/dev/null | sed 's/^/     /'
    fi
done
echo ""

# Check if running via supervisor
echo "8. Checking for supervisor:"
if command -v supervisorctl &> /dev/null; then
    echo "   Supervisor is installed"
    supervisorctl status 2>/dev/null || echo "   Supervisor not running"
else
    echo "   Supervisor not installed"
fi
echo ""

echo "=== How to View Backend Logs ==="
echo ""
echo "If Gunicorn is running directly:"
echo "  - Check process output: ps aux | grep gunicorn"
echo "  - Check if logs are redirected to a file"
echo ""
echo "If using systemd:"
echo "  sudo journalctl -u <service-name> -f"
echo ""
echo "If using supervisor:"
echo "  supervisorctl tail -f <process-name>"
echo ""
echo "If running manually:"
echo "  - Logs go to stdout/stderr"
echo "  - Check the terminal where it was started"
echo "  - Or check if output is redirected to a file"

