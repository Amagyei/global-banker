#!/bin/bash

# Script to check how the Django backend is running and how to access it

echo "=========================================="
echo "Django Backend Status Checker"
echo "=========================================="
echo ""

# Check for Gunicorn
echo "=========================================="
echo "1. Checking for Gunicorn"
echo "=========================================="
if systemctl is-active --quiet gunicorn 2>/dev/null; then
    echo "✅ Gunicorn is running as a systemd service"
    echo ""
    echo "Service status:"
    systemctl status gunicorn --no-pager -l | head -15
    echo ""
    echo "Service file location:"
    systemctl show gunicorn -p FragmentPath 2>/dev/null || echo "   Could not find service file"
    echo ""
elif pgrep -f gunicorn > /dev/null; then
    echo "⚠️  Gunicorn process is running (not as service)"
    echo ""
    echo "Running processes:"
    ps aux | grep gunicorn | grep -v grep
    echo ""
else
    echo "❌ Gunicorn is not running"
fi
echo ""

# Check for uvicorn
echo "=========================================="
echo "2. Checking for Uvicorn"
echo "=========================================="
if pgrep -f uvicorn > /dev/null; then
    echo "✅ Uvicorn is running"
    echo ""
    echo "Running processes:"
    ps aux | grep uvicorn | grep -v grep
    echo ""
else
    echo "❌ Uvicorn is not running"
fi
echo ""

# Check for Django dev server
echo "=========================================="
echo "3. Checking for Django Dev Server"
echo "=========================================="
if pgrep -f "manage.py runserver" > /dev/null; then
    echo "✅ Django dev server is running"
    echo ""
    echo "Running processes:"
    ps aux | grep "manage.py runserver" | grep -v grep
    echo ""
else
    echo "❌ Django dev server is not running"
fi
echo ""

# Check for any Python process on port 8000
echo "=========================================="
echo "4. Checking Port 8000"
echo "=========================================="
if command -v netstat &> /dev/null; then
    echo "Processes listening on port 8000:"
    sudo netstat -tlnp 2>/dev/null | grep :8000 || echo "   No process listening on port 8000"
elif command -v ss &> /dev/null; then
    echo "Processes listening on port 8000:"
    sudo ss -tlnp 2>/dev/null | grep :8000 || echo "   No process listening on port 8000"
elif command -v lsof &> /dev/null; then
    echo "Processes listening on port 8000:"
    sudo lsof -i :8000 2>/dev/null || echo "   No process listening on port 8000"
else
    echo "   Cannot check ports (netstat/ss/lsof not available)"
fi
echo ""

# Check what's listening on common ports
echo "=========================================="
echo "5. All Listening Ports (Python/Django related)"
echo "=========================================="
if command -v ss &> /dev/null; then
    sudo ss -tlnp 2>/dev/null | grep -E ":(8000|8080|3000|5000)" | head -10
elif command -v netstat &> /dev/null; then
    sudo netstat -tlnp 2>/dev/null | grep -E ":(8000|8080|3000|5000)" | head -10
else
    echo "   Cannot check ports"
fi
echo ""

# Test backend connectivity
echo "=========================================="
echo "6. Testing Backend Connectivity"
echo "=========================================="
echo "Testing http://127.0.0.1:8000/admin/ ..."
if curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" --max-time 5 http://127.0.0.1:8000/admin/ 2>/dev/null; then
    echo "✅ Backend is responding on port 8000"
    echo ""
    echo "Response headers:"
    curl -I http://127.0.0.1:8000/admin/ 2>/dev/null | head -10
else
    echo "❌ Backend is not responding on port 8000"
    echo "   (This could mean it's not running, or listening on a different port/interface)"
fi
echo ""

# Check for systemd service files
echo "=========================================="
echo "7. Systemd Service Files"
echo "=========================================="
echo "Checking for Gunicorn service:"
if [ -f "/etc/systemd/system/gunicorn.service" ]; then
    echo "✅ Found: /etc/systemd/system/gunicorn.service"
    echo ""
    echo "Service configuration:"
    cat /etc/systemd/system/gunicorn.service
elif [ -f "/etc/systemd/system/gunicorn.socket" ]; then
    echo "✅ Found: /etc/systemd/system/gunicorn.socket"
    cat /etc/systemd/system/gunicorn.socket
