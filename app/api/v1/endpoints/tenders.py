"""
Tender endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from pydantic import BaseModel, UUID4
from datetime import datetime
from decimal import Decimal
from app.core.database import get_session
from app.auth.security import get_current_active_user, require_view_tenders
from app.db.models import User, Tender, ContractingAuthority, CPVCode, TenderRiskScore
from app.core.logging import app_logger

router = APIRouter()


class TenderResponse(BaseModel):
    """Tender response model"""
    id: UUID4
    title: str
    description: Optional[str]
    source_system: str
    external_id: str
    tender_type: str
    estimated_value: Optional[Decimal]
    currency: str
    publication_date: Optional[datetime]
    submission_deadline: Optional[datetime]
    status: str
    contracting_authority_name: Optional[str]
    cpv_code: Optional[str]
    cpv_description: Optional[str]
    risk_score: Optional[Decimal]
    risk_level: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenderDetailResponse(TenderResponse):
    """Detailed tender response model"""
    raw_data: dict
    processed_data: dict
    contracting_authority: dict
    cpv_details: dict
    risk_analysis: dict


class TenderSearchRequest(BaseModel):
    """Tender search request model"""
    query: Optional[str] = None
    status: Optional[List[str]] = None
    tender_type: Optional[List[str]] = None
    contracting_authority_ids: Optional[List[int]] = None
    cpv_codes: Optional[List[str]] = None
    estimated_value_min: Optional[Decimal] = None
    estimated_value_max: Optional[Decimal] = None
    publication_date_from: Optional[datetime] = None
    publication_date_to: Optional[datetime] = None
    risk_level: Optional[List[str]] = None
    
    page: int = 1
    per_page: int = 20
    sort_by: str = "publication_date"
    sort_order: str = "desc"


class TenderSearchResponse(BaseModel):
    """Tender search response model"""
    tenders: List[TenderResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


@router.get("/", response_model=TenderSearchResponse)
async def search_tenders(
    query: Optional[str] = Query(None, description="Search query"),
    status: Optional[str] = Query(None, description="Tender status"),
    tender_type: Optional[str] = Query(None, description="Tender type"),
    contracting_authority_id: Optional[int] = Query(None, description="Contracting authority ID"),
    cpv_code: Optional[str] = Query(None, description="CPV code"),
    estimated_value_min: Optional[Decimal] = Query(None, description="Minimum estimated value"),
    estimated_value_max: Optional[Decimal] = Query(None, description="Maximum estimated value"),
    publication_date_from: Optional[datetime] = Query(None, description="Publication date from"),
    publication_date_to: Optional[datetime] = Query(None, description="Publication date to"),
    risk_level: Optional[str] = Query(None, description="Risk level"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("publication_date", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_view_tenders)
):
    """Search tenders with filters"""
    
    # Build query
    query_filters = []
    
    if query:
        query_filters.append(
            or_(
                Tender.title.ilike(f"%{query}%"),
                Tender.description.ilike(f"%{query}%")
            )
        )
    
    if status:
        query_filters.append(Tender.status == status)
    
    if tender_type:
        query_filters.append(Tender.tender_type == tender_type)
    
    if contracting_authority_id:
        query_filters.append(Tender.contracting_authority_id == contracting_authority_id)
    
    if cpv_code:
        query_filters.append(Tender.cpv_code.startswith(cpv_code))
    
    if estimated_value_min:
        query_filters.append(Tender.estimated_value >= estimated_value_min)
    
    if estimated_value_max:
        query_filters.append(Tender.estimated_value <= estimated_value_max)
    
    if publication_date_from:
        query_filters.append(Tender.publication_date >= publication_date_from)
    
    if publication_date_to:
        query_filters.append(Tender.publication_date <= publication_date_to)
    
    # Build main query
    stmt = select(Tender).join(
        ContractingAuthority, Tender.contracting_authority_id == ContractingAuthority.id, isouter=True
    ).join(
        CPVCode, Tender.cpv_code == CPVCode.code, isouter=True
    ).join(
        TenderRiskScore, Tender.id == TenderRiskScore.tender_id, isouter=True
    )
    
    if query_filters:
        stmt = stmt.where(and_(*query_filters))
    
    if risk_level:
        stmt = stmt.where(TenderRiskScore.risk_level == risk_level)
    
    # Add sorting
    if sort_by == "publication_date":
        sort_column = Tender.publication_date
    elif sort_by == "estimated_value":
        sort_column = Tender.estimated_value
    elif sort_by == "risk_score":
        sort_column = TenderRiskScore.overall_risk_score
    else:
        sort_column = Tender.created_at
    
    if sort_order == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())
    
    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)
    
    # Execute query
    result = await db.execute(stmt)
    tenders = result.scalars().all()
    
    # Convert to response format
    tender_responses = []
    for tender in tenders:
        tender_response = TenderResponse(
            id=tender.id,
            title=tender.title,
            description=tender.description,
            source_system=tender.source_system,
            external_id=tender.external_id,
            tender_type=tender.tender_type,
            estimated_value=tender.estimated_value,
            currency=tender.currency,
            publication_date=tender.publication_date,
            submission_deadline=tender.submission_deadline,
            status=tender.status,
            contracting_authority_name=tender.contracting_authority.name if tender.contracting_authority else None,
            cpv_code=tender.cpv_code,
            cpv_description=tender.cpv.description if tender.cpv else None,
            risk_score=tender.risk_scores[0].overall_risk_score if tender.risk_scores else None,
            risk_level=tender.risk_scores[0].risk_level if tender.risk_scores else None,
            created_at=tender.created_at,
            updated_at=tender.updated_at
        )
        tender_responses.append(tender_response)
    
    # Calculate pagination info
    total_pages = (total + per_page - 1) // per_page
    has_next = page < total_pages
    has_prev = page > 1
    
    # Log search activity
    app_logger.info(
        "Tender search performed",
        user_id=str(current_user.id),
        query=query,
        results_count=len(tender_responses),
        total_results=total
    )
    
    return TenderSearchResponse(
        tenders=tender_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )


@router.post("/search", response_model=TenderSearchResponse)
async def advanced_search(
    search_request: TenderSearchRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_view_tenders)
):
    """Advanced tender search with complex filters"""
    
    # This would implement the same logic as the GET endpoint
    # but with more complex filtering capabilities
    
    # For now, redirect to the basic search
    return await search_tenders(
        query=search_request.query,
        status=search_request.status[0] if search_request.status else None,
        tender_type=search_request.tender_type[0] if search_request.tender_type else None,
        contracting_authority_id=search_request.contracting_authority_ids[0] if search_request.contracting_authority_ids else None,
        cpv_code=search_request.cpv_codes[0] if search_request.cpv_codes else None,
        estimated_value_min=search_request.estimated_value_min,
        estimated_value_max=search_request.estimated_value_max,
        publication_date_from=search_request.publication_date_from,
        publication_date_to=search_request.publication_date_to,
        risk_level=search_request.risk_level[0] if search_request.risk_level else None,
        page=search_request.page,
        per_page=search_request.per_page,
        sort_by=search_request.sort_by,
        sort_order=search_request.sort_order,
        db=db,
        current_user=current_user
    )


@router.get("/{tender_id}", response_model=TenderDetailResponse)
async def get_tender(
    tender_id: UUID4,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_view_tenders)
):
    """Get tender details by ID"""
    
    # Query tender with all related data
    stmt = select(Tender).where(Tender.id == tender_id)
    result = await db.execute(stmt)
    tender = result.scalar_one_or_none()
    
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Get contracting authority
    contracting_authority = {}
    if tender.contracting_authority:
        contracting_authority = {
            "id": tender.contracting_authority.id,
            "name": tender.contracting_authority.name,
            "cui": tender.contracting_authority.cui,
            "address": tender.contracting_authority.address,
            "county": tender.contracting_authority.county,
            "city": tender.contracting_authority.city
        }
    
    # Get CPV details
    cpv_details = {}
    if tender.cpv:
        cpv_details = {
            "code": tender.cpv.code,
            "description": tender.cpv.description,
            "level": tender.cpv.level
        }
    
    # Get risk analysis
    risk_analysis = {}
    if tender.risk_scores:
        latest_risk = tender.risk_scores[0]  # Assuming ordered by date
        risk_analysis = {
            "overall_risk_score": latest_risk.overall_risk_score,
            "risk_level": latest_risk.risk_level,
            "single_bidder_risk": latest_risk.single_bidder_risk,
            "price_anomaly_risk": latest_risk.price_anomaly_risk,
            "frequency_risk": latest_risk.frequency_risk,
            "geographic_risk": latest_risk.geographic_risk,
            "risk_flags": latest_risk.risk_flags,
            "analysis_date": latest_risk.analysis_date
        }
    
    # Log tender view
    app_logger.info(
        "Tender viewed",
        user_id=str(current_user.id),
        tender_id=str(tender_id),
        tender_title=tender.title
    )
    
    return TenderDetailResponse(
        id=tender.id,
        title=tender.title,
        description=tender.description,
        source_system=tender.source_system,
        external_id=tender.external_id,
        tender_type=tender.tender_type,
        estimated_value=tender.estimated_value,
        currency=tender.currency,
        publication_date=tender.publication_date,
        submission_deadline=tender.submission_deadline,
        status=tender.status,
        contracting_authority_name=tender.contracting_authority.name if tender.contracting_authority else None,
        cpv_code=tender.cpv_code,
        cpv_description=tender.cpv.description if tender.cpv else None,
        risk_score=tender.risk_scores[0].overall_risk_score if tender.risk_scores else None,
        risk_level=tender.risk_scores[0].risk_level if tender.risk_scores else None,
        created_at=tender.created_at,
        updated_at=tender.updated_at,
        raw_data=tender.raw_data,
        processed_data=tender.processed_data,
        contracting_authority=contracting_authority,
        cpv_details=cpv_details,
        risk_analysis=risk_analysis
    )


@router.get("/statistics/overview")
async def get_tender_statistics(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_view_tenders)
):
    """Get tender statistics overview"""
    
    # This would return various statistics about tenders
    # For now, return a placeholder
    
    return {
        "total_tenders": 1250,
        "active_tenders": 89,
        "total_value": "2.5B RON",
        "average_value": "2M RON",
        "top_categories": [
            {"cpv_code": "45000000", "description": "Construction work", "count": 324},
            {"cpv_code": "48000000", "description": "Software package", "count": 156},
            {"cpv_code": "79000000", "description": "Business services", "count": 98}
        ],
        "monthly_trends": [
            {"month": "2024-01", "count": 125, "value": 250000000},
            {"month": "2024-02", "count": 134, "value": 275000000},
            {"month": "2024-03", "count": 142, "value": 290000000}
        ]
    }