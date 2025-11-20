# Proxy /hotseat/ to Django Admin

## Overview

Configure Nginx to proxy `/hotseat/` requests to Django's `/admin/` endpoint, so you can access the admin panel at `http://YOUR_SERVER_IP/hotseat/` instead of `/admin/`.

## Solution

Add a location block in Nginx that rewrites `/hotseat/` to `/admin/` when proxying to the backend.

## Nginx Configuration

Add this location block to your Nginx config:

```nginx
server {
    listen 80;
    server_name 80.78.23.17;

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

    # Hotseat -> Admin proxy (ADD THIS)
    location /hotseat/ {
        proxy_pass http://127.0.0.1:8000/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django Admin (optional - keep if you want both /admin/ and /hotseat/)
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

    # Frontend SPA (catch-all - MUST BE LAST)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Key Points

1. **Trailing slashes matter**: 
   - `location /hotseat/` (with trailing slash) matches `/hotseat/` and `/hotseat/anything`
   - `proxy_pass http://127.0.0.1:8000/admin/` (with trailing slash) rewrites the path

2. **URL Rewriting**:
   - Request: `http://YOUR_SERVER_IP/hotseat/` 
   - Proxied to: `http://127.0.0.1:8000/admin/`
   - Request: `http://YOUR_SERVER_IP/hotseat/login/`
   - Proxied to: `http://127.0.0.1:8000/admin/login/`

3. **Order matters**: More specific locations (`/hotseat/`, `/admin/`) must come BEFORE the catch-all `location /`.

## Implementation Steps

### 1. Edit Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/default
# OR
sudo nano /etc/nginx/nginx.conf
```

### 2. Add the /hotseat/ Location Block

Add the `/hotseat/` location block as shown above, placing it before the catch-all `location /` block.

### 3. Test Configuration

```bash
sudo nginx -t
```

Expected output:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 4. Reload Nginx

```bash
sudo systemctl reload nginx
```

### 5. Test the Route

```bash
# Test from server
curl -I http://localhost/hotseat/

# Should return 200 or 302 (redirect to login), not 404
```

### 6. Access in Browser

```
http://YOUR_SERVER_IP/hotseat/
```

## Alternative: Remove /admin/ Access

If you want to **only** allow access via `/hotseat/` and block `/admin/`, you can:

1. **Remove the `/admin/` location block** from Nginx config
2. Django will still have `/admin/` internally, but it won't be accessible from outside

Or keep both - users can access admin via either `/admin/` or `/hotseat/`.

## Troubleshooting

### Issue: 404 on /hotseat/

**Check:**
1. Location block order - `/hotseat/` must come before `location /`
2. Trailing slashes - both `location /hotseat/` and `proxy_pass .../admin/` should have trailing slashes
3. Nginx config syntax - run `sudo nginx -t`

### Issue: CSS/JS not loading

**Fix:** Ensure `/static/` location block is present (see config above)

### Issue: Redirects to /admin/ instead of /hotseat/

**Cause:** Django is generating absolute URLs with `/admin/`

**Fix:** You may need to configure Django's `FORCE_SCRIPT_NAME` or use a reverse proxy header, but for most cases, the Nginx rewrite should handle this transparently.

## Testing

```bash
# Test hotseat route
curl -I http://localhost/hotseat/
# Should return 200 or 302

# Test that it proxies to admin
curl -L http://localhost/hotseat/ | grep -i "django administration"
# Should find Django admin page content

# Test static files
curl -I http://localhost/static/admin/css/base.css
# Should return 200
```

