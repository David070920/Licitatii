"""
Visualization API endpoints for data visualization and analytics
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.db.models import (
    Tender, Company, ContractingAuthority, TenderBid, TenderAward, 
    TenderRiskScore, CPVCode
)
from app.auth.security import get_current_user
from app.db.models import User

router = APIRouter()


# Pydantic models for responses
class TenderVolumeData(BaseModel):
    """Tender volume data for charts"""
    date: str
    count: int
    total_value: float
    average_value: float


class GeographicData(BaseModel):
    """Geographic data for maps"""
    county: str
    count: int
    total_value: float
    average_value: float
    risk_score: Optional[float] = None


class RiskDistributionData(BaseModel):
    """Risk distribution data"""
    risk_level: str
    count: int
    percentage: float


class CompanyPerformanceData(BaseModel):
    """Company performance metrics"""
    company_name: str
    company_cui: str
    tender_count: int
    win_rate: float
    total_value: float
    average_value: float
    risk_score: Optional[float] = None


class CPVAnalysisData(BaseModel):
    """CPV code analysis data"""
    cpv_code: str
    description: str
    count: int
    total_value: float
    average_value: float
    competition_level: float


class TimeSeriesData(BaseModel):
    """Time series data for trends"""
    period: str
    metric: str
    value: float
    change_percentage: Optional[float] = None


class DashboardMetrics(BaseModel):
    """Dashboard summary metrics"""
    total_tenders: int
    total_value: float
    average_value: float
    active_tenders: int
    high_risk_tenders: int
    unique_companies: int
    unique_authorities: int
    average_risk_score: float


# Visualization endpoints
@router.get("/dashboard/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering")
):
    """Get dashboard summary metrics"""
    
    # Build date filter
    date_filter = []
    if start_date:
        date_filter.append(Tender.publication_date >= start_date)
    if end_date:
        date_filter.append(Tender.publication_date <= end_date)
    
    # Get basic tender metrics
    tender_query = db.query(Tender)
    if date_filter:
        tender_query = tender_query.filter(and_(*date_filter))
    
    total_tenders = await tender_query.count()
    
    # Get value metrics
    value_result = await tender_query.filter(
        Tender.estimated_value.isnot(None)
    ).with_entities(
        func.sum(Tender.estimated_value).label('total_value'),
        func.avg(Tender.estimated_value).label('average_value')
    ).first()
    
    total_value = float(value_result.total_value or 0)
    average_value = float(value_result.average_value or 0)
    
    # Get active tenders
    active_tenders = await tender_query.filter(
        Tender.status.in_(['published', 'active', 'evaluation'])
    ).count()
    
    # Get high risk tenders
    high_risk_query = db.query(Tender).join(TenderRiskScore).filter(
        TenderRiskScore.risk_level == 'high'
    )
    if date_filter:
        high_risk_query = high_risk_query.filter(and_(*date_filter))
    
    high_risk_tenders = await high_risk_query.count()
    
    # Get unique companies and authorities
    unique_companies = await db.query(Company).count()
    unique_authorities = await db.query(ContractingAuthority).count()
    
    # Get average risk score
    risk_result = await db.query(TenderRiskScore).filter(
        TenderRiskScore.tender_id.in_(
            tender_query.with_entities(Tender.id).subquery()
        )
    ).with_entities(
        func.avg(TenderRiskScore.overall_risk_score).label('avg_risk')
    ).first()
    
    average_risk_score = float(risk_result.avg_risk or 0)
    
    return DashboardMetrics(
        total_tenders=total_tenders,
        total_value=total_value,
        average_value=average_value,
        active_tenders=active_tenders,
        high_risk_tenders=high_risk_tenders,
        unique_companies=unique_companies,
        unique_authorities=unique_authorities,
        average_risk_score=average_risk_score
    )


@router.get("/charts/tender-volume", response_model=List[TenderVolumeData])
async def get_tender_volume_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    period: str = Query("monthly", description="Period: daily, weekly, monthly, yearly"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Get tender volume data for time series charts"""
    
    # Determine date format based on period
    date_formats = {
        'daily': '%Y-%m-%d',
        'weekly': '%Y-%W',
        'monthly': '%Y-%m',
        'yearly': '%Y'
    }
    
    if period not in date_formats:
        raise HTTPException(status_code=400, detail="Invalid period")
    
    # Build query
    query = db.query(
        func.date_trunc(period, Tender.publication_date).label('period'),
        func.count(Tender.id).label('count'),
        func.sum(Tender.estimated_value).label('total_value'),
        func.avg(Tender.estimated_value).label('average_value')
    ).filter(
        Tender.publication_date.isnot(None),
        Tender.estimated_value.isnot(None)
    )
    
    if start_date:
        query = query.filter(Tender.publication_date >= start_date)
    if end_date:
        query = query.filter(Tender.publication_date <= end_date)
    
    results = await query.group_by(
        func.date_trunc(period, Tender.publication_date)
    ).order_by(
        func.date_trunc(period, Tender.publication_date)
    ).all()
    
    return [
        TenderVolumeData(
            date=result.period.strftime(date_formats[period]),
            count=result.count,
            total_value=float(result.total_value or 0),
            average_value=float(result.average_value or 0)
        )
        for result in results
    ]


