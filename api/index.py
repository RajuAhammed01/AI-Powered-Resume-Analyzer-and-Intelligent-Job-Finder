import os
import sys

# Ensure root workspace directory is in Python module search path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from run import app

# Vercel WSGI callable
app = app

