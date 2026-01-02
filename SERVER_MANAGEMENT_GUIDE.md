# Server Management Guide

Complete guide for managing the production server (Njalla VPS).

---

## 🔐 **Server Access**

### SSH Connection
```bash
# Connect to server
ssh -i ~/.ssh/bvnkpro banker@80.78.23.17

# Or if configured in ~/.ssh/config
ssh njalla-vps
```

### Check Server Status
```bash
# System uptime and load
uptime

# Disk usage
df -h

# Memory usage
free -h

# Check running processes
ps aux | grep -E 'gunicorn|nginx|node'
```

---

## 🔧 **Backend Management (Django)**

### Navigate to Backend Directory
```bash
cd /home/banker/banksite-1/global-banker
```

### Virtual Environment
```bash
# Activate virtual environment
source ../venv/bin/activate
# or
source env/bin/activate

# Deactivate
deactivate
```

### Django Management Commands

#### Database Migrations
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations

# Rollback specific migration
python manage.py migrate <app_name> <migration_number>
```

#### Django Shell
```bash
# Interactive shell
python manage.py shell

# Run Python code directly
python manage.py shell -c "from accounts.models import User; print(User.objects.count())"
```

#### Static Files
```bash
# Collect static files
python manage.py collectstatic --noinput

# Clear collected static files
python manage.py collectstatic --clear --noinput
```

#### Create Superuser
```bash
python manage.py createsuperuser
```

#### Database Shell
```bash
# PostgreSQL shell
python manage.py dbshell

# SQLite shell (if using SQLite)
python manage.py dbshell
```

#### Check Django Configuration
```bash
# Check for common issues
python manage.py check

# Check deployment readiness
python manage.py check --deploy
```

---

## 🚀 **Gunicorn Service Management**

### Service Status
```bash
# Check service status
sudo systemctl status global-banker
# or
sudo systemctl status gunicorn

# Check if service is enabled on boot
sudo systemctl is-enabled global-banker
```

### Start/Stop/Restart
```bash
# Start service
sudo systemctl start global-banker

# Stop service
sudo systemctl stop global-banker

# Restart service (recommended)
sudo systemctl restart global-banker

# Reload service (if supported)
sudo systemctl reload global-banker
```

### View Logs
```bash
# View recent logs
sudo journalctl -u global-banker -n 50

# Follow logs in real-time
sudo journalctl -u global-banker -f

# View logs from specific time
sudo journalctl -u global-banker --since "1 hour ago"
sudo journalctl -u global-banker --since "2024-01-01 00:00:00"

# View logs with timestamps
sudo journalctl -u global-banker -n 100 --no-pager
```

### Manual Gunicorn (If Not Using Systemd)
```bash
# Find and kill Gunicorn processes
ps aux | grep gunicorn
pkill gunicorn
# or forcefully
pkill -9 gunicorn

# Start Gunicorn manually
cd /home/banker/banksite-1/global-banker
source ../venv/bin/activate
gunicorn --workers 3 --bind 127.0.0.1:8000 --timeout 120 global_banker.wsgi:application &

# Check if running
ps aux | grep gunicorn
```

### Check Port 8000
```bash
# Check what's using port 8000
sudo lsof -i :8000
# or
sudo ss -tlnp | grep 8000
# or
sudo netstat -tlnp | grep 8000

# Kill process on port 8000
sudo fuser -k 8000/tcp
```

---

## 🎨 **Frontend Management**

### Navigate to Frontend Directory
```bash
cd /home/banker/global_banker_front
# or
cd /home/banker/banksite-1/globe-gift-hub
```

### Build Frontend
```bash
# Install dependencies (if package.json changed)
npm install
# or (clean install)
npm ci

# Build for production
npm run build

# Build output goes to dist/ directory
```

### Development Server (Not for Production)
```bash
# Start Vite dev server
npm run dev

# Kill Vite server
pkill -f vite
# or
ps aux | grep vite | grep -v grep | awk '{print $2}' | xargs kill
```

### Check Frontend Files
```bash
# Check if dist/ exists
ls -la dist/

# Check dist/ size
du -sh dist/

# Remove old build
rm -rf dist/
```

---

## 🌐 **Nginx Management**

### Service Status
```bash
# Check Nginx status
sudo systemctl status nginx

# Check if Nginx is running
sudo systemctl is-active nginx
```

### Start/Stop/Restart
```bash
# Start Nginx
sudo systemctl start nginx

# Stop Nginx
sudo systemctl stop nginx

# Restart Nginx
sudo systemctl restart nginx

# Reload Nginx (preferred - no downtime)
sudo systemctl reload nginx
```

### Configuration
```bash
# Test Nginx configuration
sudo nginx -t

# View full Nginx configuration
sudo nginx -T

