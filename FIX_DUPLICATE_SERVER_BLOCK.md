# Fix Duplicate Server Block Issue

## The Problem

You have **TWO server blocks**:

1. **`/etc/nginx/sites-available/default`** - Has `/hotseat/` block ✅
2. **Another server block** - Has `server_name 80.78.23.17` but NO `/hotseat/` block ❌

The second one is matching first because it has a specific `server_name`, so your `/hotseat/` block never gets used.

## Find the Duplicate Server Block

```bash
# Find all server blocks
sudo nginx -T | grep -B 5 -A 20 "server_name 80.78.23.17"

# Or find all server blocks
sudo nginx -T | grep -B 2 -A 15 "server {"

# Check all config files
sudo find /etc/nginx -name "*.conf" -o -name "*default*" | xargs grep -l "server_name 80.78.23.17"
```

## The Solution

You need to add `/hotseat/` to the server block with `server_name 80.78.23.17`, OR remove that server block and use the default one.

### Option 1: Add `/hotseat/` to Existing Server Block (Recommended)

Find the file containing `server_name 80.78.23.17`:

```bash
# Find which file has this server block
sudo grep -r "server_name 80.78.23.17" /etc/nginx/
```

Then edit that file and add the `/hotseat/` block:

```nginx
server {
    listen 80 default_server;
    server_name 80.78.23.17;

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;  # Remove /api/ from here
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ADD THIS: Hotseat -> Admin proxy
    location /hotseat/ {
        proxy_pass http://127.0.0.1:8000/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ADD THIS: Static files
    location /static/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # Frontend root
    root /home/banker/global_banker_front/dist;
    index index.html;

    # Frontend SPA (catch-all - MUST BE LAST)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### Option 2: Remove Duplicate and Use Default

If the duplicate server block is unnecessary:

```bash
# Find and remove/disable it
sudo find /etc/nginx -name "*.conf" | xargs grep -l "server_name 80.78.23.17"
# Then either delete the file or comment out the server block
```

## Quick Fix Steps

### 1. Find the Duplicate Server Block

```bash
# This will show you the full server block
sudo nginx -T | grep -B 10 -A 30 "server_name 80.78.23.17"
```

### 2. Find Which File It's In

```bash
sudo grep -r "server_name 80.78.23.17" /etc/nginx/
```

### 3. Edit That File

```bash
# Replace FILE_PATH with the file found above
sudo vim FILE_PATH
```

### 4. Add Missing Location Blocks

Add `/hotseat/` and `/static/` blocks BEFORE `location /`:

```nginx
    # Hotseat -> Admin proxy
    location /hotseat/ {
        proxy_pass http://127.0.0.1:8000/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
```

### 5. Fix `/api/` Proxy (Important!)

Your current `/api/` block has:
```nginx
proxy_pass http://127.0.0.1:8000/api/;  # ❌ Wrong - has /api/ at end
```

Should be:
```nginx
proxy_pass http://127.0.0.1:8000;  # ✅ Correct - no /api/ at end
```

The `/api/` in the URL path is automatically appended by Nginx.

### 6. Test and Reload

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Test Access

```bash
# Should return 302 (redirect to login)
curl -I http://localhost/hotseat/
```

## Complete Corrected Server Block

Here's what the server block with `server_name 80.78.23.17` should look like:

```nginx
server {
    listen 80 default_server;
    server_name 80.78.23.17;

    # Frontend root
    root /home/banker/global_banker_front/dist;
    index index.html;

    # Backend API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;  # Fixed: removed /api/
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

    # Django Admin (optional - ADD THIS)
    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (ADD THIS)
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

## Why This Happens

Nginx matches server blocks in this order:
1. Exact `server_name` match (e.g., `80.78.23.17`)
2. `default_server` (if no exact match)

Since you have a server block with `server_name 80.78.23.17`, it matches first and ignores the `default_server` block.

## Verification

After fixing, verify:

```bash
# Check active config
sudo nginx -T | grep -A 5 "location /hotseat"

# Should show your location block
# Test it
curl -I http://localhost/hotseat/
# Should return 302, not 404
```

