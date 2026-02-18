# SignalMine Login Credentials (Demo)

The login system is now enabled. Use any of these credentials to access the chat:

## Demo Users

| Username | Password |
|----------|----------|
| `admin` | `password123` |
| `user` | `user123` |
| `demo` | `demo` |

## How It Works

1. **Login Modal** appears before accessing the chat interface
2. **Client-side storage**: Authentication token is stored in `localStorage`
3. **Token generation**: Server creates a unique token on successful login
4. **Persistence**: Token persists across page reloads until cleared
5. **Logout**: Call `logout()` in browser console to clear session

## For Production

The current implementation is demo-only. For production, you should:

- Use a proper database (PostgreSQL, MongoDB, etc.)
- Hash passwords with bcrypt or similar
- Implement token expiration (JWT with exp claim)
- Add proper session management
- Enforce HTTPS for all auth endpoints
- Use secure, HTTP-only cookies instead of localStorage for sensitive tokens

## Testing

Test the login flow:
```javascript
// In browser console:
logout()  // Clear session
// Page reloads and shows login modal again
```