else
    echo "❌ No Gunicorn systemd service found"
    echo ""
    echo "Checking for Django service:"
    ls -la /etc/systemd/system/*.service 2>/dev/null | grep -i django || echo "   No Django service found"
fi
echo ""

# Check for supervisor
echo "=========================================="
echo "8. Checking for Supervisor"
echo "=========================================="
if command -v supervisorctl &> /dev/null; then
    echo "✅ Supervisor is installed"
    echo ""
    echo "Supervisor status:"
    sudo supervisorctl status 2>/dev/null || echo "   Could not get status"
else
    echo "❌ Supervisor is not installed"
fi
echo ""

# Check for screen/tmux sessions
echo "=========================================="
echo "9. Checking for Screen/Tmux Sessions"
echo "=========================================="
if command -v screen &> /dev/null; then
    echo "Screen sessions:"
    screen -ls 2>/dev/null || echo "   No screen sessions"
fi
if command -v tmux &> /dev/null; then
    echo "Tmux sessions:"
    tmux ls 2>/dev/null || echo "   No tmux sessions"
fi
echo ""

# Check environment and working directory
echo "=========================================="
echo "10. Backend Process Details"
echo "=========================================="
if pgrep -f "gunicorn\|uvicorn\|manage.py" > /dev/null; then
    echo "Backend processes with details:"
    ps aux | grep -E "gunicorn|uvicorn|manage.py" | grep -v grep | while read line; do
        echo "---"
        echo "$line"
        PID=$(echo "$line" | awk '{print $2}')
        if [ -n "$PID" ]; then
            echo "  Working directory: $(pwdx $PID 2>/dev/null || readlink /proc/$PID/cwd 2>/dev/null || echo 'unknown')"
            echo "  Command: $(cat /proc/$PID/cmdline 2>/dev/null | tr '\0' ' ' || echo 'unknown')"
        fi
    done
else
    echo "   No backend processes found"
fi
echo ""

# Summary and access instructions
echo "=========================================="
echo "SUMMARY & ACCESS INSTRUCTIONS"
echo "=========================================="
echo ""

# Determine how backend is running
BACKEND_TYPE="unknown"
BACKEND_PORT="unknown"

if systemctl is-active --quiet gunicorn 2>/dev/null || pgrep -f gunicorn > /dev/null; then
    BACKEND_TYPE="Gunicorn"
    BACKEND_PORT="8000"
elif pgrep -f uvicorn > /dev/null; then
    BACKEND_TYPE="Uvicorn"
    BACKEND_PORT="8000"
elif pgrep -f "manage.py runserver" > /dev/null; then
    BACKEND_TYPE="Django Dev Server"
    BACKEND_PORT="8000"
fi

echo "Backend Type: $BACKEND_TYPE"
echo "Expected Port: $BACKEND_PORT"
echo ""

echo "How to Access:"
echo "=============="
echo ""
echo "1. Local access (on server):"
echo "   http://127.0.0.1:8000/admin/"
echo "   http://127.0.0.1:8000/api/"
echo ""
echo "2. External access (if port is open):"
echo "   http://$(hostname -I | awk '{print $1}'):8000/admin/"
echo "   http://$(hostname -I | awk '{print $1}'):8000/api/"
echo ""
echo "3. Via SSH tunnel (secure, from your local machine):"
echo "   ssh -L 8000:127.0.0.1:8000 banker@$(hostname -I | awk '{print $1}')"
echo "   Then access: http://localhost:8000/admin/"
echo ""

echo "Useful Commands:"
echo "================"
echo ""
echo "View Gunicorn logs:"
echo "  sudo journalctl -u gunicorn -f"
echo "  OR"
echo "  sudo journalctl -u gunicorn --since '1 hour ago'"
echo ""
echo "Restart Gunicorn:"
echo "  sudo systemctl restart gunicorn"
echo ""
echo "Check if port 8000 is accessible:"
echo "  curl http://127.0.0.1:8000/admin/"
echo ""
echo "Find process using port 8000:"
echo "  sudo lsof -i :8000"
echo "  OR"
echo "  sudo netstat -tlnp | grep :8000"
echo ""

