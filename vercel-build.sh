#!/bin/bash
# Vercel build script
# This runs before the deployment to pre-compile Python files and warm caches

set -e

echo "🚀 Starting Vercel build..."

# Pre-compile Python files for faster cold starts
echo "📦 Pre-compiling Python files..."
python3 build.py

# Warm import cache
echo "🔥 Warming import cache..."
python3 warm-cache.py

# Dependencies are handled by Vercel automatically
echo "📚 Python environment ready..."

echo "✅ Build complete!"
