#!/usr/bin/env python3
"""
Wrapper script to run WebGL tests with proper virtual environment handling.
"""

import os
import sys
import subprocess
from pathlib import Path


def get_venv_python():
    """Get the path to the virtual environment Python executable."""
    venv_path = Path("venv")
    
    if os.name == 'nt':  # Windows
        return str(venv_path / "Scripts" / "python.exe")
    else:  # Unix/Linux/macOS
        return str(venv_path / "bin" / "python")


def main():
    """Main wrapper function."""
    venv_python = get_venv_python()
    
    # Check if virtual environment exists and has the required packages
    if Path(venv_python).exists():
        print("🐍 Using virtual environment...")
        python_cmd = venv_python
    else:
        print("⚠️  Virtual environment not found, using system Python...")
        print("💡 Run 'python setup_test_runner.py' first to set up the environment.")
        python_cmd = sys.executable
    
    # Build the command with all arguments passed through
    cmd = [python_cmd, "webgl_test_runner.py"] + sys.argv[1:]
    
    try:
        # Run the test runner with the same arguments
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n🛑 Test run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