@router.get("/charts/geographic", response_model=List[GeographicData])
async def get_geographic_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Get geographic distribution data for maps"""
    
    query = db.query(
        ContractingAuthority.county,
        func.count(Tender.id).label('count'),
        func.sum(Tender.estimated_value).label('total_value'),
        func.avg(Tender.estimated_value).label('average_value'),
        func.avg(TenderRiskScore.overall_risk_score).label('risk_score')
    ).join(
        Tender, Tender.contracting_authority_id == ContractingAuthority.id
    ).outerjoin(
        TenderRiskScore, TenderRiskScore.tender_id == Tender.id
    ).filter(
        ContractingAuthority.county.isnot(None),
        Tender.estimated_value.isnot(None)
    )
    
    if start_date:
        query = query.filter(Tender.publication_date >= start_date)
    if end_date:
        query = query.filter(Tender.publication_date <= end_date)
    
    results = await query.group_by(
        ContractingAuthority.county
    ).order_by(
        desc(func.count(Tender.id))
    ).all()
    
    return [
        GeographicData(
            county=result.county,
            count=result.count,
            total_value=float(result.total_value or 0),
            average_value=float(result.average_value or 0),
            risk_score=float(result.risk_score or 0) if result.risk_score else None
        )
        for result in results
    ]


@router.get("/charts/risk-distribution", response_model=List[RiskDistributionData])
async def get_risk_distribution_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Get risk distribution data for risk analysis charts"""
    
    query = db.query(
        TenderRiskScore.risk_level,
        func.count(TenderRiskScore.id).label('count')
    ).join(
        Tender, Tender.id == TenderRiskScore.tender_id
    )
    
    if start_date:
        query = query.filter(Tender.publication_date >= start_date)
    if end_date:
        query = query.filter(Tender.publication_date <= end_date)
    
    results = await query.group_by(
        TenderRiskScore.risk_level
    ).all()
    
    total_count = sum(result.count for result in results)
    
    return [
        RiskDistributionData(
            risk_level=result.risk_level,
            count=result.count,
            percentage=round((result.count / total_count) * 100, 2) if total_count > 0 else 0
        )
        for result in results
    ]


