# Quick Reference - Server Commands

## 🚀 Most Common Commands

### Deploy New Code
```bash
# Backend
cd /home/banker/banksite-1/global-banker && git pull && source ../venv/bin/activate && pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput && sudo systemctl restart global-banker

# Frontend
cd /home/banker/global_banker_front && git pull && npm install && npm run build && sudo systemctl reload nginx
```

### Restart Services
```bash
# Backend
sudo systemctl restart global-banker

# Frontend (Nginx)
sudo systemctl reload nginx

# Both
sudo systemctl restart global-banker && sudo systemctl reload nginx
```

### View Logs
```bash
# Backend logs
sudo journalctl -u global-banker -f

# Frontend logs (Nginx)
sudo tail -f /var/log/nginx/error.log

# Recent backend errors
sudo journalctl -u global-banker -p err -n 50
```

### Check Status
```bash
# Service status
sudo systemctl status global-banker
sudo systemctl status nginx

# Test backend
curl http://localhost:8000/api/wallet/networks/

# Test frontend
curl http://localhost/
```

### Database
```bash
# Migrations
cd /home/banker/banksite-1/global-banker && source ../venv/bin/activate && python manage.py migrate

# Django shell
python manage.py shell
```

---

## 🔧 Troubleshooting

### Backend Down
```bash
sudo systemctl restart global-banker
sudo journalctl -u global-banker -n 50
```

### Frontend Down
```bash
sudo systemctl reload nginx
sudo tail -n 50 /var/log/nginx/error.log
```

### Port Conflicts
```bash
sudo lsof -i :8000
sudo fuser -k 8000/tcp
```

---

## 📍 File Locations

- **Backend**: `/home/banker/banksite-1/global-banker`
- **Frontend**: `/home/banker/global_banker_front`
- **Nginx Config**: `/etc/nginx/sites-available/default`
- **Gunicorn Service**: `/etc/systemd/system/global-banker.service`
- **Logs**: `sudo journalctl -u global-banker`
- **Environment**: `/home/banker/banksite-1/global-banker/.env`







