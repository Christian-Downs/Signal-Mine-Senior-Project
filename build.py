#!/usr/bin/env python3
"""
Pre-compilation script for Vercel deployment
Compiles all Python files to .pyc bytecode for faster execution
"""

import py_compile
import os
import sys
from pathlib import Path

def compile_python_files():
    """Compile all Python files to bytecode"""
    
    dirs_to_compile = [
        "api",
        ".",
    ]
    
    compiled_count = 0
    failed_count = 0
    
    print("🔨 Pre-compiling Python files for Vercel...")
    print("-" * 50)
    
    for directory in dirs_to_compile:
        py_files = Path(directory).glob("*.py")
        
        for py_file in py_files:
            if py_file.name.startswith("test_"):
                continue  # Skip test files
            
            try:
                # Compile to __pycache__
                py_compile.compile(str(py_file), doraise=True)
                print(f"✅ {py_file}")
                compiled_count += 1
            except py_compile.PyCompileError as e:
                print(f"❌ {py_file}: {e}")
                failed_count += 1
    
    print("-" * 50)
    print(f"Compiled: {compiled_count} files")
    if failed_count > 0:
        print(f"Failed: {failed_count} files")
        return False
    
    print("✨ Pre-compilation complete!")
    return True

if __name__ == "__main__":
    success = compile_python_files()
    sys.exit(0 if success else 1)
