import sys
import os

# Add the backend directory to the path so we can import the app
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app

# This is required for Vercel's Python runtime to pick up the FastAPI app
# It should be named 'app'
# Alternatively, Vercel can find it if we export it as 'handler' or similar
# but 'app' is standard for FastAPI.
