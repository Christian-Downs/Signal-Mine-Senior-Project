# Vercel Login Setup

## Overview
The login system is now configured to work with Vercel's serverless architecture.

## Files Created/Updated

### New File: `api/login.py`
- Serverless function for handling user authentication
- Accepts POST requests with `{ username, password }`
- Returns `{ token }` on success or `{ error }` on failure
- Handles CORS preflight requests

### Updated: `vercel.json`
- Added build config for `api/login.py`
- Added route mapping: `/api/login` → `/api/login.py`
- Login endpoint is now first in the routes list (for priority)

### Updated: `frontend.py`
- Removed Flask-based `/api/login` endpoint (no longer needed)
- Removed unused `secrets` import
- Removed demo user storage (moved to serverless function)
- Kept static file serving for local development

### Updated: `public/app.js`
- Login form already calls `/api/login` (no changes needed)
- Added console logging for debugging

## Demo Credentials
```
username: admin      password: password123
username: user       password: user123
username: demo       password: demo
```

## Testing with Vercel Dev

1. **Start Vercel dev environment:**
   ```bash
   vercel dev
   ```

2. **Test login:**
   - Open http://localhost:3000
   - Enter credentials from above
   - Should see chat interface after successful login

3. **Debug in browser console:**
   - Press F12 to open DevTools
   - Check Console tab for login flow logs

## Architecture

```
User fills login form
        ↓
app.js submits to /api/login
        ↓
Vercel routes to api/login.py (serverless)
        ↓
Validates credentials against DEMO_USERS
        ↓
Generates JWT-like token (secrets.token_urlsafe)
        ↓
Returns token to frontend
        ↓
Frontend stores in localStorage
        ↓
Shows chat interface
```

## Notes
- This is a demo implementation with in-memory token storage
- For production: use a real database, hash passwords, implement token expiration
- The token is stored in browser localStorage (not secure for production)
- Tokens are lost on serverless function restart (expected for serverless architecture)
