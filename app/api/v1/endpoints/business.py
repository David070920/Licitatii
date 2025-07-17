"""
Business user endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, UUID4
from datetime import datetime
from app.core.database import get_session
from app.auth.security import get_current_active_user, require_permission
from app.db.models import User, SavedSearch, RiskAlert
from app.core.logging import app_logger

router = APIRouter()


class SavedSearchRequest(BaseModel):
    """Saved search request model"""
    search_name: str
    search_query: dict
    search_filters: dict = {}
    alert_enabled: bool = False
    alert_frequency: str = "daily"


class SavedSearchResponse(BaseModel):
    """Saved search response model"""
    id: UUID4
    search_name: str
    search_query: dict
    search_filters: dict
    alert_enabled: bool
    alert_frequency: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    """Alert response model"""
    id: UUID4
    alert_type: str
    alert_level: str
    title: str
    message: str
    status: str
    sent_at: datetime
    read_at: Optional[datetime]

    class Config:
        from_attributes = True


class AnalyticsDashboardResponse(BaseModel):
    """Analytics dashboard response model"""
    total_tenders_monitored: int
    active_alerts: int
    saved_searches: int
    recent_activity: List[dict]
    market_insights: dict
    competitor_analysis: dict


@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permission("basic_analytics"))
):
    """Get business dashboard data"""
    
    # Get user's saved searches count
    saved_searches_result = await db.execute(
        select(SavedSearch).where(SavedSearch.user_id == current_user.id)
    )
    saved_searches_count = len(saved_searches_result.scalars().all())
    
    # Get user's active alerts count
    alerts_result = await db.execute(
        select(RiskAlert).where(
            RiskAlert.user_id == current_user.id,
            RiskAlert.status == "unread"
        )
    )
    active_alerts_count = len(alerts_result.scalars().all())
    
    # Mock data for other metrics
    dashboard_data = AnalyticsDashboardResponse(
        total_tenders_monitored=1250,
        active_alerts=active_alerts_count,
        saved_searches=saved_searches_count,
        recent_activity=[
            {
                "type": "new_tender",
                "title": "Software Development Services",
                "authority": "Ministry of Health",
                "value": 150000,
                "timestamp": "2024-01-15T10:30:00Z"
            },
            {
                "type": "alert_triggered",
                "title": "High Risk Tender Alert",
                "description": "Single bidder detected",
                "timestamp": "2024-01-15T09:15:00Z"
            }
        ],
        market_insights={
            "trending_categories": [
                {"category": "IT Services", "growth": 15.2},
                {"category": "Construction", "growth": -5.8},
                {"category": "Consulting", "growth": 8.4}
            ],
            "average_tender_value": 2150000,
            "market_size": "2.5B RON"
        },
        competitor_analysis={
            "top_competitors": [
                {"name": "Company A", "win_rate": 25.5, "avg_value": 850000},
                {"name": "Company B", "win_rate": 18.2, "avg_value": 1200000},
                {"name": "Company C", "win_rate": 15.7, "avg_value": 750000}
            ],
            "market_share": 12.3,
            "performance_trend": "improving"
        }
    )
    
    app_logger.info(
        "Business dashboard accessed",
        user_id=str(current_user.id)
    )
    
    return dashboard_data


@router.get("/saved-searches", response_model=List[SavedSearchResponse])
async def get_saved_searches(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's saved searches"""
    
    result = await db.execute(
        select(SavedSearch).where(SavedSearch.user_id == current_user.id)
    )
    saved_searches = result.scalars().all()
    
    return [SavedSearchResponse.from_orm(search) for search in saved_searches]


