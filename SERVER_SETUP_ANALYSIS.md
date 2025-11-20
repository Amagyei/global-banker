# Server Setup Analysis - Frontend & Backend

## Summary from Terminal Output

Based on the terminal logs, here's what I found about your server setup:

## Backend Setup

### Current Status
- **Running**: ✅ Gunicorn is running (process ID 21425)
- **Port**: `127.0.0.1:8000` (localhost only, not exposed externally)
- **Workers**: 3 worker processes (PIDs: 21426, 21427, 21428)
- **Command**: `/home/banker/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 --timeout 120 global_banker.wsgi:application`
- **Status**: Active and responding (tested with `curl http://127.0.0.1:8000/admin/` - returns 302 redirect)

### Issues Found
1. **Systemd Service**: `global-banker.service` exists but has **bad unit file settings**
   - Error: "Assignment outside of section. Ignoring."
   - Lines 11, 12, 15, 16, 17, 20, 21, 22, 23, 24 have syntax errors
   - Service cannot be enabled/started via systemd
   - **Currently running manually** (not as a systemd service)

2. **Service File Location**: `/etc/systemd/system/global-banker.service`
   - Needs to be fixed to properly manage the service

### Backend Details
- **Location**: `/home/banker/global-banker`
- **Virtual Environment**: `/home/banker/venv`
- **Python Version**: 3.13.5
- **Django Version**: 5.2.7
- **Database**: PostgreSQL (`global_banker` database, user `bank_manager`)
- **Database URL**: `postgresql://bank_manager:gonethrougH17%40$%2F@localhost:5432/global_banker`
- **Static Files**: Collected to `/home/banker/global-banker/staticfiles`

### Environment Variables
- **Missing**: `.env` file not found
- **Warning**: `DEFAULT_XPUB not set - wallet address derivation will fail`
- **Settings**: `ALLOWED_HOSTS` includes `bvnkpro.com`, `www.bvnkpro.com`, `80.78.23.17`

## Frontend Setup

### Current Status
- **Location**: `/home/banker/global_banker_front`
- **Repository**: `github.com/amagyei/global_banker_front`
- **Build Output**: Should be in `/home/banker/global_banker_front/dist`
- **Status**: Unknown (not shown in logs)

### Nginx Configuration
- **Status**: ✅ Installed and running
- **Config Test**: ✅ Passes (`nginx -t` successful)
- **Config File**: `/etc/nginx/sites-available/default`
- **Issue**: Failed to reload at one point (line 375: "Job for nginx.service failed")
- **Root Directory**: Should be `/home/banker/global_banker_front/dist`

### Nginx Issues
- **Missing Proxy Blocks**: No `/api/`, `/hotseat/`, or `/static/` location blocks found
- **Current Config**: Only has default static file serving
- **Result**: `/admin/` returns 404, `/api/` might work by accident

## System Information

### Server Details
- **OS**: Debian GNU/Linux (6.12.43+deb13-amd64)
- **User**: `banker` (with sudo access)
- **IP Address**: `80.78.23.17`
- **Domain**: `bvnkpro.com`, `www.bvnkpro.com`

### Network
- **Backend Port**: 8000 (localhost only)
- **Frontend Port**: 80 (via Nginx)
- **SSH**: Port 22 (accessible)

## Current Problems

### 1. Systemd Service File Syntax Errors
```
/etc/systemd/system/global-banker.service has syntax errors:
- Lines 11, 12, 15, 16, 17, 20, 21, 22, 23, 24: "Assignment outside of section"
```

**Impact**: Cannot manage Gunicorn via systemd (restart, enable on boot, etc.)

### 2. Nginx Missing Proxy Configuration
- No `/api/` location block
- No `/hotseat/` location block  
- No `/static/` location block
- No `/admin/` location block

**Impact**: 
- `/admin/` returns 404
- `/api/` might work by accident (fallback behavior)
- Static files not properly served

### 3. Missing Environment Variables
- No `.env` file found
- `DEFAULT_XPUB` not set
- Wallet functionality will fail

### 4. Gunicorn Running Manually
- Not managed by systemd
- Will not auto-start on reboot
- No proper logging via journalctl

## What's Working

✅ **Backend is running** (Gunicorn on port 8000)
✅ **Database is connected** (PostgreSQL)
✅ **Nginx is installed** and config syntax is valid
✅ **Dependencies installed** (all Python packages)
✅ **Migrations applied** (no pending migrations)
✅ **Static files collected** (163 files)

## What Needs Fixing

### Priority 1: Fix Systemd Service File
```bash
# Check current service file
sudo cat /etc/systemd/system/global-banker.service

# Fix syntax errors (likely missing [Service] section header)
```

### Priority 2: Add Nginx Proxy Blocks
Add to `/etc/nginx/sites-available/default`:
- `/api/` → `http://127.0.0.1:8000`
- `/hotseat/` → `http://127.0.0.1:8000/admin/`
- `/static/` → `http://127.0.0.1:8000` or direct filesystem

### Priority 3: Create `.env` File
```bash
# Create .env file with required variables
cd /home/banker/global-banker
nano .env
# Add: DEFAULT_XPUB, SECRET_KEY, DATABASE_URL, etc.
```

### Priority 4: Frontend Build
```bash
# Check if frontend is built
cd /home/banker/global_banker_front
ls -la dist/

# If not built:
npm install
npm run build
```

## Access Information

### Backend Access
- **Local**: `http://127.0.0.1:8000/admin/` ✅ (works)
- **External**: `http://80.78.23.17:8000/admin/` ❌ (port not exposed)
- **Via Nginx**: `http://80.78.23.17/hotseat/` ❌ (not configured yet)

### Frontend Access
- **Via Nginx**: `http://80.78.23.17/` ❓ (unknown if built/deployed)

### API Access
- **Local**: `http://127.0.0.1:8000/api/` ✅ (works)
- **Via Nginx**: `http://80.78.23.17/api/` ❓ (might work by accident)

## Recommended Actions

1. **Fix systemd service file** to enable proper service management
2. **Add Nginx proxy blocks** for `/api/`, `/hotseat/`, `/static/`
3. **Create `.env` file** with all required environment variables
4. **Build frontend** if not already built
5. **Test all routes** after fixes

## Commands to Run

```bash
# 1. Check systemd service file
sudo cat /etc/systemd/system/global-banker.service

# 2. Check Nginx config
sudo cat /etc/nginx/sites-available/default

# 3. Check if frontend is built
ls -la /home/banker/global_banker_front/dist/

# 4. Check Gunicorn process
ps aux | grep gunicorn

# 5. Check what's listening on ports
sudo ss -tlnp | grep -E ":(80|8000)"
```

