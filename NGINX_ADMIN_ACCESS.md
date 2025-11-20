# Accessing Django Admin with Nginx Setup

## Current Setup

Your Nginx is configured to:
- Serve frontend static files from `/` (root)
- Proxy `/api/` requests to Gunicorn backend on port 8000

## Problem

Django admin is at `/admin/`, which is **NOT** under `/api/`, so Nginx won't proxy it to the backend. It will try to serve it as a static file and return 404.

## Solutions

### Option 1: Add Admin Route to Nginx (Recommended)

Add a location block in your Nginx config to proxy `/admin/` to the backend:

```nginx
server {
    listen 80;
    server_name 80.78.23.17;

    # Frontend static files
    root /home/banker/global_banker_front/dist;
    index index.html;

    # Backend API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django Admin (ADD THIS)
    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (CSS, JS for admin)
    location /static/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # Media files (if any)
    location /media/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # Frontend SPA (catch-all)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Important**: The `/admin/` and `/static/` blocks must come **BEFORE** the catch-all `location /` block.

### Option 2: Access Admin Directly on Port 8000

If Gunicorn is accessible directly:

```bash
# Access admin directly
http://80.78.23.17:8000/admin/
```

**Note**: This only works if:
- Port 8000 is open in firewall
- Gunicorn is binding to `0.0.0.0:8000` (not just `127.0.0.1:8000`)

### Option 3: Use SSH Tunnel (Secure)

If you want secure access without exposing port 8000:

```bash
# On your local machine
ssh -L 8000:127.0.0.1:8000 banker@80.78.23.17

# Then access in browser
http://localhost:8000/admin/
```

## Steps to Enable Admin Access

### 1. Update Nginx Configuration

```bash
# Edit Nginx config
sudo nano /etc/nginx/sites-available/default
# OR
sudo nano /etc/nginx/sites-available/your-site-name

# Add the /admin/ and /static/ location blocks (see above)
```

### 2. Test Nginx Configuration

```bash
sudo nginx -t
```

### 3. Reload Nginx

```bash
sudo systemctl reload nginx
```

### 4. Verify Admin is Accessible

```bash
# Should return HTML (not 404)
curl http://localhost/admin/
```

### 5. Access Admin in Browser

```
http://80.78.23.17/admin/
```

## Creating Admin User

If you don't have an admin user yet:

```bash
cd /home/banker/banksite-1/global-banker
source venv/bin/activate  # or: source env/bin/activate
python manage.py createsuperuser
```

## Admin URL Structure

- **Admin Login**: `http://80.78.23.17/admin/`
- **Admin Logout**: `http://80.78.23.17/admin/logout/`
- **Model Admin**: `http://80.78.23.17/admin/wallet/oxapaypayment/`
- **Model Admin**: `http://80.78.23.17/admin/wallet/topupintent/`

## Troubleshooting

### Issue: 404 on /admin/

**Cause**: Nginx not proxying `/admin/` to backend

**Fix**: Add `/admin/` location block to Nginx config (see Option 1)

### Issue: Admin loads but CSS/JS missing

**Cause**: Static files not being served

**Fix**: Add `/static/` location block to Nginx config

### Issue: CSRF token errors

**Cause**: Nginx not forwarding proper headers

**Fix**: Ensure `proxy_set_header Host $host;` is set

### Issue: Redirects to wrong URL

**Cause**: Django doesn't know the correct host

**Fix**: Set `ALLOWED_HOSTS` in Django settings:
```python
ALLOWED_HOSTS = ['80.78.23.17', 'your-domain.com']
```

## Quick Check Script

Run this to check if admin is accessible:

```bash
# Check if admin URL responds
curl -I http://localhost/admin/

# Should return 200 or 302 (redirect to login)
# If 404, Nginx is not proxying /admin/
```

