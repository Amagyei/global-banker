# Why /api/ Works But /admin/ Doesn't

## The Mystery

You're seeing:
- ✅ `/api/*` routes work (e.g., `/api/wallet/networks/`)
- ❌ `/admin/` returns 404

But your Nginx config doesn't have a `/api/` location block defined. So how is `/api/` working?

## Possible Explanations

### 1. Frontend API Client Uses Relative URLs (Most Likely)

Your frontend is probably making API calls using relative URLs like `/api/...`. When the browser makes these requests:

**For `/api/` requests:**
- Browser requests: `http://YOUR_IP/api/wallet/networks/`
- Nginx receives: `/api/wallet/networks/`
- Nginx's catch-all `location /` tries to serve it as a static file
- **BUT** - The frontend `dist` directory doesn't have `/api/` folder
- Nginx falls back to `try_files $uri $uri/ /index.html`
- The request might be getting handled by the frontend router or there's a default proxy somewhere

**Wait, that doesn't fully explain it...**

### 2. There's a Default Proxy in Main nginx.conf

Check if there's a default proxy configuration in the main Nginx config:

```bash
sudo cat /etc/nginx/nginx.conf | grep -A 10 "proxy_pass\|location"
```

There might be a default proxy configuration that catches `/api/` requests.

### 3. Vite Dev Server Proxy (If Testing Locally)

If you're testing from your local machine with Vite dev server running, the `vite.config.ts` has a proxy:

```typescript
proxy: {
  "/api": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
  },
}
```

This only works in development, not production.

### 4. Frontend Build Configuration

The production build might be configured to handle `/api/` differently, but this is unlikely without explicit configuration.

## Why /admin/ Doesn't Work

**The Real Reason:**

When you visit `/admin/` in the browser:

1. Browser requests: `http://YOUR_IP/admin/`
2. Nginx receives: `/admin/`
3. Nginx matches the catch-all `location /` block
4. Nginx tries: `try_files $uri $uri/ /index.html`
5. It looks for `/admin/` in the frontend `dist` directory
6. Doesn't find it (because it's a backend route, not a frontend file)
7. Falls back to `/index.html` (your React app)
8. React router doesn't have an `/admin/` route
9. Returns 404

**Why `/api/` might seem to work:**

1. If `/api/` requests are made by JavaScript (Axios/fetch), they might be:
   - Going through a different path
   - Being intercepted by service workers
   - Or there's actually a proxy config you haven't found yet

2. **OR** - The requests are actually failing, but you're not noticing because:
   - The frontend handles errors gracefully
   - You're testing from a different environment

## How to Verify

### Check if /api/ Actually Works

```bash
# Test from server
curl http://localhost/api/wallet/networks/

# If this returns JSON, there IS a proxy somewhere
# If this returns HTML or 404, there's NO proxy
```

### Check All Nginx Config Files

```bash
# Main config
sudo cat /etc/nginx/nginx.conf

# All site configs
sudo cat /etc/nginx/sites-available/*
sudo cat /etc/nginx/sites-enabled/*

# Check for any proxy_pass
sudo grep -r "proxy_pass" /etc/nginx/
```

### Check Active Nginx Configuration

```bash
# See what Nginx is actually using
sudo nginx -T | grep -A 5 "location"
```

## The Solution

Regardless of why `/api/` seems to work, you need to **explicitly define** both:

1. **`/api/` location block** - To ensure API requests are properly proxied
2. **`/hotseat/` location block** - To proxy admin requests

This ensures:
- ✅ Consistent behavior
- ✅ Proper error handling
- ✅ Correct headers
- ✅ No reliance on undefined behavior

## Recommended Configuration

Add these to your Nginx config:

```nginx
# Backend API proxy (explicit)
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
```

## Summary

- **`/api/` might work by accident** (fallback behavior, or hidden config)
- **`/admin/` doesn't work** because it's caught by the catch-all and served as a static file
- **Solution**: Explicitly define both location blocks for predictable behavior