# View configuration files
sudo cat /etc/nginx/sites-available/default
sudo cat /etc/nginx/nginx.conf

# Find all Nginx config files
sudo find /etc/nginx -name "*.conf" -type f
```

### Logs
```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log

# View recent errors
sudo tail -n 100 /var/log/nginx/error.log

# Search for specific errors
sudo grep -i error /var/log/nginx/error.log | tail -20
```

### Check Nginx Ports
```bash
# Check what ports Nginx is listening on
sudo ss -tlnp | grep nginx
# or
sudo netstat -tlnp | grep nginx
```

---

## 🗄️ **Database Management**

### PostgreSQL (If Using)
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Connect to specific database
sudo -u postgres psql -d your_database_name

# List databases
sudo -u postgres psql -l

# Backup database
sudo -u postgres pg_dump your_database_name > backup_$(date +%Y%m%d).sql

# Restore database
sudo -u postgres psql your_database_name < backup_file.sql
```

### SQLite (If Using)
```bash
# Check database file
ls -lh db.sqlite3

# Backup SQLite database
cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d)

# Check database size
du -h db.sqlite3

# SQLite shell
sqlite3 db.sqlite3
```

### Django Database Commands
```bash
# Reset database (⚠️ DESTRUCTIVE - deletes all data)
python manage.py flush

# Show all tables
python manage.py dbshell
# Then: .tables (SQLite) or \dt (PostgreSQL)
```

---

## 📊 **Monitoring & Logs**

### System Logs
```bash
# System logs
sudo journalctl -xe

# Recent system errors
sudo journalctl -p err -b

# Service logs
sudo journalctl -u global-banker -f
sudo journalctl -u nginx -f
```

### Application Logs
```bash
# Django logs (if configured)
tail -f /home/banker/banksite-1/global-banker/logs/*.log

# Check log directory
ls -la /home/banker/banksite-1/global-banker/logs/
```

### Resource Monitoring
```bash
# CPU and memory usage
top
# or
htop

# Disk I/O
iostat -x 1

# Network connections
netstat -tuln
# or
ss -tuln
```

---

## 🔄 **Deployment Workflow**

### Full Deployment (Backend + Frontend)
```bash
# 1. Backend
cd /home/banker/banksite-1/global-banker
git pull origin main
source ../venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart global-banker

# 2. Frontend
cd /home/banker/global_banker_front
git pull origin main
npm install
npm run build
sudo systemctl reload nginx

# 3. Verify
curl http://localhost:8000/api/wallet/networks/
curl http://localhost/
```

### Quick Deployment Script
```bash
#!/bin/bash
# Save as deploy.sh

set -e

echo "🚀 Starting deployment..."

# Backend
echo "📦 Deploying backend..."
cd /home/banker/banksite-1/global-banker
git pull origin main
source ../venv/bin/activate
pip install -r requirements.txt --quiet
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart global-banker

# Frontend
echo "🎨 Deploying frontend..."
cd /home/banker/global_banker_front
git pull origin main
npm ci --silent
npm run build
sudo systemctl reload nginx

echo "✅ Deployment complete!"
```

---

## 🛠️ **Troubleshooting**

### Backend Not Responding
```bash
# Check if Gunicorn is running
ps aux | grep gunicorn

# Check port 8000
sudo lsof -i :8000

# Check Gunicorn logs
sudo journalctl -u global-banker -n 50

# Test backend directly
curl http://localhost:8000/api/wallet/networks/

# Restart service
sudo systemctl restart global-banker
```

### Frontend Not Loading
```bash
# Check Nginx status
sudo systemctl status nginx

# Check Nginx config
sudo nginx -t

# Check if dist/ exists
ls -la /home/banker/global_banker_front/dist/

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Rebuild frontend
cd /home/banker/global_banker_front
npm run build
sudo systemctl reload nginx
```

### Database Issues
```bash
# Check database connection
python manage.py dbshell

# Check migration status
python manage.py showmigrations

# Reset migrations (⚠️ DESTRUCTIVE)
python manage.py migrate <app_name> zero
python manage.py migrate <app_name>
```

### Permission Issues
```bash
# Fix file permissions
sudo chown -R banker:banker /home/banker/banksite-1/
sudo chmod -R 755 /home/banker/banksite-1/

# Fix Nginx permissions
sudo chown -R www-data:www-data /home/banker/global_banker_front/dist/
```

### Port Conflicts
```bash
# Find process using port
sudo lsof -i :8000
sudo lsof -i :80
sudo lsof -i :8080

# Kill process
sudo kill -9 <PID>
# or
sudo fuser -k 8000/tcp
```

---

## 🔍 **Quick Health Checks**

