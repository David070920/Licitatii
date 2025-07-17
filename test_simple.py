import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Romanian Public Procurement Platform API",
    version="1.0.0",
    description="API for Romanian Public Procurement Platform"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Romanian Public Procurement Platform API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/v1/dashboard/metrics")
def get_dashboard_metrics():
    return {
        "total_tenders": 1250,
        "total_value": 2500000000,
        "unique_authorities": 120,
        "unique_companies": 850,
        "average_risk_score": 35.2,
        "active_tenders": 45
    }

@app.get("/api/v1/visualizations/dashboard/metrics")
def get_visualization_metrics():
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
def get_tender_volume():
    return [
        {"month": "Ian", "count": 95, "value": 180000000},
        {"month": "Feb", "count": 88, "value": 165000000},
        {"month": "Mar", "count": 102, "value": 195000000},
        {"month": "Apr", "count": 110, "value": 210000000},
        {"month": "Mai", "count": 125, "value": 240000000}
    ]

@app.get("/api/v1/charts/geographic")
def get_geographic_data():
    return [
        {"county": "Bucuresti", "count": 150, "total_value": 450000000},
        {"county": "Cluj", "count": 85, "total_value": 180000000},
        {"county": "Timis", "count": 72, "total_value": 160000000},
        {"county": "Constanta", "count": 65, "total_value": 140000000},
        {"county": "Iasi", "count": 58, "total_value": 125000000}
    ]

@app.get("/api/v1/charts/risk-distribution")
def get_risk_distribution():
    return [
        {"risk_level": "low", "count": 750, "percentage": 60},
        {"risk_level": "medium", "count": 312, "percentage": 25},
        {"risk_level": "high", "count": 156, "percentage": 12.5},
        {"risk_level": "critical", "count": 32, "percentage": 2.5}
    ]

@app.get("/api/v1/charts/company-performance")
def get_company_performance():
    return [
        {"company": "SC CONSTRUCTII SRL", "contracts": 25, "total_value": 45000000, "success_rate": 92},
        {"company": "TECH SOLUTIONS SA", "contracts": 18, "total_value": 32000000, "success_rate": 88},
        {"company": "INFRASTRUCTURE CORP", "contracts": 12, "total_value": 28000000, "success_rate": 85},
        {"company": "SERVICES GROUP", "contracts": 15, "total_value": 22000000, "success_rate": 90}
    ]

@app.get("/api/v1/charts/cpv-analysis")
def get_cpv_analysis():
    return [
        {"cpv_code": "45000000", "description": "Construction work", "count": 320, "total_value": 850000000},
        {"cpv_code": "30000000", "description": "Office equipment", "count": 150, "total_value": 120000000},
        {"cpv_code": "50000000", "description": "Repair services", "count": 200, "total_value": 95000000},
        {"cpv_code": "79000000", "description": "Business services", "count": 180, "total_value": 85000000}
    ]

@app.get("/api/v1/charts/time-series")
def get_time_series():
    return [
        {"date": "2024-01", "tender_count": 95, "total_value": 180000000, "risk_score": 38.5},
        {"date": "2024-02", "tender_count": 88, "total_value": 165000000, "risk_score": 36.2},
        {"date": "2024-03", "tender_count": 102, "total_value": 195000000, "risk_score": 35.8},
        {"date": "2024-04", "tender_count": 110, "total_value": 210000000, "risk_score": 34.1},
        {"date": "2024-05", "tender_count": 125, "total_value": 240000000, "risk_score": 33.5}
    ]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)