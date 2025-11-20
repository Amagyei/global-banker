# Debug Nginx Proxy Not Working

## Current Config Status

Your Nginx config looks correct:
- ✅ `/api/` and `/hotseat/` blocks are BEFORE `location /`
- ✅ `location /` is at the END
- ✅ `root` points to `/home/banker/global_banker_front/dist`
- ✅ `try_files` uses `/index.html`

But you're still getting 404 from React frontend. Let's debug:

## Debugging Steps

### 1. Verify Frontend is Built

```bash
# Check if dist directory exists
ls -la /home/banker/global_banker_front/dist/

# If it doesn't exist or is empty, build it:
cd /home/banker/global_banker_front
npm install
npm run build
```

### 2. Test Location Block Matching

```bash
# Check what Nginx is actually using
sudo nginx -T | grep -A 10 "location /hotseat"

# Should show your location block
```

### 3. Test Backend Directly

```bash
# Verify backend is responding
curl -v http://127.0.0.1:8000/admin/
# Should return 302 (redirect to login), not 404
```

### 4. Test Through Nginx

```bash
# Test /hotseat/ through Nginx
curl -v http://localhost/hotseat/

# Check the response:
# - If 404: Location block not matching
# - If 302/200: Working! (might be React catching it)
# - If HTML from React: Frontend is intercepting
```

### 5. Check Nginx Error Logs

```bash
# Watch error logs in real-time
sudo tail -f /var/log/nginx/error.log

# Then try accessing /hotseat/ in browser
# See what errors appear
```

### 6. Check Access Logs

```bash
# See what requests Nginx is receiving
sudo tail -f /var/log/nginx/access.log

# Try accessing /hotseat/ and see the log entry
```

### 7. Verify Active Configuration

```bash
# Check if your config is actually being used
sudo nginx -T | grep -E "location /|root|proxy_pass" | head -20

# Should show your location blocks in correct order
```

## Common Issues

### Issue 1: Frontend Not Built

**Symptom**: `dist` directory doesn't exist or is empty

**Fix**:
```bash
cd /home/banker/global_banker_front
npm install
npm run build
```

### Issue 2: React Router Catching Routes

**Symptom**: Request reaches backend but React shows 404 page

**Cause**: React Router's catch-all route shows 404 for unknown routes

**Fix**: This is actually correct behavior - the request IS being proxied, but React is handling it. Try accessing `/hotseat/` directly (not through React).

### Issue 3: Browser Cache

**Symptom**: Old 404 page cached

**Fix**: Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

### Issue 4: Nginx Not Reloaded

**Symptom**: Changes not taking effect

**Fix**:
```bash
# Force reload
sudo systemctl reload nginx

# Or restart
sudo systemctl restart nginx

# Verify it's running
sudo systemctl status nginx
```

### Issue 5: Multiple Server Blocks

**Symptom**: Another server block is matching first

**Fix**:
```bash
# Check all server blocks
sudo nginx -T | grep -A 5 "server {"

# Check which one is default_server
sudo nginx -T | grep "default_server"
```

## Quick Test Script

Run this on your server to diagnose:

```bash
#!/bin/bash
echo "=== Testing Nginx Proxy ==="
echo ""

echo "1. Testing backend directly:"
curl -I http://127.0.0.1:8000/admin/ 2>&1 | head -3
echo ""

echo "2. Testing /hotseat/ through Nginx:"
curl -I http://localhost/hotseat/ 2>&1 | head -5
echo ""

echo "3. Testing /api/ through Nginx:"
curl -I http://localhost/api/wallet/networks/ 2>&1 | head -5
echo ""

echo "4. Checking frontend dist:"
ls -la /home/banker/global_banker_front/dist/ 2>&1 | head -5
echo ""

echo "5. Checking active Nginx config:"
sudo nginx -T 2>&1 | grep -A 3 "location /hotseat" | head -5
```

## Expected Behavior

### If Working Correctly:

```bash
# /hotseat/ should proxy to backend
curl -I http://localhost/hotseat/
# Should return: HTTP/1.1 302 Found
# Location: /admin/login/?next=/admin/
```

### If Not Working:

```bash
# /hotseat/ returns 404
curl -I http://localhost/hotseat/
# Returns: HTTP/1.1 404 Not Found
# (HTML from React 404 page)
```

## Most Likely Issue

Based on your description "returns a 404 via my react frontend", the request is likely:

1. **Reaching the frontend** (not being proxied)
2. **React Router showing 404** for unknown routes

**This means the location blocks aren't matching.** Possible causes:

1. **Nginx config not reloaded** - Run `sudo systemctl reload nginx`
2. **Another server block matching first** - Check for multiple server blocks
3. **Location block syntax issue** - Verify no typos in the config
4. **Frontend serving from wrong location** - Check if React dev server is running on port 80

## Solution

Try this test:

```bash
# On server, test if location block matches
curl -v http://localhost/hotseat/ 2>&1 | grep -E "HTTP|Location|Host"

# If you see "HTTP/1.1 302" or "HTTP/1.1 200" → Working!
# If you see "HTTP/1.1 404" → Location block not matching
```

If it's still 404, check:
1. Is the frontend built? (`ls /home/banker/global_banker_front/dist/`)
2. Is Nginx actually using this config? (`sudo nginx -T | grep hotseat`)
3. Are there other server blocks? (`sudo nginx -T | grep "server {"`)

