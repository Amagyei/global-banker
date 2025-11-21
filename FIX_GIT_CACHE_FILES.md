# Fix Git Cache Files Issue

## Problem
Git is complaining about `__pycache__` files that are already tracked, even though they're in `.gitignore`.

## Solution

Run these commands on your server:

```bash
cd ~/global-banker

# 1. Remove all __pycache__ directories from git tracking (but keep them locally)
find . -type d -name __pycache__ -exec git rm -r --cached {} + 2>/dev/null || true

# 2. Remove all .pyc files from git tracking
find . -name "*.pyc" -exec git rm --cached {} + 2>/dev/null || true

# 3. Remove all .pyo files from git tracking
find . -name "*.pyo" -exec git rm --cached {} + 2>/dev/null || true

# 4. Stage the .gitignore update
git add .gitignore

# 5. Commit the changes
git commit -m "Remove __pycache__ files from git tracking and update .gitignore"

# 6. Now you can pull
git pull
```

## Alternative: Quick Fix (if you don't want to commit)

If you just want to pull without committing:

```bash
cd ~/global-banker

# Stash the cache files (they'll be recreated automatically)
git stash push -m "Stash cache files" -- __pycache__/

# Or force remove from index
git rm -r --cached */__pycache__/ 2>/dev/null || true
git rm --cached **/*.pyc 2>/dev/null || true

# Now pull
git pull
```

## Verify .gitignore is working

After fixing, verify that new cache files won't be tracked:

```bash
# Create a test cache file
touch test/__pycache__/test.pyc

# Check git status - it should NOT show the cache file
git status

# If it shows, .gitignore isn't working properly
```

## One-liner Solution

```bash
cd ~/global-banker && find . -type d -name __pycache__ -exec git rm -r --cached {} + 2>/dev/null; find . -name "*.pyc" -exec git rm --cached {} + 2>/dev/null; git add .gitignore && git commit -m "Remove cache files from tracking" && git pull
```

