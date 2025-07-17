#!/usr/bin/env python3
"""
Development server startup script
"""

import os
import sys
import uvicorn
from app.core.config import settings

def main():
    """Run the development server"""
    print("🚀 Starting Romanian Public Procurement Platform API...")
    print(f"📊 Environment: {settings.ENVIRONMENT}")
    print(f"🐛 Debug Mode: {settings.DEBUG}")
    print(f"📝 API Documentation: http://localhost:8000{settings.API_V1_STR}/docs")
    print(f"🔍 ReDoc Documentation: http://localhost:8000{settings.API_V1_STR}/redoc")
    print("=" * 60)
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True,
            loop="asyncio"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()