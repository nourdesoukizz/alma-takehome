#!/usr/bin/env python3
"""
Local development server for Document Form Filler
Runs with visible browser for form filling
"""

import os
import sys
import uvicorn
from pathlib import Path

# Set environment for local development
os.environ["ENVIRONMENT"] = "local"
os.environ["FORM_FILLING_MODE"] = "visible"  # visible browser mode

def main():
    """Run the application locally"""
    
    print("\n" + "="*60)
    print("🚀 Starting Document Form Filler (Local Mode)")
    print("="*60)
    print("\n📍 Server will run at: http://localhost:8000")
    print("🌐 Form filling will open in a visible browser window")
    print("📂 Upload documents to see the form being filled automatically\n")
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment may not be activated")
        print("   Run: source venv/bin/activate\n")
    
    # Check for required directories
    Path("uploads").mkdir(exist_ok=True)
    Path("static").mkdir(exist_ok=True)
    
    try:
        # Run the FastAPI application
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down server...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()