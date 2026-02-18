#!/usr/bin/env python3
"""
Vercel cache warmer - ensures imports are loaded for faster cold starts
Run this as part of the build process
"""

import sys
import importlib

modules_to_warm = [
    "json",
    "os",
    "uuid",
    "secrets",
    "http.server",
    "pydantic",
    "openai",
]

def warm_cache():
    """Pre-import common modules to warm Python's import cache"""
    print("🔥 Warming import cache...")
    
    for module_name in modules_to_warm:
        try:
            importlib.import_module(module_name)
            print(f"  ✓ {module_name}")
        except ImportError as e:
            print(f"  ⚠ {module_name}: {e}")
    
    print("✨ Cache warming complete!")

if __name__ == "__main__":
    warm_cache()
