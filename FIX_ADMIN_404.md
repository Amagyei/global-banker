# Fix 404 Error for /admin/ Route

## Problem

- ✅ `/api/*` routes work (e.g., `/api/wallet/networks/`)
- ❌ `/admin/` returns 404

## Root Cause

Nginx is only configured to proxy `/api/` requests to the Django backend. When you visit `/admin/`, Nginx tries to serve it as a static file from the frontend `dist` directory, which doesn't exist, resulting in a 404.

## Solution

Add `/admin/` and `/static/` location blocks to your Nginx configuration to proxy them to the Django backend.

## Steps to Fix

### 1. SSH into your server
```bash
ssh banker@YOUR_SERVER_IP
```

### 2. Find your Nginx config file
```bash
# Usually one of these:
sudo nano /etc/nginx/sites-available/default
# OR
sudo nano /etc/nginx/nginx.conf
# OR
sudo nano /etc/nginx/sites-available/your-site-name
```

### 3. Add admin and static location blocks

Your current config probably looks like this:

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

    # Frontend SPA (catch-all)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Add these blocks BEFORE the catch-all `location /` block:**

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

    # Django Static Files (CSS, JS for admin) - ADD THIS
    location /static/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        # Optional: serve static files directly from Django's STATIC_ROOT
        # alias /home/banker/banksite-1/global-banker/staticfiles/;
    }

    # Django Media Files (if any) - OPTIONAL
    location /media/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        # Optional: serve media files directly
        # alias /home/banker/banksite-1/global-banker/media/;
    }

    # Frontend SPA (catch-all) - MUST BE LAST
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**⚠️ IMPORTANT:** The order matters! More specific locations (`/admin/`, `/static/`) must come BEFORE the catch-all `location /`.

### 4. Test Nginx configuration
```bash
sudo nginx -t
```

You should see:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 5. Reload Nginx
```bash
sudo systemctl reload nginx
```

### 6. Verify it works
```bash
# Test from server
curl -I http://localhost/admin/

# Should return 200 or 302 (redirect to login), not 404
```

### 7. Access in browser
```
http://YOUR_SERVER_IP/admin/
```

## Alternative: Serve Static Files Directly

If you want better performance, you can serve Django static files directly from the filesystem instead of proxying:

```nginx
# Collect static files first (on server)
cd /home/banker/banksite-1/global-banker
source venv/bin/activate
python manage.py collectstatic --noinput

# Then in Nginx config:
location /static/ {
    alias /home/banker/banksite-1/global-banker/staticfiles/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

## Quick Test Script

Run this on your server to verify the fix:

```bash
#!/bin/bash
echo "Testing /admin/ route..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/admin/)
if [ "$STATUS" = "200" ] || [ "$STATUS" = "302" ]; then
    echo "✅ /admin/ is working (HTTP $STATUS)"
else
    echo "❌ /admin/ returned HTTP $STATUS"
fi

echo ""
echo "Testing /api/ route..."
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/wallet/networks/)
if [ "$API_STATUS" = "200" ] || [ "$API_STATUS" = "401" ]; then
    echo "✅ /api/ is working (HTTP $API_STATUS)"
else
    echo "❌ /api/ returned HTTP $API_STATUS"
fi
```

## Troubleshooting

### Still getting 404?

1. **Check Nginx error logs:**
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

2. **Verify backend is running:**
   ```bash
   curl http://127.0.0.1:8000/admin/
   # Should work if backend is running
   ```

3. **Check location block order:**
   ```bash
   sudo nginx -T | grep -A 5 "location /"
   # /admin/ and /static/ should come BEFORE /
   ```

4. **Verify proxy_pass is correct:**
   ```bash
   # Check if Gunicorn is listening on 127.0.0.1:8000
   sudo lsof -i :8000
   ```

### Admin loads but CSS/JS missing?

- Add `/static/` location block (see above)
- Or run `python manage.py collectstatic` and serve from filesystem

### CSRF token errors?

- Ensure `proxy_set_header Host $host;` is set
- Check `ALLOWED_HOSTS` in Django settings includes your server IP/domain