### Backend Health
```bash
# Test API endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/wallet/networks/

# Check Gunicorn workers
ps aux | grep gunicorn | wc -l

# Check service status
sudo systemctl status global-banker --no-pager
```

### Frontend Health
```bash
# Test frontend
curl http://localhost/

# Check Nginx
sudo systemctl status nginx --no-pager

# Check dist/ directory
ls -lh /home/banker/global_banker_front/dist/
```

### Database Health
```bash
# Test database connection
python manage.py check --database default

# Count records
python manage.py shell -c "from accounts.models import User; print(f'Users: {User.objects.count()}')"
```

---

## 📝 **Common Tasks**

### Update Environment Variables
```bash
# Edit .env file
nano /home/banker/banksite-1/global-banker/.env

# After editing, restart Gunicorn
sudo systemctl restart global-banker
```

### Clear Cache
```bash
# Django cache (if using Redis)
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Or restart Redis
sudo systemctl restart redis
```

### View Recent Errors
```bash
# Gunicorn errors
sudo journalctl -u global-banker -p err -n 50

# Nginx errors
sudo tail -n 50 /var/log/nginx/error.log

# System errors
sudo journalctl -p err -b | tail -50
```

### Check Disk Space
```bash
# Overall disk usage
df -h

# Directory sizes
du -sh /home/banker/*

# Find large files
find /home/banker -type f -size +100M -exec ls -lh {} \;
```

### Check Memory Usage
```bash
# Current memory
free -h

# Process memory usage
ps aux --sort=-%mem | head -10
```

---

## 🚨 **Emergency Procedures**

### Complete Service Restart
```bash
# Stop all services
sudo systemctl stop global-banker
sudo systemctl stop nginx

# Start services
sudo systemctl start global-banker
sudo systemctl start nginx

# Check status
sudo systemctl status global-banker
sudo systemctl status nginx
```

### Rollback Deployment
```bash
# Backend - revert to previous commit
cd /home/banker/banksite-1/global-banker
git log --oneline -10  # Find previous commit
git checkout <previous_commit_hash>
source ../venv/bin/activate
python manage.py migrate  # May need to rollback migrations
sudo systemctl restart global-banker

# Frontend - revert to previous commit
cd /home/banker/global_banker_front
git log --oneline -10
git checkout <previous_commit_hash>
npm install
npm run build
sudo systemctl reload nginx
```

### Database Backup
```bash
# PostgreSQL backup
sudo -u postgres pg_dump your_database > backup_$(date +%Y%m%d_%H%M%S).sql

# SQLite backup
cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d_%H%M%S)

# Restore from backup
sudo -u postgres psql your_database < backup_file.sql
```

---

## 📋 **Useful One-Liners**

```bash
# Quick status check
sudo systemctl status global-banker nginx --no-pager

# View all service logs
sudo journalctl -u global-banker -u nginx -n 20

# Check all listening ports
sudo ss -tlnp

# Find all Python processes
ps aux | grep python

# Check Git status
cd /home/banker/banksite-1/global-banker && git status
cd /home/banker/global_banker_front && git status

# Quick deployment (after git pull)
cd /home/banker/banksite-1/global-banker && source ../venv/bin/activate && python manage.py migrate && sudo systemctl restart global-banker && cd /home/banker/global_banker_front && npm run build && sudo systemctl reload nginx
```

---

## 🔐 **Security Commands**

### Check SSH Access
```bash
# View SSH connections
sudo ss -tnp | grep :22

# Check SSH config
sudo cat /etc/ssh/sshd_config | grep -E "PasswordAuthentication|PubkeyAuthentication"
```

### Firewall (UFW)
```bash
# Check firewall status
sudo ufw status

# Allow/deny ports
sudo ufw allow 80
sudo ufw allow 443
sudo ufw deny 8000  # Don't expose Gunicorn directly
```

---

## 📚 **Additional Resources**

- **Django Docs**: https://docs.djangoproject.com/
- **Gunicorn Docs**: https://docs.gunicorn.org/
- **Nginx Docs**: https://nginx.org/en/docs/
- **Systemd Docs**: https://www.freedesktop.org/software/systemd/man/

---

## ⚠️ **Important Notes**

1. **Always test configuration** before restarting services:
   - `sudo nginx -t` for Nginx
   - `python manage.py check` for Django

2. **Use `reload` instead of `restart`** when possible (no downtime):
   - `sudo systemctl reload nginx`
   - `sudo systemctl reload global-banker` (if supported)

3. **Backup before migrations**:
   - Always backup database before running migrations
   - Test migrations on staging first

4. **Monitor logs** after changes:
   - Check logs immediately after deployment
   - Watch for errors in the first few minutes

5. **Document changes**:
   - Keep track of configuration changes
   - Note any manual database changes







