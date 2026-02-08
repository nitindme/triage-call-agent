"""
Main Flask app entry point for Render/Vercel deployment.
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.chdir(project_root)

# Use v3 with improved delays and LLaMA integration
from web.app_v3 import app

# Gunicorn/Vercel looks for 'app' variable
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
