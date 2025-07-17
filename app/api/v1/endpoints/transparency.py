"""
Transparency platform endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, UUID4
from datetime import datetime
from decimal import Decimal
from app.core.database import get_session
from app.db.models import Tender, TenderRiskScore, ContractingAuthority, Company
from app.core.logging import app_logger

router = APIRouter()


class RiskAnalysisResponse(BaseModel):
    """Risk analysis response model"""
    tender_id: UUID4
    title: str
    contracting_authority: str
    estimated_value: Optional[Decimal]
    overall_risk_score: Decimal
    risk_level: str
    risk_flags: List[str]
    analysis_date: datetime
    detailed_analysis: dict

    class Config:
        from_attributes = True


class StatisticsResponse(BaseModel):
    """Statistics response model"""
    total_tenders: int
    total_value: Decimal
    high_risk_tenders: int
    single_bidder_tenders: int
    average_tender_value: Decimal
    top_categories: List[dict]
    risk_distribution: dict
    monthly_trends: List[dict]


class AuthorityProfileResponse(BaseModel):
    """Authority profile response model"""
    id: int
    name: str
    cui: Optional[str]
    address: Optional[str]
    county: Optional[str]
    city: Optional[str]
    authority_type: Optional[str]
    total_tenders: int
    total_value: Decimal
    average_risk_score: Optional[Decimal]
    high_risk_percentage: float

    class Config:
        from_attributes = True


class CompanyProfileResponse(BaseModel):
    """Company profile response model"""
    id: int
    name: str
    cui: Optional[str]
    address: Optional[str]
    county: Optional[str]
    city: Optional[str]
    company_type: Optional[str]
    total_bids: int
    won_bids: int
    win_rate: float
    total_won_value: Decimal

    class Config:
        from_attributes = True


@router.get("/", response_model=dict)
async def get_transparency_overview(
    db: AsyncSession = Depends(get_session)
):
    """Get transparency platform overview"""
    
    # Get basic statistics
    total_tenders_result = await db.execute(select(func.count(Tender.id)))
    total_tenders = total_tenders_result.scalar()
    
    total_value_result = await db.execute(select(func.sum(Tender.estimated_value)))
    total_value = total_value_result.scalar() or 0
    
    high_risk_result = await db.execute(
        select(func.count(TenderRiskScore.id)).where(
            TenderRiskScore.risk_level.in_(["high", "critical"])
        )
    )
    high_risk_count = high_risk_result.scalar()
    
    return {
        "message": "Romanian Public Procurement Transparency Platform",
        "statistics": {
            "total_tenders": total_tenders,
            "total_value": float(total_value),
            "high_risk_tenders": high_risk_count,
            "transparency_score": 85.2
        },
        "features": [
            "Real-time tender monitoring",
            "Risk analysis and detection",
            "Procurement statistics",
            "Authority and company profiles",
            "Geographic analysis"
        ]
    }


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    db: AsyncSession = Depends(get_session)
):
    """Get public procurement statistics"""
    
    # Get total tenders
    total_tenders_result = await db.execute(select(func.count(Tender.id)))
    total_tenders = total_tenders_result.scalar()
    
    # Get total value
    total_value_result = await db.execute(select(func.sum(Tender.estimated_value)))
    total_value = total_value_result.scalar() or 0
    
    # Get high risk tenders
    high_risk_result = await db.execute(
        select(func.count(TenderRiskScore.id)).where(
            TenderRiskScore.risk_level.in_(["high", "critical"])
        )
    )
    high_risk_tenders = high_risk_result.scalar()
    
    # Calculate average tender value
    average_value = total_value / total_tenders if total_tenders > 0 else 0
    
    # Mock data for other statistics
    statistics = StatisticsResponse(
        total_tenders=total_tenders,
        total_value=total_value,
        high_risk_tenders=high_risk_tenders,
        single_bidder_tenders=156,  # Mock data
        average_tender_value=average_value,
        top_categories=[
            {"category": "Construction", "count": 324, "value": 850000000},
            {"category": "IT Services", "count": 298, "value": 650000000},
            {"category": "Consulting", "count": 187, "value": 380000000}
        ],
        risk_distribution={
            "low": 65.2,
            "medium": 24.8,
            "high": 8.5,
            "critical": 1.5
        },
        monthly_trends=[
            {"month": "2024-01", "count": 125, "value": 250000000, "risk_score": 2.3},
            {"month": "2024-02", "count": 134, "value": 275000000, "risk_score": 2.1},
            {"month": "2024-03", "count": 142, "value": 290000000, "risk_score": 2.4}
        ]
    )
    
    return statistics


@router.get("/risk-analysis", response_model=List[RiskAnalysisResponse])
async def get_risk_analysis(
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    limit: int = Query(50, le=100, description="Limit results"),
    db: AsyncSession = Depends(get_session)
):
    """Get risk analysis data"""
    
    # Build query
    stmt = select(TenderRiskScore, Tender, ContractingAuthority).join(
        Tender, TenderRiskScore.tender_id == Tender.id
    ).join(
        ContractingAuthority, Tender.contracting_authority_id == ContractingAuthority.id,
        isouter=True
    )
    
    if risk_level:
        stmt = stmt.where(TenderRiskScore.risk_level == risk_level)
    
    stmt = stmt.order_by(TenderRiskScore.overall_risk_score.desc()).limit(limit)
    
    result = await db.execute(stmt)
    risk_data = result.all()
    
    response = []
    for risk_score, tender, authority in risk_data:
        response.append(RiskAnalysisResponse(
            tender_id=tender.id,
            title=tender.title,
            contracting_authority=authority.name if authority else "Unknown",
            estimated_value=tender.estimated_value,
            overall_risk_score=risk_score.overall_risk_score,
            risk_level=risk_score.risk_level,
            risk_flags=risk_score.risk_flags or [],
            analysis_date=risk_score.analysis_date,
            detailed_analysis=risk_score.detailed_analysis or {}
        ))
    
    return response


@router.get("/authorities", response_model=List[AuthorityProfileResponse])
async def get_authorities(
    county: Optional[str] = Query(None, description="Filter by county"),
    limit: int = Query(50, le=100, description="Limit results"),
    db: AsyncSession = Depends(get_session)
):
    """Get contracting authorities"""
    
    stmt = select(ContractingAuthority)
    
    if county:
        stmt = stmt.where(ContractingAuthority.county == county)
    
    stmt = stmt.limit(limit)
    
    result = await db.execute(stmt)
    authorities = result.scalars().all()
    
    response = []
    for authority in authorities:
        # Get authority statistics (mock data for now)
        response.append(AuthorityProfileResponse(
            id=authority.id,
            name=authority.name,
            cui=authority.cui,
            address=authority.address,
            county=authority.county,
            city=authority.city,
            authority_type=authority.authority_type,
            total_tenders=25,  # Mock data
            total_value=Decimal("5250000"),  # Mock data
            average_risk_score=Decimal("2.3"),  # Mock data
            high_risk_percentage=12.5  # Mock data
        ))
    
    return response


@router.get("/authorities/{authority_id}", response_model=AuthorityProfileResponse)
async def get_authority_profile(
    authority_id: int,
    db: AsyncSession = Depends(get_session)
):
    """Get authority profile details"""
    
    result = await db.execute(
        select(ContractingAuthority).where(ContractingAuthority.id == authority_id)
    )
    authority = result.scalar_one_or_none()
    
    if not authority:
        raise HTTPException(status_code=404, detail="Authority not found")
    
    # Get authority statistics
    tenders_result = await db.execute(
        select(func.count(Tender.id)).where(Tender.contracting_authority_id == authority_id)
    )
    total_tenders = tenders_result.scalar()
    
    value_result = await db.execute(
        select(func.sum(Tender.estimated_value)).where(Tender.contracting_authority_id == authority_id)
    )
    total_value = value_result.scalar() or 0
    
    return AuthorityProfileResponse(
        id=authority.id,
        name=authority.name,
        cui=authority.cui,
        address=authority.address,
        county=authority.county,
        city=authority.city,
        authority_type=authority.authority_type,
        total_tenders=total_tenders,
        total_value=total_value,
        average_risk_score=Decimal("2.3"),  # Mock data
        high_risk_percentage=12.5  # Mock data
    )


@router.get("/companies", response_model=List[CompanyProfileResponse])
async def get_companies(
    county: Optional[str] = Query(None, description="Filter by county"),
    limit: int = Query(50, le=100, description="Limit results"),
    db: AsyncSession = Depends(get_session)
):
    """Get company profiles"""
    
    stmt = select(Company)
    
    if county:
        stmt = stmt.where(Company.county == county)
    
    stmt = stmt.limit(limit)
    
    result = await db.execute(stmt)
    companies = result.scalars().all()
    
    response = []
    for company in companies:
        # Mock statistics for now
        response.append(CompanyProfileResponse(
            id=company.id,
            name=company.name,
            cui=company.cui,
            address=company.address,
            county=company.county,
            city=company.city,
            company_type=company.company_type,
            total_bids=15,  # Mock data
            won_bids=4,  # Mock data
            win_rate=26.7,  # Mock data
            total_won_value=Decimal("1250000")  # Mock data
        ))
    
    return response


@router.get("/companies/{company_id}", response_model=CompanyProfileResponse)
async def get_company_profile(
    company_id: int,
    db: AsyncSession = Depends(get_session)
):
    """Get company profile details"""
    
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get company statistics (mock data for now)
    return CompanyProfileResponse(
        id=company.id,
        name=company.name,
        cui=company.cui,
        address=company.address,
        county=company.county,
        city=company.city,
        company_type=company.company_type,
        total_bids=15,  # Mock data
        won_bids=4,  # Mock data
        win_rate=26.7,  # Mock data
        total_won_value=Decimal("1250000")  # Mock data
    )


@router.get("/visualizations/geographic")
async def get_geographic_visualization(
    db: AsyncSession = Depends(get_session)
):
    """Get geographic visualization data"""
    
    # Mock data for geographic visualization
    return {
        "type": "geographic",
        "data": {
            "counties": [
                {"name": "Bucharest", "tender_count": 324, "total_value": 850000000, "risk_score": 2.1},
                {"name": "Cluj", "tender_count": 156, "total_value": 425000000, "risk_score": 1.8},
                {"name": "Timis", "tender_count": 98, "total_value": 285000000, "risk_score": 2.3},
                {"name": "Brasov", "tender_count": 87, "total_value": 198000000, "risk_score": 1.9}
            ],
            "heatmap": {
                "high_risk_areas": ["Bucharest", "Timis"],
                "low_risk_areas": ["Cluj", "Brasov"]
            }
        }
    }


@router.get("/visualizations/temporal")
async def get_temporal_visualization(
    db: AsyncSession = Depends(get_session)
):
    """Get temporal visualization data"""
    
    # Mock data for temporal visualization
    return {
        "type": "temporal",
        "data": {
            "monthly_trends": [
                {"month": "2024-01", "tender_count": 125, "total_value": 250000000, "avg_risk": 2.3},
                {"month": "2024-02", "tender_count": 134, "total_value": 275000000, "avg_risk": 2.1},
                {"month": "2024-03", "tender_count": 142, "total_value": 290000000, "avg_risk": 2.4}
            ],
            "seasonal_patterns": {
                "peak_months": ["March", "September", "November"],
                "low_months": ["January", "July", "August"]
            }
        }
    }


@router.get("/visualizations/risk-heatmap")
async def get_risk_heatmap(
    db: AsyncSession = Depends(get_session)
):
    """Get risk heatmap data"""
    
    # Mock data for risk heatmap
    return {
        "type": "risk_heatmap",
        "data": {
            "categories": [
                {"category": "Construction", "risk_score": 2.8, "tender_count": 324},
                {"category": "IT Services", "risk_score": 1.9, "tender_count": 298},
                {"category": "Consulting", "risk_score": 2.2, "tender_count": 187},
                {"category": "Medical Equipment", "risk_score": 3.1, "tender_count": 156}
            ],
            "authorities": [
                {"authority": "Ministry of Health", "risk_score": 2.6, "tender_count": 89},
                {"authority": "Ministry of Transport", "risk_score": 2.9, "tender_count": 76},
                {"authority": "Bucharest City Hall", "risk_score": 2.1, "tender_count": 124}
            ]
        }
    }