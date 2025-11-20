# Systemd Service Commands for global-banker

## The Issue

You tried:
```bash
sudo systemctl reload global-banker
```

But got:
```
Failed to reload global-banker.service: Job type reload is not applicable for unit global-banker.service.
```

## Why This Happens

Not all systemd services support `reload`. The `reload` command only works if the service is configured with `ExecReload=` in its service file.

For services that don't support reload, you need to use `restart` instead.

## Correct Commands

### Restart the Service
```bash
sudo systemctl restart global-banker
```

### Check Service Status
```bash
sudo systemctl status global-banker
```

### View Service Logs
```bash
# Live logs (follow)
sudo journalctl -u global-banker -f

# Last 50 lines
sudo journalctl -u global-banker -n 50

# Since specific time
sudo journalctl -u global-banker --since "1 hour ago"
```

### Stop the Service
```bash
sudo systemctl stop global-banker
```

### Start the Service
```bash
sudo systemctl start global-banker
```

### Enable Service (start on boot)
```bash
sudo systemctl enable global-banker
```

### Disable Service (don't start on boot)
```bash
sudo systemctl disable global-banker
```

## Difference: Reload vs Restart

- **`reload`**: Gracefully reloads configuration without stopping the service (if supported)
- **`restart`**: Stops and starts the service (always works)

For most Django/Gunicorn services, `restart` is the standard way to apply changes.

## Quick Reference

```bash
# Restart service (use this instead of reload)
sudo systemctl restart global-banker

# Check if it's running
sudo systemctl status global-banker

# View recent logs
sudo journalctl -u global-banker -n 20
```

