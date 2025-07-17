from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os

# Import settings
from app.core.config import settings

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Romanian Public Procurement Platform API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.VERSION
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Romanian Public Procurement Platform API",
        "version": settings.VERSION,
        "docs_url": "/docs"
    }

# Basic API endpoints
@app.get("/api/v1/dashboard/metrics")
async def get_dashboard_metrics():
    return {
        "total_tenders": 1250,
        "total_value": 2500000000,
        "unique_authorities": 120,
        "unique_companies": 850,
        "average_risk_score": 35.2,
        "active_tenders": 45
    }

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
    return {
        "data": [
            {"month": "Ian", "count": 95, "value": 180000000},
            {"month": "Feb", "count": 88, "value": 165000000},
            {"month": "Mar", "count": 102, "value": 195000000},
            {"month": "Apr", "count": 110, "value": 210000000},
            {"month": "Mai", "count": 125, "value": 240000000}
        ]
    }

@app.get("/api/v1/charts/geographic")
async def get_geographic_data():
    return {
        "data": [
            {"county": "Bucuresti", "count": 150, "total_value": 450000000},
            {"county": "Cluj", "count": 85, "total_value": 180000000},
            {"county": "Timis", "count": 72, "total_value": 160000000},
            {"county": "Constanta", "count": 65, "total_value": 140000000},
            {"county": "Iasi", "count": 58, "total_value": 125000000}
        ]
    }

@app.get("/api/v1/charts/risk-distribution")
async def get_risk_distribution():
    return {
        "data": [
            {"risk_level": "low", "count": 750, "percentage": 60},
            {"risk_level": "medium", "count": 312, "percentage": 25},
            {"risk_level": "high", "count": 156, "percentage": 12.5},
            {"risk_level": "critical", "count": 32, "percentage": 2.5}
        ]
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"message": "Resource not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

# Run the app
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )