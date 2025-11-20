# How to Restart Gunicorn Workers

## Method 1: Systemd Service (Most Common)

If Gunicorn is running as a systemd service (recommended for production):

```bash
# Restart the service
sudo systemctl restart global-banker

# Check status
sudo systemctl status global-banker

# View live logs
sudo journalctl -u global-banker -f

# View recent logs
sudo journalctl -u global-banker -n 50
```

**Note:** If `reload` fails with "Job type reload is not applicable", use `restart` instead.

---

## Method 2: Manual Process Restart

If Gunicorn is running as a manual process:

```bash
# Find Gunicorn processes
ps aux | grep gunicorn
# or
pgrep -f gunicorn

# Kill all Gunicorn processes
pkill gunicorn
# or forcefully
pkill -9 gunicorn

# Restart Gunicorn
cd /home/banker/global-banker
source ../venv/bin/activate  # Adjust path if different
gunicorn --workers 3 --bind 127.0.0.1:8000 --timeout 120 global_banker.wsgi:application &
```

---

## Method 3: Graceful Reload (No Downtime)

If you want to reload workers without dropping connections:

```bash
# Send HUP signal to reload workers
kill -HUP $(pgrep -f "gunicorn.*master")

# Or find master process manually
ps aux | grep gunicorn | grep master
kill -HUP <MASTER_PID>
```

This reloads workers gracefully without interrupting active connections.

---

## Method 4: Supervisor (If Using Supervisor)

```bash
sudo supervisorctl restart global-banker
# or
sudo supervisorctl reload global-banker
```

---

## Quick Diagnostic Commands

```bash
# Check if Gunicorn is listening on port 8000
sudo lsof -i :8000
# or
sudo ss -tlnp | grep 8000
# or
sudo netstat -tlnp | grep 8000

# Count Gunicorn processes (should be workers + 1 master)
ps aux | grep gunicorn | grep -v grep | wc -l

# Check systemd service status
sudo systemctl status global-banker

# Check if service is enabled on boot
sudo systemctl is-enabled global-banker
```

---

## Recommended Production Setup

For production, use systemd service:

1. **Service file location:** `/etc/systemd/system/global-banker.service`

2. **After making changes:**
   ```bash
   # Reload systemd configuration
   sudo systemctl daemon-reload
   
   # Restart service
   sudo systemctl restart global-banker
   ```

3. **Enable on boot:**
   ```bash
   sudo systemctl enable global-banker
   ```

---

## Troubleshooting

### Port Already in Use

If you get "Address already in use":

```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill the process
sudo kill -9 <PID>

# Or kill all Gunicorn processes
pkill -9 gunicorn
```

### Service Won't Start

```bash
# Check service logs
sudo journalctl -u global-banker -n 100

# Check service file syntax
sudo systemctl status global-banker

# Test service file
sudo systemd-analyze verify /etc/systemd/system/global-banker.service
```

### Workers Not Restarting

```bash
# Force kill and restart
sudo systemctl stop global-banker
pkill -9 gunicorn
sudo systemctl start global-banker
```

