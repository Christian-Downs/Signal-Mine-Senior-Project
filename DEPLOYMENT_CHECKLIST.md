# Vercel Deployment Checklist ✅

## Pre-Deployment (Local Testing)

- [x] Pre-compile Python files
  ```bash
  python3 build.py
  ```

- [x] Test with Vercel dev environment
  ```bash
  vercel dev
  ```

- [x] Verify login works
- [x] Verify chat API works
- [x] Verify models endpoint works
- [x] Check browser console for errors (F12)

## Commit to Git

```bash
git add .
git commit -m "Add Vercel performance optimizations

- Pre-compilation of Python bytecode
- Import cache warming
- Deployment filtering (.vercelignore)
- Optimized vercel.json configuration
- Expected improvements: 25-50% faster"

git push
```

## Vercel Deployment

### Option 1: Git Push (Recommended)
```bash
# Vercel automatically detects the buildCommand and runs optimizations
git push origin login_testing
# Then merge to main and push to trigger production deploy
```

### Option 2: Manual Deploy
```bash
vercel deploy --prod
```

## Post-Deployment (Verify in Production)

1. **Check Vercel Dashboard**
   - Navigate to your project
   - Verify all deployments succeeded
   - Check build logs for optimization output

2. **Test Production Endpoints**
   ```bash
   curl https://your-domain.vercel.app/api/health
   # Should return: {"status": "up"}
   ```

3. **Monitor Cold Start Times**
   - Check Vercel Analytics
   - Look for improvements in Lambda duration
   - Expected: <2s for first request

4. **Test Full Flow**
   - Open https://your-domain.vercel.app
   - Login with demo credentials
   - Send a chat prompt
   - Verify response time improved

## What the Build Does

When you push to Vercel or run `vercel deploy`:

1. Vercel sees `buildCommand` in vercel.json
2. Runs `bash vercel-build.sh`:
   - Pre-compiles all Python to bytecode
   - Warms import cache
   - Prepares optimized environment
3. Deploys optimized functions with:
   - Python 3.9 runtime
   - Pre-compiled .pyc files
   - Minimal dependencies
   - 50MB lambda size limit

## Performance Benchmarks

Monitor these metrics in Vercel Analytics:

| Metric | Target | Notes |
|--------|--------|-------|
| Cold Start | <2s | After deploy |
| Warm Start | <500ms | Subsequent requests |
| Deployment Size | <150MB | Total deployment |
| Build Time | <2min | Including pre-compilation |

## Troubleshooting

### Build Fails
- Check build logs in Vercel dashboard
- Ensure all Python files are syntactically correct
- Run `python3 build.py` locally to verify

### API Returns 502
- Check function logs in Vercel
- Verify OPENAI_API_KEY is set in Vercel environment
- Check `.vercelignore` isn't excluding needed files

### Slow Cold Starts
- Verify pre-compilation ran (check build logs)
- Check Python version is 3.9 or later
- Increase Lambda memory if budget allows

## Rollback Plan

If deployment issues occur:
1. Go to Vercel dashboard
2. Select previous stable deployment
3. Click "Promote to Production"

Or manually redeploy:
```bash
git revert HEAD  # Undo last commit
git push
```

---

✨ **You're all set!** The optimizations are automated and transparent.
No code changes needed - Vercel handles the build magic.
