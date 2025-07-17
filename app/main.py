import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Create FastAPI app
app = FastAPI(
    title="Romanian Public Procurement Platform API",
    version="1.0.0",
    description="API for Romanian Public Procurement Platform",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Romanian Public Procurement Platform API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Romanian Public Procurement Platform API"
    }

# Dashboard metrics endpoint
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

# Visualization endpoints
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

# Test endpoint
@app.get("/test")
async def test_endpoint():
    return {"message": "API is working!", "status": "success"}