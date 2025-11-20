# Fix Nginx Location Block Order

## The Problem

Your Nginx config has the location blocks in the **wrong order**:

```nginx
location / {                    # ← This matches FIRST (catches everything)
    try_files $uri $uri/ =404;
}

location /api/ {                # ← Never reached
    proxy_pass http://127.0.0.1:8000;
}

location /hotseat/ {            # ← Never reached
    proxy_pass http://127.0.0.1:8000/admin/;
}
```

**Nginx matches location blocks in order**, and `location /` matches **everything**, so `/api/` and `/hotseat/` never get a chance.

## The Fix

**Move `location /` to the END** (after all specific location blocks):

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;

    # Fix root directory to point to your frontend
    root /home/banker/global_banker_front/dist;
    index index.html;

    server_name _;

    # Backend API proxy (MUST BE BEFORE location /)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Hotseat -> Admin proxy (MUST BE BEFORE location /)
    location /hotseat/ {
        proxy_pass http://127.0.0.1:8000/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django Admin (optional - if you want /admin/ too)
    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (for admin CSS/JS) - MUST BE BEFORE location /
    location /static/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # Frontend SPA (catch-all - MUST BE LAST)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Key Changes

1. **Moved `location /` to the end** - So specific routes match first
2. **Changed `root`** from `/var/www/html` to `/home/banker/global_banker_front/dist`
3. **Changed `try_files`** from `=404` to `/index.html` (for React SPA routing)
4. **Added `/static/` block** - For admin CSS/JS
5. **Added `/admin/` block** - Optional, if you want direct access

## Why Port 8000 Doesn't Work

You mentioned `:8000/admin` returns "site can't be reached". This is because:

- **Gunicorn binds to**: `127.0.0.1:8000` (localhost only)
- **Not accessible externally**: Port 8000 is not exposed to the internet
- **Firewall**: Port 8000 is likely blocked

**This is correct for security** - you should access via Nginx on port 80, not directly on port 8000.

## Step-by-Step Fix

### 1. Edit Nginx Config
```bash
sudo vim /etc/nginx/sites-available/default
```

### 2. Replace the server block

Replace lines 932-1000 with the corrected version above.

**Important changes:**
- Line 952: Change `root /var/www/html;` to `root /home/banker/global_banker_front/dist;`
- Line 959: Move `location /` block to the END (after all other location blocks)
- Line 962: Change `try_files $uri $uri/ =404;` to `try_files $uri $uri/ /index.html;`

### 3. Test Configuration
```bash
sudo nginx -t
```

### 4. Reload Nginx
```bash
sudo systemctl reload nginx
```

### 5. Test Routes
```bash
# Test /hotseat/
curl -I http://localhost/hotseat/
# Should return 200 or 302 (not 404)

# Test /api/
curl -I http://localhost/api/wallet/networks/
# Should return 200 or 401 (not 404)

# Test frontend
curl -I http://localhost/
# Should return 200
```

### 6. Access in Browser
```
http://80.78.23.17/hotseat/  ✅ Should work now
http://80.78.23.17/admin/    ✅ Should work now (if you add the block)
http://80.78.23.17/api/...   ✅ Should work now
```

## Complete Corrected Config

Here's the complete corrected `server` block:

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;

    # Frontend static files
    root /home/banker/global_banker_front/dist;
    index index.html;

    server_name _;

    # Backend API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Hotseat -> Admin proxy
    location /hotseat/ {
        proxy_pass http://127.0.0.1:8000/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django Admin (optional)
    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (for admin CSS/JS)
    location /static/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # Frontend SPA (catch-all - MUST BE LAST)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Why This Fixes It

**Before (Wrong Order):**
```
Request: /hotseat/
  ↓
Nginx matches: location / (first match)
  ↓
Tries to serve: /var/www/html/hotseat/
  ↓
Not found → 404
```

**After (Correct Order):**
```
Request: /hotseat/
  ↓
Nginx checks: location /api/ (no match)
  ↓
Nginx checks: location /hotseat/ (MATCH!)
  ↓
Proxies to: http://127.0.0.1:8000/admin/
  ↓
Gunicorn responds → Success ✅
```

## Troubleshooting

### Still getting 404?

1. **Check location block order:**
   ```bash
   sudo nginx -T | grep -A 3 "location /"
   # /api/, /hotseat/, /static/ should come BEFORE /
   ```

2. **Check if frontend is built:**
   ```bash
   ls -la /home/banker/global_banker_front/dist/
   # Should contain index.html
   ```

3. **Check Nginx error logs:**
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

4. **Verify backend is running:**
   ```bash
   curl http://127.0.0.1:8000/admin/
   # Should work if Gunicorn is running
   ```

### Frontend not loading?

Make sure the frontend is built:
```bash
cd /home/banker/global_banker_front
npm install
npm run build
```

Then verify:
```bash
ls -la /home/banker/global_banker_front/dist/index.html
```

