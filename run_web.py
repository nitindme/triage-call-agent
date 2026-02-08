#!/usr/bin/env python3
"""
AI Incident Triage Platform
Launch the web application.
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Change to project root for relative paths
os.chdir(project_root)

from web.app_v2 import app

if __name__ == "__main__":
    # Get port from environment (for cloud hosting) or default to 5050
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    
    print("\n" + "="*60)
    print("🚨 AI Incident Triage Platform")
    print("="*60)
    print(f"\n📌 Running on port: {port}")
    print("\n[Press Ctrl+C to stop]\n")
    
    app.run(host="0.0.0.0", debug=debug, port=port, threaded=True)
