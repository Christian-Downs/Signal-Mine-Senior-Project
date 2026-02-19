"""
SignalMine LP Chat - Main Entry Point
Run this file to start the Flask server locally
"""

import sys
import os
import compileall
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


def compile_python_files():
    """Pre-compile all Python files to bytecode for faster startup"""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    print("Compiling Python files for faster execution...")
    start_time = time.time()
    
    # Compile all .py files in the project directory
    success = compileall.compile_dir(
        project_dir,
        quiet=1,  # Only print errors
        force=False,  # Only recompile if source changed
        workers=0  # Use all available CPUs
    )
    
    elapsed = (time.time() - start_time) * 1000
    if success:
        print(f"Compilation complete ({elapsed:.0f}ms)")
    else:
        print("Some files failed to compile (non-fatal)")


if __name__ == '__main__':
    # Compile Python files to bytecode first
    compile_python_files()
    
    from frontend import app, DB_AVAILABLE
    
    # Initialize database
    if DB_AVAILABLE:
        from api.database import init_database
        try:
            init_database()
            print("Database initialized successfully!")
        except Exception as e:
            print(f"Warning: Database initialization failed: {e}")
    
    port = int(os.environ.get("PORT", 5000))
    print(f"\n{'='*50}")
    print(f"SignalMine LP Chat")
    print(f"{'='*50}")
    print(f"Server running at: http://localhost:{port}")
    print(f"Database available: {DB_AVAILABLE}")
    print(f"{'='*50}\n")
    
    app.run(debug=True, port=port, host='0.0.0.0')
