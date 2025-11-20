# Production Deployment Checklist

## After Pulling New Code

### 1. Backend Deployment Steps

```bash
# Navigate to backend directory
cd /home/banker/banksite-1/global-banker

# Activate virtual environment (if using one)
source venv/bin/activate  # or: source env/bin/activate

# Install/update Python dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Collect static files (if any new static files)
python manage.py collectstatic --noinput

# Restart Gunicorn service
sudo systemctl restart gunicorn

# Check Gunicorn status
sudo systemctl status gunicorn

# View recent logs
sudo journalctl -u gunicorn -n 50 --no-pager
```

### 2. Frontend Deployment Steps

```bash
# Navigate to frontend directory
cd /home/banker/global_banker_front  # or wherever your frontend is

# Install/update npm dependencies (if package.json changed)
npm install

# Build frontend
npm run build

# The dist/ folder should be served by Nginx
# Check that Nginx is pointing to the correct dist/ directory
```

### 3. Nginx Configuration

```bash
# Check Nginx configuration syntax
sudo nginx -t

# Reload Nginx (if config changed)
sudo systemctl reload nginx

# Restart Nginx (if reload doesn't work)
sudo systemctl restart nginx

# Check Nginx status
sudo systemctl status nginx
```

### 4. Verify Deployment

```bash
# Check if backend is running
curl http://localhost:8000/api/wallet/networks/ -H "Authorization: Bearer YOUR_TOKEN"

# Check if frontend is accessible
curl http://localhost/

# Check webhook endpoint (should return 405 Method Not Allowed for GET)
curl http://localhost/api/v2/wallet/oxapay/webhook/
```

### 5. Check Logs

```bash
# Backend logs (Gunicorn)
sudo journalctl -u gunicorn -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Django logs (if configured)
tail -f /home/banker/banksite-1/global-banker/logs/*.log
```

### 6. Environment Variables

Make sure these are set in your `.env` file or environment:

```bash
# Required for OXA Pay
OXAPAY_API_KEY=your_api_key_here
OXAPAY_CALLBACK_URL=https://your-domain.com/api/v2/wallet/oxapay/webhook/

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Django
SECRET_KEY=your_secret_key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,80.78.23.17

# Wallet (if using non-custodial)
DEFAULT_XPUB=your_xpub_here
WALLET_TEST_MODE=False
```

### 7. Webhook URL Configuration

**IMPORTANT**: Update `OXAPAY_CALLBACK_URL` to your production URL:

```bash
# Edit .env file
nano /home/banker/banksite-1/global-banker/.env

# Add or update:
OXAPAY_CALLBACK_URL=https://80.78.23.17/api/v2/wallet/oxapay/webhook/
# OR if you have a domain:
OXAPAY_CALLBACK_URL=https://your-domain.com/api/v2/wallet/oxapay/webhook/
```

### 8. Quick Deployment Script

Create a deployment script for future use:

```bash
#!/bin/bash
# deploy.sh

cd /home/banker/banksite-1/global-banker
source venv/bin/activate  # Adjust path if needed
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn

cd /home/banker/global_banker_front
npm install
npm run build

sudo systemctl reload nginx

echo "✅ Deployment complete!"
echo "Check logs: sudo journalctl -u gunicorn -n 50"
```

## Common Issues

### Issue: Gunicorn won't start
```bash
# Check for port conflicts
sudo lsof -i :8000
# Kill process if needed
sudo kill -9 <PID>

# Check Gunicorn config
cat /etc/systemd/system/gunicorn.service

# Restart service
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

### Issue: Frontend not updating
```bash
# Clear browser cache
# Or rebuild frontend
cd /home/banker/global_banker_front
rm -rf dist/
npm run build

# Check Nginx is serving correct directory
sudo nginx -T | grep root
```

### Issue: Database migrations fail
```bash
# Check database connection
python manage.py dbshell

# Check migration status
python manage.py showmigrations

# If needed, fake migrations (careful!)
# python manage.py migrate --fake
```

## Post-Deployment Verification

1. ✅ Backend API responds: `curl http://localhost:8000/api/wallet/networks/`
2. ✅ Frontend loads: Visit `http://80.78.23.17`
3. ✅ Webhook endpoint exists: `curl -X POST http://localhost:8000/api/v2/wallet/oxapay/webhook/`
4. ✅ Webhook status page accessible (admin only)
5. ✅ No errors in logs

