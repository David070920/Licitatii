from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

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