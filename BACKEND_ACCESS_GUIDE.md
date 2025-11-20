# Backend Access Guide

## Quick Commands

### Check Backend Status
```bash
# Run the diagnostic script
./CHECK_BACKEND_STATUS.sh

# Or manually check:
ps aux | grep -E "gunicorn|uvicorn|manage.py" | grep -v grep
sudo systemctl status gunicorn
```

### Access Backend

#### Option 1: Direct Access (if port 8000 is open)
```bash
# From server
curl http://127.0.0.1:8000/admin/

# From browser (replace with your server IP)
http://YOUR_SERVER_IP:8000/admin/
```

#### Option 2: SSH Tunnel (Recommended - Secure)
```bash
# On your local machine
ssh -L 8000:127.0.0.1:8000 banker@YOUR_SERVER_IP

# Then in browser
http://localhost:8000/admin/
```

#### Option 3: Via Nginx (if configured)
```bash
# If Nginx proxies /admin/ to backend
http://YOUR_SERVER_IP/admin/
```

## Common Backend Setups

### 1. Gunicorn (Production)
```bash
# Check status
sudo systemctl status gunicorn

# View logs
sudo journalctl -u gunicorn -f

# Restart
sudo systemctl restart gunicorn

# Service file location
/etc/systemd/system/gunicorn.service
```

### 2. Uvicorn (ASGI)
```bash
# Check if running
ps aux | grep uvicorn

# Usually started manually or via supervisor
```

### 3. Django Dev Server
```bash
# Check if running
ps aux | grep "manage.py runserver"

# Usually in screen/tmux session
screen -ls
tmux ls
```

## Finding What's Running

### Check Port 8000
```bash
# Method 1: lsof
sudo lsof -i :8000

# Method 2: netstat
sudo netstat -tlnp | grep :8000

# Method 3: ss
sudo ss -tlnp | grep :8000
```

### Check All Python Processes
```bash
ps aux | grep python | grep -v grep
```

### Check Systemd Services
```bash
# List all services
systemctl list-units --type=service | grep -E "gunicorn|django"

# Check specific service
systemctl status gunicorn
```

## Viewing Logs

### Gunicorn (systemd)
```bash
# Live logs
sudo journalctl -u gunicorn -f

# Last 100 lines
sudo journalctl -u gunicorn -n 100

# Since specific time
sudo journalctl -u gunicorn --since "1 hour ago"
```

### Manual Process
```bash
# If running in screen
screen -r

# If running in tmux
tmux attach

# If running in background, check nohup.out
find . -name "nohup.out" -type f
```

## Starting Backend

### Gunicorn (Recommended for Production)
```bash
cd /home/banker/banksite-1/global-banker
source venv/bin/activate  # or: source env/bin/activate

# Start manually
gunicorn global_banker.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -

# Or as systemd service
sudo systemctl start gunicorn
```

### Uvicorn (for ASGI)
```bash
cd /home/banker/banksite-1/global-banker
source venv/bin/activate

uvicorn global_banker.asgi:application \
    --host 127.0.0.1 \
    --port 8000
```

### Django Dev Server (Development Only)
```bash
cd /home/banker/banksite-1/global-banker
source venv/bin/activate

python manage.py runserver 127.0.0.1:8000
```

## Testing Backend

### Test Admin Access
```bash
curl -I http://127.0.0.1:8000/admin/
# Should return 200 or 302 (redirect to login)
```

### Test API Access
```bash
curl http://127.0.0.1:8000/api/wallet/networks/
# Should return JSON
```

### Test Health
```bash
curl http://127.0.0.1:8000/admin/
# Should return HTML (login page)
```

## Troubleshooting

### Backend Not Responding
1. Check if process is running:
   ```bash
   ps aux | grep -E "gunicorn|uvicorn|manage.py"
   ```

2. Check if port is listening:
   ```bash
   sudo lsof -i :8000
   ```

3. Check firewall:
   ```bash
   sudo ufw status
   sudo iptables -L -n
   ```

4. Check logs:
   ```bash
   sudo journalctl -u gunicorn -n 50
   ```

### Permission Errors
```bash
# Check file permissions
ls -la /home/banker/banksite-1/global-banker/

# Check if user can access
whoami
```

### Port Already in Use
```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill process (if needed)
sudo kill -9 <PID>
```

## Creating Systemd Service

If Gunicorn is not running as a service, create one:

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

Add:
```ini
[Unit]
Description=gunicorn daemon for Django
After=network.target

[Service]
User=banker
Group=banker
WorkingDirectory=/home/banker/banksite-1/global-banker
ExecStart=/home/banker/banksite-1/global-banker/venv/bin/gunicorn \
    --access-logfile - \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    global_banker.wsgi:application

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
```

