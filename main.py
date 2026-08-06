"""JARVIS — Root entry point. Run `python main.py` to start.

Usage:
  python main.py              # Interactive menu
  python main.py --text       # Text mode with streaming
  python main.py --voice      # Speech mode
  python main.py --api        # Start unified API server
  python main.py --debug      # Debug mode
  python main.py --health     # System health
  python main.py "query"      # One-shot query
"""
import os
import sys
import logging
import io

# Fix encoding issues on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

# Quiet noisy libraries so they don't pollute streaming output
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

from interface.cli import main

if __name__ == "__main__":
    main()
