# Fix Git Pull Issue - Untracked Files Conflict

## Problem
Git won't pull because local untracked files (`.gitignore` and `db.sqlite3`) would be overwritten by the merge.

## Solution

Run these commands on your server:

```bash
cd ~/global-banker

# 1. Backup your local .gitignore (it has the Python cache ignores we added)
cp .gitignore .gitignore.local.backup

# 2. Temporarily move db.sqlite3 out of the way
mv db.sqlite3 db.sqlite3.backup

# 3. Remove the local .gitignore temporarily
rm .gitignore

# 4. Now pull (should work)
git pull

# 5. Restore your local .gitignore and merge with remote
cp .gitignore.local.backup .gitignore.local
# Merge the two .gitignore files - keep both sets of ignores
cat .gitignore .gitignore.local | sort -u > .gitignore.merged
mv .gitignore.merged .gitignore

# 6. Restore db.sqlite3 (it should be ignored now)
mv db.sqlite3.backup db.sqlite3

# 7. Verify .gitignore has db.sqlite3
grep -q "db.sqlite3" .gitignore || echo "db.sqlite3" >> .gitignore

# 8. Add and commit the merged .gitignore
git add .gitignore
git commit -m "Merge .gitignore with Python cache and db.sqlite3 ignores"

# 9. Push if needed
git push
```

## Simpler Solution (Recommended)

If you want to keep your local `.gitignore` and just ignore the remote version:

```bash
cd ~/global-banker

# 1. Backup local files
cp .gitignore .gitignore.backup
mv db.sqlite3 db.sqlite3.backup

# 2. Pull with strategy to prefer remote for .gitignore
git pull -X theirs

# 3. Restore your improved .gitignore
cp .gitignore.backup .gitignore

# 4. Make sure it has db.sqlite3
grep -q "db.sqlite3" .gitignore || echo -e "\ndb.sqlite3\ndb.sqlite3-journal" >> .gitignore

# 5. Restore db.sqlite3
mv db.sqlite3.backup db.sqlite3

# 6. Commit the updated .gitignore
git add .gitignore
git commit -m "Update .gitignore to ignore db.sqlite3 and Python cache files"
```

## Easiest Solution (If you don't care about remote .gitignore)

```bash
cd ~/global-banker

# 1. Remove local files temporarily
mv .gitignore .gitignore.backup
mv db.sqlite3 db.sqlite3.backup

# 2. Pull
git pull

# 3. Restore your .gitignore (the one with all the ignores we added)
cp .gitignore.backup .gitignore

# 4. Restore db.sqlite3
mv db.sqlite3.backup db.sqlite3

# 5. Ensure db.sqlite3 is in .gitignore
grep -q "db.sqlite3" .gitignore || echo -e "\ndb.sqlite3\ndb.sqlite3-journal" >> .gitignore

# 6. Commit
git add .gitignore
git commit -m "Update .gitignore with Python cache and db.sqlite3 ignores"
```

