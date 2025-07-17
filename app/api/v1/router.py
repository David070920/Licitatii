"""
Main API v1 router
"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, tenders, business, transparency, admin, risk, visualizations

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenders.router, prefix="/tenders", tags=["Tenders"])
api_router.include_router(business.router, prefix="/business", tags=["Business"])
api_router.include_router(transparency.router, prefix="/transparency", tags=["Transparency"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administration"])
api_router.include_router(risk.router, prefix="/risk", tags=["Risk Analysis"])
api_router.include_router(visualizations.router, prefix="/visualizations", tags=["Data Visualization"])