@router.post("/saved-searches", response_model=SavedSearchResponse)
async def create_saved_search(
    search_request: SavedSearchRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new saved search"""
    
    saved_search = SavedSearch(
        user_id=current_user.id,
        search_name=search_request.search_name,
        search_query=search_request.search_query,
        search_filters=search_request.search_filters,
        alert_enabled=search_request.alert_enabled,
        alert_frequency=search_request.alert_frequency
    )
    
    db.add(saved_search)
    await db.commit()
    await db.refresh(saved_search)
    
    app_logger.info(
        "Saved search created",
        user_id=str(current_user.id),
        search_name=search_request.search_name
    )
    
    return SavedSearchResponse.from_orm(saved_search)


@router.put("/saved-searches/{search_id}", response_model=SavedSearchResponse)
async def update_saved_search(
    search_id: UUID4,
    search_request: SavedSearchRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Update a saved search"""
    
    result = await db.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == current_user.id
        )
    )
    saved_search = result.scalar_one_or_none()
    
    if not saved_search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    
    saved_search.search_name = search_request.search_name
    saved_search.search_query = search_request.search_query
    saved_search.search_filters = search_request.search_filters
    saved_search.alert_enabled = search_request.alert_enabled
    saved_search.alert_frequency = search_request.alert_frequency
    
    await db.commit()
    await db.refresh(saved_search)
    
    return SavedSearchResponse.from_orm(saved_search)


@router.delete("/saved-searches/{search_id}")
async def delete_saved_search(
    search_id: UUID4,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a saved search"""
    
    result = await db.execute(
        select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.user_id == current_user.id
        )
    )
    saved_search = result.scalar_one_or_none()
    
    if not saved_search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    
    await db.delete(saved_search)
    await db.commit()
    
    return {"message": "Saved search deleted successfully"}


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's alerts"""
    
    stmt = select(RiskAlert).where(RiskAlert.user_id == current_user.id)
    
    if status:
        stmt = stmt.where(RiskAlert.status == status)
    
    result = await db.execute(stmt)
    alerts = result.scalars().all()
    
    return [AlertResponse.from_orm(alert) for alert in alerts]


@router.put("/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: UUID4,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Mark alert as read"""
    
    result = await db.execute(
        select(RiskAlert).where(
            RiskAlert.id == alert_id,
            RiskAlert.user_id == current_user.id
        )
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "read"
    alert.read_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Alert marked as read"}


@router.get("/analytics/trends")
async def get_analytics_trends(
    current_user: User = Depends(require_permission("advanced_analytics"))
):
    """Get analytics trends"""
    
    # Mock data for trends
    return {
        "tender_volume_trend": [
            {"month": "2024-01", "count": 125, "value": 250000000},
            {"month": "2024-02", "count": 134, "value": 275000000},
            {"month": "2024-03", "count": 142, "value": 290000000}
        ],
        "category_distribution": [
            {"category": "IT Services", "percentage": 35.2},
            {"category": "Construction", "percentage": 28.5},
            {"category": "Consulting", "percentage": 18.3},
            {"category": "Other", "percentage": 18.0}
        ],
        "risk_distribution": [
            {"risk_level": "low", "count": 856},
            {"risk_level": "medium", "count": 298},
            {"risk_level": "high", "count": 84},
            {"risk_level": "critical", "count": 12}
        ]
    }


@router.get("/reports")
async def get_reports(
    current_user: User = Depends(require_permission("custom_reports"))
):
    """Get available reports"""
    
    # Mock data for reports
    return {
        "available_reports": [
            {
                "id": "monthly_summary",
                "name": "Monthly Summary Report",
                "description": "Overview of monthly tender activity",
                "format": "PDF"
            },
            {
                "id": "risk_analysis",
                "name": "Risk Analysis Report",
                "description": "Detailed risk analysis of tenders",
                "format": "Excel"
            },
            {
                "id": "market_insights",
                "name": "Market Insights Report",
                "description": "Market trends and opportunities",
                "format": "PDF"
            }
        ]
    }


@router.post("/reports/generate")
async def generate_report(
    report_type: str,
    current_user: User = Depends(require_permission("custom_reports"))
):
    """Generate a custom report"""
    
    # This would typically queue a background job to generate the report
    # For now, return a mock response
    
    return {
        "message": "Report generation started",
        "report_id": "report_123456",
        "status": "processing",
        "estimated_completion": "2024-01-15T15:30:00Z"
    }