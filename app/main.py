import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import create_tables, get_db
from app.api.v1.router import api_router
from app.auth.security import get_current_user
from app.db.models import User

# Security scheme
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting up...")
    # Create database tables
    create_tables()
    print("Database tables created")
    
    yield
    
    # Shutdown
    print("Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Romanian Public Procurement Platform API",
    version="1.0.0",
    description="API for Romanian Public Procurement Platform with advanced risk detection",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Romanian Public Procurement Platform API",
        "status": "running",
        "version": "1.0.0",
        "docs_url": "/api/v1/docs"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Romanian Public Procurement Platform API",
        "version": "1.0.0"
    }

# Dashboard metrics endpoint (with authentication)
@app.get("/api/v1/dashboard/metrics")
async def get_dashboard_metrics(current_user: User = Depends(get_current_user)):
    return {
        "total_tenders": 1250,
        "total_value": 2500000000,
        "unique_authorities": 120,
        "unique_companies": 850,
        "average_risk_score": 35.2,
        "active_tenders": 45,
        "user_id": str(current_user.id)
    }

# Visualization endpoints (public access)
@app.get("/api/v1/visualizations/dashboard/metrics")
async def get_visualization_metrics():
    return {
        "total_tenders": 1250,
        "total_value": 2500000000,
        "unique_authorities": 120,
        "unique_companies": 850,
        "average_risk_score": 35.2,
        "active_tenders": 45,
        "monthly_growth": 8.3,
        "risk_trend": "decreasing"
    }

@app.get("/api/v1/charts/tender-volume")
async def get_tender_volume():
    return [
        {"month": "Ian", "count": 95, "value": 180000000},
        {"month": "Feb", "count": 88, "value": 165000000},
        {"month": "Mar", "count": 102, "value": 195000000},
        {"month": "Apr", "count": 110, "value": 210000000},
        {"month": "Mai", "count": 125, "value": 240000000}
    ]

@app.get("/api/v1/charts/geographic")
async def get_geographic_data():
    return [
        {"county": "Bucuresti", "count": 150, "total_value": 450000000},
        {"county": "Cluj", "count": 85, "total_value": 180000000},
        {"county": "Timis", "count": 72, "total_value": 160000000},
        {"county": "Constanta", "count": 65, "total_value": 140000000},
        {"county": "Iasi", "count": 58, "total_value": 125000000}
    ]

@app.get("/api/v1/charts/risk-distribution")
async def get_risk_distribution():
    return [
        {"risk_level": "low", "count": 750, "percentage": 60},
        {"risk_level": "medium", "count": 312, "percentage": 25},
        {"risk_level": "high", "count": 156, "percentage": 12.5},
        {"risk_level": "critical", "count": 32, "percentage": 2.5}
    ]

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail
            },
            "meta": {
                "timestamp": "2024-01-01T00:00:00Z",
                "request_id": "req_123"
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Internal server error"
            },
            "meta": {
                "timestamp": "2024-01-01T00:00:00Z",
                "request_id": "req_123"
            }
        }
    )

# Test endpoint
@app.get("/test")
async def test_endpoint():
    return {"message": "API is working!", "status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )