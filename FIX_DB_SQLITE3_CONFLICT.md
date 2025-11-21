# Fix db.sqlite3 Merge Conflict

## Problem
Git is trying to merge `db.sqlite3` which is a binary database file that shouldn't be in version control.

## Solution

Run these commands on your server:

```bash
cd ~/global-banker

# 1. Abort the current merge
git merge --abort

# 2. Remove db.sqlite3 from git tracking (keeps local file)
git rm --cached db.sqlite3

# 3. Make sure .gitignore includes db.sqlite3 (should already be there)
# If not, add it:
echo "db.sqlite3" >> .gitignore
echo "db.sqlite3-journal" >> .gitignore

# 4. Stage the .gitignore update
git add .gitignore

# 5. Commit the removal
git commit -m "Remove db.sqlite3 from git tracking"

# 6. Now pull again
git pull

# 7. If there's still a conflict, use theirs (remote version)
git pull --strategy-option=theirs

# OR if that doesn't work:
git checkout --theirs db.sqlite3
git add db.sqlite3
git rm db.sqlite3  # Remove from tracking
git commit -m "Remove db.sqlite3 from tracking"
```

## One-liner Solution

```bash
cd ~/global-banker && git merge --abort && git rm --cached db.sqlite3 && echo -e "\ndb.sqlite3\ndb.sqlite3-journal" >> .gitignore && git add .gitignore && git commit -m "Remove db.sqlite3 from tracking" && git pull
```

## Alternative: Force Use Remote Version

If you want to use the remote version and then remove it:

```bash
cd ~/global-banker

# Abort merge
git merge --abort

# Use remote version temporarily
git checkout origin/main -- db.sqlite3 2>/dev/null || git checkout origin/master -- db.sqlite3

# Remove from tracking
git rm --cached db.sqlite3

# Add to .gitignore
echo "db.sqlite3" >> .gitignore
echo "db.sqlite3-journal" >> .gitignore

# Commit
git add .gitignore
git commit -m "Remove db.sqlite3 from tracking"

# Pull
git pull
```

## Best Practice: Keep Your Local Database

Since `db.sqlite3` is a database file, you probably want to keep your local version:

```bash
cd ~/global-banker

# Abort merge
git merge --abort

# Remove from git tracking
git rm --cached db.sqlite3

# Ensure .gitignore has it
grep -q "db.sqlite3" .gitignore || echo "db.sqlite3" >> .gitignore
grep -q "db.sqlite3-journal" .gitignore || echo "db.sqlite3-journal" >> .gitignore

# Commit
git add .gitignore
git commit -m "Remove db.sqlite3 from git tracking"

# Pull (should work now)
git pull
```

