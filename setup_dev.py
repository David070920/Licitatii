#!/usr/bin/env python3
"""
Development setup script
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def setup_environment():
    """Setup development environment"""
    print("🚀 Setting up Romanian Procurement Platform Development Environment")
    
    # Check if we're in a virtual environment
    if sys.prefix == sys.base_prefix:
        print("⚠️  Warning: Not in a virtual environment")
        print("It's recommended to create a virtual environment first:")
        print("python -m venv venv")
        print("source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
        print("")
        
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Exiting...")
            return False
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        print("\n📝 Creating .env file...")
        with open(".env", "w") as f:
            f.write("""# Romanian Procurement Platform Configuration

# Database Configuration
DATABASE_URL=postgresql://procurement:password@localhost:5432/procurement_db

# Security Configuration
SECRET_KEY=your-secret-key-change-this-in-production-super-secret-key-12345
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000"]

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379

# External APIs
SICAP_API_URL=https://sicap.gov.ro/api
ANRMAP_API_URL=https://anrmap.gov.ro/api

# Application Settings
APP_NAME=Romanian Public Procurement Platform
DEBUG=true
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# Pagination
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
""")
        print("✓ Created .env file with default configuration")
        print("⚠️  Remember to update the database URL and secret key!")
    else:
        print("✓ .env file already exists")
    
    # Initialize Alembic if not already done
    if not Path("alembic/versions").exists():
        print("\n🗄️  Initializing database migrations...")
        if not run_command("alembic init alembic", "Initializing Alembic"):
            # If alembic is already initialized, that's ok
            pass
        
        # Create versions directory if it doesn't exist
        Path("alembic/versions").mkdir(exist_ok=True)
    
    # Generate initial migration
    if not run_command("alembic revision --autogenerate -m 'Initial migration'", "Creating initial migration"):
        print("⚠️  Could not create initial migration - this is normal if database is not set up yet")
    
    print("\n🎉 Development environment setup completed!")
    print("\n📋 Next steps:")
    print("1. Set up PostgreSQL database:")
    print("   - Install PostgreSQL")
    print("   - Create database: procurement_db")
    print("   - Create user: procurement with password")
    print("   - Update DATABASE_URL in .env file")
    print("")
    print("2. Set up Redis (optional):")
    print("   - Install Redis")
    print("   - Start Redis server")
    print("   - Update REDIS_URL in .env file")
    print("")
    print("3. Initialize database:")
    print("   python init_db.py")
    print("")
    print("4. Run the application:")
    print("   uvicorn app.main:app --reload")
    print("")
    print("5. Access the API documentation:")
    print("   http://localhost:8000/api/v1/docs")
    print("")
    print("6. Default admin credentials:")
    print("   Email: admin@licitatii.ro")
    print("   Password: admin123")
    
    return True

def check_prerequisites():
    """Check if required software is installed"""
    print("🔍 Checking prerequisites...")
    
    prerequisites = [
        ("python", "Python 3.8+"),
        ("pip", "pip package manager"),
    ]
    
    missing = []
    for cmd, desc in prerequisites:
        try:
            subprocess.run([cmd, "--version"], capture_output=True, check=True)
            print(f"✓ {desc} is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"✗ {desc} is not installed")
            missing.append(desc)
    
    if missing:
        print(f"\n❌ Missing prerequisites: {', '.join(missing)}")
        return False
    
    return True

if __name__ == "__main__":
    if check_prerequisites():
        setup_environment()
    else:
        print("Please install missing prerequisites and try again.")
        sys.exit(1)