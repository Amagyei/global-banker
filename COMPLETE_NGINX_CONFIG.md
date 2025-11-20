# Complete Nginx Configuration

## Current Situation

Your Nginx config only has the default static file serving. You need to add:
1. Backend API proxy (`/api/`)
2. Hotseat proxy (`/hotseat/` → `/admin/`)
3. Static files proxy (`/static/`)

## Complete Nginx Configuration

Replace your current `server` block with this complete configuration:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name _;  # Or your domain/IP: 80.78.23.17

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
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }

    # Hotseat -> Admin proxy
    location /hotseat/ {
        proxy_pass http://127.0.0.1:8000/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }

    # Django Static Files (CSS, JS for admin)
    location /static/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # Django Media Files (if any)
    location /media/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # Frontend SPA (catch-all - MUST BE LAST)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Step-by-Step Instructions

### 1. Edit Nginx Config

```bash
sudo nano /etc/nginx/sites-available/default
```

### 2. Find the HTTP Server Block

Look for the `server` block that starts with:
```nginx
server {
    listen 80;
    ...
```

### 3. Replace the Entire Server Block

Replace everything inside the `server { ... }` block (from `listen 80;` to the closing `}`) with the configuration above.

**Important:** 
- Keep the `server {` opening and `}` closing
- Only replace the content inside
- Make sure `root` points to your frontend dist directory: `/home/banker/global_banker_front/dist`

### 4. Save and Exit

In nano:
- `Ctrl + O` to save
- `Enter` to confirm
- `Ctrl + X` to exit

### 5. Test Configuration

```bash
sudo nginx -t
```

Should show:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 6. Reload Nginx

```bash
sudo systemctl reload nginx
```

### 7. Verify Everything Works

```bash
# Test API
curl -I http://localhost/api/wallet/networks/
# Should return 200 or 401 (not 404)

# Test Hotseat
curl -I http://localhost/hotseat/
# Should return 200 or 302 (not 404)

# Test Frontend
curl -I http://localhost/
# Should return 200
```

## What Each Block Does

1. **`location /api/`**: Proxies all API requests to Django backend on port 8000
2. **`location /hotseat/`**: Rewrites `/hotseat/` to `/admin/` and proxies to Django
3. **`location /static/`**: Serves Django static files (admin CSS/JS)
4. **`location /media/`**: Serves Django media files (if any)
5. **`location /`**: Serves frontend React app (catch-all, must be last)

## Troubleshooting

### If nginx -t fails:

Check for:
- Missing semicolons (`;`)
- Unclosed braces `{ }`
- Incorrect paths

### If routes still return 404:

1. **Check backend is running:**
   ```bash
   curl http://127.0.0.1:8000/admin/
   # Should work if Gunicorn is running
   ```

2. **Check Nginx error logs:**
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

3. **Verify location block order:**
   ```bash
   sudo nginx -T | grep -A 3 "location /"
   # More specific locations should come first
   ```

### If static files don't load:

Make sure `/static/` location block is present and comes before the catch-all `location /`.

## Quick Reference

- **API Endpoints**: `http://YOUR_IP/api/...`
- **Admin Panel**: `http://YOUR_IP/hotseat/`
- **Frontend**: `http://YOUR_IP/`

