"""
Risk Analysis API Endpoints

This module provides REST API endpoints for risk analysis functionality,
including risk assessment, statistics, and reporting.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import redis

from app.core.database import get_db
from app.auth.security import get_current_user
from app.db.models import User, Tender, TenderRiskScore
from app.services.risk_detection.risk_analyzer import RiskAnalyzer
from app.services.risk_detection.base import RiskDetectionConfig
from app.services.tasks.risk_analysis import analyze_new_tenders, periodic_risk_assessment

router = APIRouter()


# Pydantic models for request/response
class RiskAnalysisRequest(BaseModel):
    tender_id: str = Field(..., description="Tender ID to analyze")
    force_refresh: bool = Field(False, description="Force refresh of analysis")


class RiskAnalysisResponse(BaseModel):
    tender_id: str
    risk_score: float
    risk_level: str
    risk_flags: List[str]
    confidence: float
    analysis_date: datetime
    detailed_analysis: Dict[str, Any]


class RiskStatisticsResponse(BaseModel):
    period_days: int
    total_analyzed: int
    avg_overall_score: float
    risk_level_distribution: Dict[str, Any]
    algorithm_performance: Dict[str, Any]
    top_risk_flags: List[tuple]
    high_risk_rate: float
    analysis_date: datetime


class HighRiskTenderResponse(BaseModel):
    tender_id: str
    title: str
    contracting_authority: Optional[str]
    estimated_value: Optional[float]
    overall_risk_score: float
    risk_level: str
    risk_flags: List[str]
    analysis_date: datetime
    publication_date: Optional[datetime]


class RiskConfigurationRequest(BaseModel):
    single_bidder_threshold: Optional[float] = Field(None, ge=0, le=1)
    price_anomaly_z_threshold: Optional[float] = Field(None, ge=0)
    frequent_winner_threshold: Optional[float] = Field(None, ge=0, le=1)
    geographic_clustering_threshold: Optional[float] = Field(None, ge=0, le=1)
    high_risk_threshold: Optional[float] = Field(None, ge=0, le=100)
    medium_risk_threshold: Optional[float] = Field(None, ge=0, le=100)
    low_risk_threshold: Optional[float] = Field(None, ge=0, le=100)


# Dependency for risk analyzer
def get_risk_analyzer() -> RiskAnalyzer:
    """Get risk analyzer instance"""
    config = RiskDetectionConfig()
    try:
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        redis_client.ping()
    except:
        redis_client = None
    
    return RiskAnalyzer(config, redis_client)


@router.post("/analyze", response_model=RiskAnalysisResponse)
async def analyze_tender_risk(
    request: RiskAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    risk_analyzer: RiskAnalyzer = Depends(get_risk_analyzer)
):
    """Analyze risk factors for a specific tender"""
    
    # Get tender
    tender = db.query(Tender).filter(Tender.id == request.tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    try:
        # Perform risk analysis
        result = risk_analyzer.analyze_tender(tender, db, request.force_refresh)
        
        return RiskAnalysisResponse(
            tender_id=str(tender.id),
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            risk_flags=result.risk_flags,
            confidence=result.confidence,
            analysis_date=result.timestamp,
            detailed_analysis=result.detailed_analysis
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk analysis failed: {str(e)}")


@router.get("/statistics", response_model=RiskStatisticsResponse)
async def get_risk_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    risk_analyzer: RiskAnalyzer = Depends(get_risk_analyzer)
):
    """Get risk statistics for the specified period"""
    
    try:
        stats = risk_analyzer.get_risk_statistics(db, days)
        
        return RiskStatisticsResponse(
            period_days=stats["period_days"],
            total_analyzed=stats["total_analyzed"],
            avg_overall_score=stats["avg_overall_score"],
            risk_level_distribution=stats["risk_level_distribution"],
            algorithm_performance=stats["algorithm_performance"],
            top_risk_flags=stats["top_risk_flags"],
            high_risk_rate=stats["high_risk_rate"],
            analysis_date=datetime.fromisoformat(stats["analysis_date"])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/high-risk-tenders", response_model=List[HighRiskTenderResponse])
async def get_high_risk_tenders(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of tenders to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    risk_analyzer: RiskAnalyzer = Depends(get_risk_analyzer)
):
    """Get the highest risk tenders"""
    
    try:
        high_risk_tenders = risk_analyzer.get_high_risk_tenders(db, limit)
        
        return [
            HighRiskTenderResponse(
                tender_id=tender["tender_id"],
                title=tender["title"],
                contracting_authority=tender["contracting_authority"],
                estimated_value=tender["estimated_value"],
                overall_risk_score=tender["overall_risk_score"],
                risk_level=tender["risk_level"],
                risk_flags=tender["risk_flags"],
                analysis_date=datetime.fromisoformat(tender["analysis_date"]),
                publication_date=datetime.fromisoformat(tender["publication_date"]) if tender["publication_date"] else None
            )
            for tender in high_risk_tenders
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get high-risk tenders: {str(e)}")


@router.get("/algorithm-performance")
async def get_algorithm_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    risk_analyzer: RiskAnalyzer = Depends(get_risk_analyzer)
):
    """Get performance metrics for risk detection algorithms"""
    
    try:
        performance = risk_analyzer.get_algorithm_performance(db)
        return {"algorithm_performance": performance}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get algorithm performance: {str(e)}")


@router.get("/system-info")
async def get_system_info(
    current_user: User = Depends(get_current_user),
    risk_analyzer: RiskAnalyzer = Depends(get_risk_analyzer)
):
    """Get information about the risk detection system"""
    
    try:
        system_info = risk_analyzer.get_system_info()
        return {"system_info": system_info}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system info: {str(e)}")


@router.post("/reanalyze/{tender_id}")
async def reanalyze_tender(
    tender_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    risk_analyzer: RiskAnalyzer = Depends(get_risk_analyzer)
):
    """Reanalyze a specific tender with fresh data"""
    
    try:
        result = risk_analyzer.reanalyze_tender(tender_id, db)
        
        return {
            "message": "Tender reanalyzed successfully",
            "tender_id": tender_id,
            "risk_score": result.risk_score,
            "risk_level": result.risk_level,
            "analysis_date": result.timestamp.isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reanalysis failed: {str(e)}")


@router.post("/batch-analyze")
async def trigger_batch_analysis(
    background_tasks: BackgroundTasks,
    batch_size: int = Query(100, ge=1, le=500, description="Number of tenders to analyze"),
    current_user: User = Depends(get_current_user)
):
    """Trigger batch analysis of new tenders"""
    
    # Add background task
    background_tasks.add_task(analyze_new_tenders.delay, batch_size)
    
    return {
        "message": "Batch analysis task scheduled",
        "batch_size": batch_size
    }


@router.post("/periodic-assessment")
async def trigger_periodic_assessment(
    background_tasks: BackgroundTasks,
    days_lookback: int = Query(30, ge=1, le=365, description="Days to look back for assessment"),
    current_user: User = Depends(get_current_user)
):
    """Trigger periodic risk assessment"""
    
    # Add background task
    background_tasks.add_task(periodic_risk_assessment.delay, days_lookback)
    
    return {
        "message": "Periodic assessment task scheduled",
        "days_lookback": days_lookback
    }


@router.get("/configuration")
async def get_risk_configuration(
    current_user: User = Depends(get_current_user),
    risk_analyzer: RiskAnalyzer = Depends(get_risk_analyzer)
):
    """Get current risk detection configuration"""
    
    try:
        config = risk_analyzer.config
        
        return {
            "configuration": {
                "single_bidder_threshold": config.single_bidder_threshold,
                "price_anomaly_z_threshold": config.price_anomaly_z_threshold,
                "frequent_winner_threshold": config.frequent_winner_threshold,
                "geographic_clustering_threshold": config.geographic_clustering_threshold,
                "high_risk_threshold": config.high_risk_threshold,
                "medium_risk_threshold": config.medium_risk_threshold,
                "low_risk_threshold": config.low_risk_threshold,
                "min_sample_size_price_analysis": config.min_sample_size_price_analysis,
                "min_sample_size_frequency_analysis": config.min_sample_size_frequency_analysis,
                "min_sample_size_geographic_analysis": config.min_sample_size_geographic_analysis,
                "analysis_window_months": config.analysis_window_months,
                "historical_data_years": config.historical_data_years
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")


@router.put("/configuration")
async def update_risk_configuration(
    request: RiskConfigurationRequest,
    current_user: User = Depends(get_current_user),
    risk_analyzer: RiskAnalyzer = Depends(get_risk_analyzer)
):
    """Update risk detection configuration"""
    
    try:
        # Prepare configuration updates
        config_updates = {}
        
        if request.single_bidder_threshold is not None:
            config_updates["single_bidder_threshold"] = request.single_bidder_threshold
        if request.price_anomaly_z_threshold is not None:
            config_updates["price_anomaly_z_threshold"] = request.price_anomaly_z_threshold
        if request.frequent_winner_threshold is not None:
            config_updates["frequent_winner_threshold"] = request.frequent_winner_threshold
        if request.geographic_clustering_threshold is not None:
            config_updates["geographic_clustering_threshold"] = request.geographic_clustering_threshold
        if request.high_risk_threshold is not None:
            config_updates["high_risk_threshold"] = request.high_risk_threshold
        if request.medium_risk_threshold is not None:
            config_updates["medium_risk_threshold"] = request.medium_risk_threshold
        if request.low_risk_threshold is not None:
            config_updates["low_risk_threshold"] = request.low_risk_threshold
        
        # Validate configuration
        validation_result = risk_analyzer.validate_configuration()
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Configuration validation failed: {validation_result['issues']}"
            )
        
        # Update configuration
        risk_analyzer.update_configuration(config_updates)
        
        return {
            "message": "Configuration updated successfully",
            "updated_fields": list(config_updates.keys()),
            "validation_warnings": validation_result.get("warnings", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


@router.post("/validate-configuration")
async def validate_risk_configuration(
    current_user: User = Depends(get_current_user),
    risk_analyzer: RiskAnalyzer = Depends(get_risk_analyzer)
):
    """Validate current risk detection configuration"""
    
    try:
        validation_result = risk_analyzer.validate_configuration()
        
        return {
            "validation_result": validation_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration validation failed: {str(e)}")


@router.get("/tender/{tender_id}/risk-history")
async def get_tender_risk_history(
    tender_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get risk analysis history for a specific tender"""
    
    # Get tender
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    try:
        # Get risk score history
        risk_history = db.query(TenderRiskScore).filter(
            TenderRiskScore.tender_id == tender_id
        ).order_by(TenderRiskScore.analysis_date.desc()).all()
        
        history_data = []
        for score in risk_history:
            history_data.append({
                "analysis_date": score.analysis_date.isoformat(),
                "overall_risk_score": float(score.overall_risk_score),
                "risk_level": score.risk_level,
                "single_bidder_risk": float(score.single_bidder_risk) if score.single_bidder_risk else None,
                "price_anomaly_risk": float(score.price_anomaly_risk) if score.price_anomaly_risk else None,
                "frequency_risk": float(score.frequency_risk) if score.frequency_risk else None,
                "geographic_risk": float(score.geographic_risk) if score.geographic_risk else None,
                "risk_flags": score.risk_flags,
                "analysis_version": score.analysis_version
            })
        
        return {
            "tender_id": tender_id,
            "tender_title": tender.title,
            "risk_history": history_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get risk history: {str(e)}")


@router.get("/reports/summary")
async def get_risk_summary_report(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    risk_analyzer: RiskAnalyzer = Depends(get_risk_analyzer)
):
    """Get a summary risk report for the specified period"""
    
    try:
        # Get statistics
        stats = risk_analyzer.get_risk_statistics(db, days)
        
        # Get high-risk tenders
        high_risk_tenders = risk_analyzer.get_high_risk_tenders(db, limit=10)
        
        # Get algorithm performance
        algorithm_performance = risk_analyzer.get_algorithm_performance(db)
        
        # Generate summary report
        report = {
            "report_type": "summary",
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat(),
            "statistics": stats,
            "top_high_risk_tenders": high_risk_tenders,
            "algorithm_performance": algorithm_performance,
            "recommendations": _generate_report_recommendations(stats, high_risk_tenders)
        }
        
        return {"report": report}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary report: {str(e)}")


def _generate_report_recommendations(stats: Dict[str, Any], 
                                   high_risk_tenders: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations based on risk analysis"""
    
    recommendations = []
    
    # High-risk rate recommendations
    high_risk_rate = stats.get("high_risk_rate", 0)
    if high_risk_rate > 15:
        recommendations.append("High-risk tender rate is elevated (>15%). Consider increased oversight.")
    elif high_risk_rate > 25:
        recommendations.append("Critical: High-risk tender rate is very high (>25%). Immediate action required.")
    
    # Average score recommendations
    avg_score = stats.get("avg_overall_score", 0)
    if avg_score > 50:
        recommendations.append("Average risk score is elevated. Review procurement processes.")
    
    # High-value tender recommendations
    high_value_high_risk = sum(
        1 for tender in high_risk_tenders 
        if tender.get("estimated_value", 0) and tender["estimated_value"] > 1000000
    )
    
    if high_value_high_risk > 0:
        recommendations.append(f"{high_value_high_risk} high-value tenders flagged as high-risk. Priority review recommended.")
    
    # Algorithm performance recommendations
    algorithm_performance = stats.get("algorithm_performance", {})
    for algorithm, performance in algorithm_performance.items():
        if performance.get("high_risk_count", 0) > performance.get("total_analyses", 1) * 0.2:
            recommendations.append(f"{algorithm} algorithm detecting high risk in >20% of cases. Review algorithm parameters.")
    
    return recommendations