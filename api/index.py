import os
import sys

# Ensure repository root is available on sys.path for backend module imports
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.api.main import app

# Vercel serverless function entrypoint
__all__ = ["app"]
