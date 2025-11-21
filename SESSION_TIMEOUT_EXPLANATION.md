# Session Timeout Configuration

## Current Settings

- **Access Token Lifetime**: 15 minutes
- **Refresh Token Lifetime**: 15 minutes

## How It Works

### Active Users (Stay Logged In)
- When a user makes an API call, the frontend automatically refreshes the access token if it's expired
- Each API call triggers a token refresh, which extends the session
- **Active users will stay logged in indefinitely** as long as they're using the site

### Inactive Users (Logged Out After 15 Minutes)
- If a user is inactive for 15 minutes (no API calls), the refresh token expires
- On the next API call, token refresh fails → user is logged out
- The frontend automatically redirects to login page

## Frontend Behavior

The frontend (`globe-gift-hub/src/lib/api.ts`) automatically handles token refresh:

1. **On 401 Error**: Frontend attempts to refresh the token
2. **If Refresh Succeeds**: Retries the original request with new token
3. **If Refresh Fails**: Clears session and user must log in again

## Testing

To test the inactivity timeout:

1. Log in to the application
2. Wait 15+ minutes without any activity
3. Try to make an API call (navigate to a page, click a button)
4. You should be automatically logged out and redirected to login

## Changing the Timeout

To change the inactivity timeout, update `SIMPLE_JWT` in `settings.py`:

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # Change this
    'REFRESH_TOKEN_LIFETIME': timedelta(minutes=15),  # Change this
    # ... other settings
}
```

**Note**: Both should be set to the same value for proper inactivity timeout behavior.

## Important Notes

- ⚠️ **Active users won't be logged out** - only inactive users
- ⚠️ **Token refresh happens automatically** - users don't notice it
- ⚠️ **After deployment**, existing tokens will still be valid until they expire
- ⚠️ **Users currently logged in** will need to log in again after their tokens expire

