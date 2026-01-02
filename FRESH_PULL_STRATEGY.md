# Fresh Pull Strategy - Clone to Different Directory

## Strategy
1. Clone the repo to a temporary directory
2. Copy the files to your main directory
3. Preserve your local files (db.sqlite3, .env, etc.)

## Steps

### Option 1: Fresh Clone and Copy (Recommended)

```bash
cd ~

# 1. Clone to a temporary directory
git clone <your-repo-url> global-banker-temp

# 2. Copy files to main directory (preserving your local files)
cd ~/global-banker

# Backup important local files first
cp .env .env.backup 2>/dev/null || true
cp db.sqlite3 db.sqlite3.backup 2>/dev/null || true

# Copy everything from temp directory (excluding .git to keep your history)
rsync -av --exclude='.git' --exclude='db.sqlite3' --exclude='.env' ~/global-banker-temp/ ~/global-banker/

# OR use cp (simpler but less control)
# cp -r ~/global-banker-temp/* ~/global-banker/
# cp -r ~/global-banker-temp/.* ~/global-banker/ 2>/dev/null || true

# 3. Restore your local files
cp .env.backup .env 2>/dev/null || true
cp db.sqlite3.backup db.sqlite3 2>/dev/null || true

# 4. Clean up temp directory
rm -rf ~/global-banker-temp

# 5. Verify .gitignore has db.sqlite3
grep -q "db.sqlite3" .gitignore || echo -e "\ndb.sqlite3\ndb.sqlite3-journal" >> .gitignore

# 6. Stage changes
git add .

# 7. Check status
git status
```

### Option 2: Pull to Temp and Merge Selectively

```bash
cd ~

# 1. Clone to temp directory
git clone <your-repo-url> global-banker-temp

# 2. Go to your main directory
cd ~/global-banker

# 3. Abort any current merge
git merge --abort 2>/dev/null || true

# 4. Reset to clean state (optional - be careful!)
# git reset --hard HEAD  # Only if you want to discard local changes

# 5. Add remote temp as a new remote
git remote add temp ../global-banker-temp

# 6. Fetch from temp
git fetch temp

# 7. Merge from temp (this should work since temp is clean)
git merge temp/main --no-edit

# 8. Remove temp remote
git remote remove temp

# 9. Clean up
rm -rf ~/global-banker-temp
```

### Option 3: Simple Copy with Git Reset (Easiest)

```bash
cd ~

# 1. Clone fresh copy
git clone <your-repo-url> global-banker-temp

# 2. Go to main directory
cd ~/global-banker

# 3. Backup important files
mkdir -p ~/backup-global-banker
cp .env ~/backup-global-banker/ 2>/dev/null || true
cp db.sqlite3 ~/backup-global-banker/ 2>/dev/null || true
cp .gitignore ~/backup-global-banker/ 2>/dev/null || true

# 4. Remove everything except .git
find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +

# 5. Copy everything from temp (except .git)
cp -r ~/global-banker-temp/. ~/global-banker/
rm -rf ~/global-banker/.git
mv ~/global-banker-temp/.git ~/global-banker/

# 6. Restore your important files
cp ~/backup-global-banker/.env . 2>/dev/null || true
cp ~/backup-global-banker/db.sqlite3 . 2>/dev/null || true

# 7. Update .gitignore
grep -q "db.sqlite3" .gitignore || echo -e "\ndb.sqlite3\ndb.sqlite3-journal" >> .gitignore
grep -q "__pycache__" .gitignore || echo -e "\n__pycache__/\n*.pyc" >> .gitignore

# 8. Clean up
rm -rf ~/global-banker-temp
rm -rf ~/backup-global-banker

# 9. Check status
git status
```

## Safest Approach (Recommended)

```bash
cd ~

# 1. Clone fresh copy
git clone <your-repo-url> global-banker-temp

# 2. Backup your important local files
cd ~/global-banker
mkdir -p ~/backup-$(date +%Y%m%d)
cp .env ~/backup-$(date +%Y%m%d)/ 2>/dev/null || true
cp db.sqlite3 ~/backup-$(date +%Y%m%d)/ 2>/dev/null || true

# 3. Stash or commit any uncommitted changes (optional)
git stash  # or git commit -am "Backup before fresh pull"

# 4. Reset your main directory to match remote
git fetch origin
git reset --hard origin/main  # or origin/master

# 5. Copy your important files back
cp ~/backup-$(date +%Y%m%d)/.env . 2>/dev/null || true
cp ~/backup-$(date +%Y%m%d)/db.sqlite3 . 2>/dev/null || true

# 6. Ensure .gitignore is correct
cat >> .gitignore << 'EOF'

# Python cache
__pycache__/
*.py[cod]
*$py.class

# Database
db.sqlite3
db.sqlite3-journal
EOF

# 7. Remove db.sqlite3 from tracking if it's tracked
git rm --cached db.sqlite3 2>/dev/null || true

# 8. Commit .gitignore update
git add .gitignore
git commit -m "Update .gitignore to ignore db.sqlite3 and Python cache"

# 9. Clean up temp directory
rm -rf ~/global-banker-temp

# 10. Verify
git status
```

## Important Files to Preserve

Make sure to backup and restore:
- `.env` - Environment variables
- `db.sqlite3` - Local database (if using SQLite)
- Any custom configuration files
- Any local scripts you've created

## After Copying

1. **Check git status:**
   ```bash
   git status
   ```

2. **Update .gitignore:**
   ```bash
   # Make sure these are in .gitignore
   echo "db.sqlite3" >> .gitignore
   echo "__pycache__/" >> .gitignore
   ```

3. **Remove tracked files that should be ignored:**
   ```bash
   git rm --cached db.sqlite3 2>/dev/null
   git rm -r --cached */__pycache__/ 2>/dev/null
   ```

4. **Commit changes:**
   ```bash
   git add .gitignore
   git commit -m "Update .gitignore"
   ```

## Advantages of This Approach

✅ Avoids merge conflicts completely
✅ Gets clean copy of remote code
✅ Preserves your local important files
✅ Fresh start with git history

## Disadvantages

⚠️ Loses any uncommitted local changes (unless you backup)
⚠️ Need to manually restore important files
⚠️ May need to re-run migrations or setup