@router.get("/charts/company-performance", response_model=List[CompanyPerformanceData])
async def get_company_performance_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, description="Number of companies to return"),
    sort_by: str = Query("win_rate", description="Sort by: win_rate, total_value, tender_count"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Get company performance data for business intelligence"""
    
    # Build subquery for tender filtering
    tender_subquery = db.query(Tender.id)
    if start_date:
        tender_subquery = tender_subquery.filter(Tender.publication_date >= start_date)
    if end_date:
        tender_subquery = tender_subquery.filter(Tender.publication_date <= end_date)
    
    # Main query for company performance
    query = db.query(
        Company.name,
        Company.cui,
        func.count(TenderBid.id).label('tender_count'),
        func.sum(func.case([(TenderBid.is_winner == True, 1)], else_=0)).label('wins'),
        func.sum(TenderAward.awarded_amount).label('total_value'),
        func.avg(TenderAward.awarded_amount).label('average_value'),
        func.avg(TenderRiskScore.overall_risk_score).label('risk_score')
    ).join(
        TenderBid, TenderBid.company_id == Company.id
    ).outerjoin(
        TenderAward, TenderAward.company_id == Company.id
    ).outerjoin(
        TenderRiskScore, TenderRiskScore.tender_id == TenderBid.tender_id
    ).filter(
        TenderBid.tender_id.in_(tender_subquery)
    ).group_by(
        Company.id, Company.name, Company.cui
    )
    
    # Apply sorting
    if sort_by == "win_rate":
        query = query.order_by(desc(func.sum(func.case([(TenderBid.is_winner == True, 1)], else_=0)) / func.count(TenderBid.id)))
    elif sort_by == "total_value":
        query = query.order_by(desc(func.sum(TenderAward.awarded_amount)))
    elif sort_by == "tender_count":
        query = query.order_by(desc(func.count(TenderBid.id)))
    
    results = await query.limit(limit).all()
    
    return [
        CompanyPerformanceData(
            company_name=result.name,
            company_cui=result.cui or "N/A",
            tender_count=result.tender_count,
            win_rate=round((result.wins / result.tender_count) * 100, 2) if result.tender_count > 0 else 0,
            total_value=float(result.total_value or 0),
            average_value=float(result.average_value or 0),
            risk_score=float(result.risk_score or 0) if result.risk_score else None
        )
        for result in results
    ]


@router.get("/charts/cpv-analysis", response_model=List[CPVAnalysisData])
async def get_cpv_analysis_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, description="Number of CPV codes to return"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Get CPV code analysis data for market insights"""
    
    query = db.query(
        CPVCode.code,
        CPVCode.description,
        func.count(Tender.id).label('count'),
        func.sum(Tender.estimated_value).label('total_value'),
        func.avg(Tender.estimated_value).label('average_value'),
        func.avg(func.count(TenderBid.id)).label('avg_bidders')
    ).join(
        Tender, Tender.cpv_code == CPVCode.code
    ).outerjoin(
        TenderBid, TenderBid.tender_id == Tender.id
    ).filter(
        Tender.estimated_value.isnot(None)
    )
    
    if start_date:
        query = query.filter(Tender.publication_date >= start_date)
    if end_date:
        query = query.filter(Tender.publication_date <= end_date)
    
    results = await query.group_by(
        CPVCode.code, CPVCode.description
    ).order_by(
        desc(func.count(Tender.id))
    ).limit(limit).all()
    
    return [
        CPVAnalysisData(
            cpv_code=result.code,
            description=result.description[:100] + "..." if len(result.description) > 100 else result.description,
            count=result.count,
            total_value=float(result.total_value or 0),
            average_value=float(result.average_value or 0),
            competition_level=float(result.avg_bidders or 0)
        )
        for result in results
    ]


@router.get("/charts/time-series", response_model=List[TimeSeriesData])
async def get_time_series_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    metric: str = Query("tender_count", description="Metric: tender_count, total_value, risk_score"),
    period: str = Query("monthly", description="Period: daily, weekly, monthly, yearly"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Get time series data for trend analysis"""
    
    # Validate parameters
    valid_metrics = ["tender_count", "total_value", "risk_score"]
    valid_periods = ["daily", "weekly", "monthly", "yearly"]
    
    if metric not in valid_metrics:
        raise HTTPException(status_code=400, detail="Invalid metric")
    if period not in valid_periods:
        raise HTTPException(status_code=400, detail="Invalid period")
    
    # Build base query
    if metric == "tender_count":
        query = db.query(
            func.date_trunc(period, Tender.publication_date).label('period'),
            func.count(Tender.id).label('value')
        ).filter(Tender.publication_date.isnot(None))
    elif metric == "total_value":
        query = db.query(
            func.date_trunc(period, Tender.publication_date).label('period'),
            func.sum(Tender.estimated_value).label('value')
        ).filter(
            Tender.publication_date.isnot(None),
            Tender.estimated_value.isnot(None)
        )
    elif metric == "risk_score":
        query = db.query(
            func.date_trunc(period, Tender.publication_date).label('period'),
            func.avg(TenderRiskScore.overall_risk_score).label('value')
        ).join(
            TenderRiskScore, TenderRiskScore.tender_id == Tender.id
        ).filter(Tender.publication_date.isnot(None))
    
    if start_date:
        query = query.filter(Tender.publication_date >= start_date)
    if end_date:
        query = query.filter(Tender.publication_date <= end_date)
    
    results = await query.group_by(
        func.date_trunc(period, Tender.publication_date)
    ).order_by(
        func.date_trunc(period, Tender.publication_date)
    ).all()
    
    # Calculate percentage changes
    data = []
    prev_value = None
    
    for result in results:
        value = float(result.value or 0)
        change_percentage = None
        
        if prev_value is not None and prev_value != 0:
            change_percentage = round(((value - prev_value) / prev_value) * 100, 2)
        
        data.append(TimeSeriesData(
            period=result.period.strftime('%Y-%m-%d'),
            metric=metric,
            value=value,
            change_percentage=change_percentage
        ))
        
        prev_value = value
    
    return data


@router.get("/export/data")
async def export_visualization_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    chart_type: str = Query(..., description="Chart type to export"),
    format: str = Query("json", description="Export format: json, csv"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Export visualization data in various formats"""
    
    # Map chart types to their respective functions
    chart_handlers = {
        "tender-volume": get_tender_volume_data,
        "geographic": get_geographic_data,
        "risk-distribution": get_risk_distribution_data,
        "company-performance": get_company_performance_data,
        "cpv-analysis": get_cpv_analysis_data,
        "time-series": get_time_series_data
    }
    
    if chart_type not in chart_handlers:
        raise HTTPException(status_code=400, detail="Invalid chart type")
    
    # Get data using the appropriate handler
    handler = chart_handlers[chart_type]
    data = await handler(db=db, current_user=current_user, start_date=start_date, end_date=end_date)
    
    if format == "json":
        return {"data": data, "chart_type": chart_type, "exported_at": datetime.now().isoformat()}
    elif format == "csv":
        # Convert to CSV format (simplified)
        if not data:
            return {"error": "No data to export"}
        
        import csv
        import io
        
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].dict().keys())
            writer.writeheader()
            for item in data:
                writer.writerow(item.dict())
        
        return {"csv_data": output.getvalue(), "chart_type": chart_type}
    
    raise HTTPException(status_code=400, detail="Invalid export format")