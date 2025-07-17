"""
Risk Analyzer

Main orchestrator for the risk detection system that manages all algorithms
and provides a unified interface for risk analysis.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import logging

from app.db.models import Tender, TenderRiskScore, RiskAlgorithm, RiskAlert
from app.core.database import get_db
from .base import RiskDetectionConfig, RiskDetectionResult, RiskAnalysisCache
from .composite_risk_scorer import CompositeRiskScorer

logger = logging.getLogger(__name__)


class RiskAnalyzer:
    """Main risk analysis orchestrator"""
    
    def __init__(self, config: Optional[RiskDetectionConfig] = None, redis_client=None):
        self.config = config or RiskDetectionConfig()
        self.composite_scorer = CompositeRiskScorer(self.config)
        self.cache = RiskAnalysisCache(redis_client)
        self.version = "1.0.0"
    
    def analyze_tender(self, tender: Tender, db: Session, 
                      force_refresh: bool = False) -> RiskDetectionResult:
        """Analyze a single tender for risk factors"""
        
        try:
            # Check cache first
            cache_key = f"risk_analysis:{tender.id}:{self.version}"
            
            if not force_refresh:
                cached_result = self.cache.get_cached_result(cache_key)
                if cached_result:
                    logger.info(f"Using cached risk analysis for tender {tender.id}")
                    return RiskDetectionResult(
                        risk_score=cached_result["risk_score"],
                        risk_level=cached_result["risk_level"],
                        risk_flags=cached_result["risk_flags"],
                        detailed_analysis=cached_result["detailed_analysis"],
                        confidence=cached_result.get("confidence", 1.0)
                    )
            
            # Perform analysis
            logger.info(f"Starting risk analysis for tender {tender.id}")
            result = self.composite_scorer.analyze_tender(tender, db)
            
            # Save to database
            self._save_analysis_result(tender, result, db)
            
            # Cache result
            self.cache.cache_result(cache_key, result.to_dict())
            
            # Generate alerts if necessary
            self._generate_alerts(tender, result, db)
            
            logger.info(f"Risk analysis completed for tender {tender.id}: {result.risk_level} ({result.risk_score:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing tender {tender.id}: {str(e)}")
            raise
    
    def analyze_batch(self, tenders: List[Tender], db: Session) -> List[RiskDetectionResult]:
        """Analyze multiple tenders for risk factors"""
        
        logger.info(f"Starting batch risk analysis for {len(tenders)} tenders")
        
        try:
            # Perform batch analysis
            results = self.composite_scorer.analyze_batch(tenders, db)
            
            # Save results and generate alerts
            for tender, result in zip(tenders, results):
                self._save_analysis_result(tender, result, db)
                self._generate_alerts(tender, result, db)
            
            logger.info(f"Batch risk analysis completed for {len(tenders)} tenders")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch analysis: {str(e)}")
            raise
    
    def analyze_recent_tenders(self, db: Session, days: int = 30) -> List[RiskDetectionResult]:
        """Analyze tenders from the last N days"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        recent_tenders = db.query(Tender).filter(
            Tender.publication_date >= cutoff_date
        ).all()
        
        logger.info(f"Analyzing {len(recent_tenders)} tenders from last {days} days")
        
        return self.analyze_batch(recent_tenders, db)
    
    def get_risk_statistics(self, db: Session, days: int = 30) -> Dict[str, Any]:
        """Get risk statistics for the specified period"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get risk scores from the period
        risk_scores = db.query(TenderRiskScore).filter(
            TenderRiskScore.analysis_date >= cutoff_date
        ).all()
        
        if not risk_scores:
            return {
                "period_days": days,
                "total_analyzed": 0,
                "message": "No risk analyses found for the specified period"
            }
        
        # Calculate statistics
        total_analyzed = len(risk_scores)
        risk_level_counts = {
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "MINIMAL": 0
        }
        
        algorithm_stats = {
            "single_bidder": {"total": 0, "avg_score": 0},
            "price_anomaly": {"total": 0, "avg_score": 0},
            "frequent_winner": {"total": 0, "avg_score": 0},
            "geographic_clustering": {"total": 0, "avg_score": 0}
        }
        
        total_overall_score = 0
        flag_counts = {}
        
        for score in risk_scores:
            # Risk level counts
            risk_level_counts[score.risk_level] += 1
            
            # Overall score
            total_overall_score += float(score.overall_risk_score)
            
            # Algorithm scores
            if score.single_bidder_risk:
                algorithm_stats["single_bidder"]["total"] += float(score.single_bidder_risk)
            if score.price_anomaly_risk:
                algorithm_stats["price_anomaly"]["total"] += float(score.price_anomaly_risk)
            if score.frequency_risk:
                algorithm_stats["frequent_winner"]["total"] += float(score.frequency_risk)
            if score.geographic_risk:
                algorithm_stats["geographic_clustering"]["total"] += float(score.geographic_risk)
            
            # Flag counts
            for flag in score.risk_flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
        
        # Calculate averages
        avg_overall_score = total_overall_score / total_analyzed
        
        for algorithm in algorithm_stats:
            algorithm_stats[algorithm]["avg_score"] = algorithm_stats[algorithm]["total"] / total_analyzed
        
        # Calculate percentages
        risk_level_percentages = {
            level: (count / total_analyzed) * 100 
            for level, count in risk_level_counts.items()
        }
        
        # Top flags
        top_flags = sorted(flag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "period_days": days,
            "total_analyzed": total_analyzed,
            "avg_overall_score": round(avg_overall_score, 2),
            "risk_level_distribution": {
                "counts": risk_level_counts,
                "percentages": risk_level_percentages
            },
            "algorithm_performance": algorithm_stats,
            "top_risk_flags": top_flags,
            "high_risk_rate": risk_level_percentages["HIGH"],
            "analysis_date": datetime.utcnow().isoformat()
        }
    
    def get_high_risk_tenders(self, db: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the highest risk tenders"""
        
        high_risk_scores = db.query(TenderRiskScore).join(Tender).filter(
            TenderRiskScore.risk_level == "HIGH"
        ).order_by(desc(TenderRiskScore.overall_risk_score)).limit(limit).all()
        
        results = []
        for score in high_risk_scores:
            tender_info = {
                "tender_id": str(score.tender_id),
                "title": score.tender.title,
                "contracting_authority": score.tender.contracting_authority.name if score.tender.contracting_authority else None,
                "estimated_value": float(score.tender.estimated_value) if score.tender.estimated_value else None,
                "overall_risk_score": float(score.overall_risk_score),
                "risk_level": score.risk_level,
                "risk_flags": score.risk_flags,
                "analysis_date": score.analysis_date.isoformat(),
                "publication_date": score.tender.publication_date.isoformat() if score.tender.publication_date else None
            }
            results.append(tender_info)
        
        return results
    
    def get_algorithm_performance(self, db: Session) -> Dict[str, Any]:
        """Get performance metrics for each algorithm"""
        
        # Get algorithm configurations
        algorithms = db.query(RiskAlgorithm).filter(
            RiskAlgorithm.is_active == True
        ).all()
        
        performance_data = {}
        
        for algorithm in algorithms:
            # Get recent analyses
            recent_scores = db.query(TenderRiskScore).filter(
                TenderRiskScore.analysis_date >= datetime.utcnow() - timedelta(days=30)
            ).all()
            
            if algorithm.algorithm_type == "single_bidder":
                scores = [float(s.single_bidder_risk) for s in recent_scores if s.single_bidder_risk]
            elif algorithm.algorithm_type == "price_anomaly":
                scores = [float(s.price_anomaly_risk) for s in recent_scores if s.price_anomaly_risk]
            elif algorithm.algorithm_type == "frequent_winner":
                scores = [float(s.frequency_risk) for s in recent_scores if s.frequency_risk]
            elif algorithm.algorithm_type == "geographic_clustering":
                scores = [float(s.geographic_risk) for s in recent_scores if s.geographic_risk]
            else:
                scores = []
            
            if scores:
                performance_data[algorithm.algorithm_type] = {
                    "avg_score": sum(scores) / len(scores),
                    "max_score": max(scores),
                    "min_score": min(scores),
                    "total_analyses": len(scores),
                    "high_risk_count": sum(1 for s in scores if s > 70),
                    "medium_risk_count": sum(1 for s in scores if 40 <= s <= 70),
                    "low_risk_count": sum(1 for s in scores if s < 40)
                }
        
        return performance_data
    
    def reanalyze_tender(self, tender_id: str, db: Session) -> RiskDetectionResult:
        """Reanalyze a specific tender with fresh data"""
        
        tender = db.query(Tender).filter(Tender.id == tender_id).first()
        if not tender:
            raise ValueError(f"Tender with ID {tender_id} not found")
        
        # Delete existing analysis
        db.query(TenderRiskScore).filter(
            TenderRiskScore.tender_id == tender_id
        ).delete()
        
        # Perform fresh analysis
        result = self.analyze_tender(tender, db, force_refresh=True)
        
        logger.info(f"Reanalyzed tender {tender_id}: {result.risk_level} ({result.risk_score:.2f})")
        
        return result
    
    def _save_analysis_result(self, tender: Tender, result: RiskDetectionResult, db: Session):
        """Save analysis result to database"""
        
        try:
            # Delete existing analysis for this tender
            db.query(TenderRiskScore).filter(
                TenderRiskScore.tender_id == tender.id
            ).delete()
            
            # Save new analysis
            risk_score = self.composite_scorer.save_risk_score(tender, result, db)
            
            logger.debug(f"Saved risk analysis for tender {tender.id}")
            
        except Exception as e:
            logger.error(f"Error saving risk analysis for tender {tender.id}: {str(e)}")
            raise
    
    def _generate_alerts(self, tender: Tender, result: RiskDetectionResult, db: Session):
        """Generate alerts for high-risk tenders"""
        
        if result.risk_level not in ["HIGH", "MEDIUM"]:
            return
        
        try:
            # Check if alert already exists
            existing_alert = db.query(RiskAlert).filter(
                and_(
                    RiskAlert.tender_id == tender.id,
                    RiskAlert.alert_type == "risk_detection"
                )
            ).first()
            
            if existing_alert:
                return  # Alert already exists
            
            # Create alert title and message
            alert_title = f"{result.risk_level} Risk Detected: {tender.title[:100]}..."
            
            alert_message = f"""
            Risk Level: {result.risk_level}
            Risk Score: {result.risk_score:.2f}
            
            Primary Risk Factors:
            {', '.join(result.risk_flags[:5])}
            
            Contracting Authority: {tender.contracting_authority.name if tender.contracting_authority else 'Unknown'}
            Estimated Value: {tender.estimated_value if tender.estimated_value else 'Not specified'}
            
            This tender has been flagged for potential corruption or irregularities.
            Please review the detailed analysis for more information.
            """
            
            # Note: In a real implementation, you would get user IDs from a subscription system
            # For now, we'll create a placeholder that can be expanded
            
            logger.info(f"Generated {result.risk_level} risk alert for tender {tender.id}")
            
        except Exception as e:
            logger.error(f"Error generating alert for tender {tender.id}: {str(e)}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get information about the risk detection system"""
        
        return {
            "system_version": self.version,
            "composite_scorer_info": self.composite_scorer.get_algorithm_info(),
            "configuration": {
                "single_bidder_threshold": self.config.single_bidder_threshold,
                "price_anomaly_z_threshold": self.config.price_anomaly_z_threshold,
                "frequent_winner_threshold": self.config.frequent_winner_threshold,
                "geographic_clustering_threshold": self.config.geographic_clustering_threshold,
                "high_risk_threshold": self.config.high_risk_threshold,
                "medium_risk_threshold": self.config.medium_risk_threshold,
                "low_risk_threshold": self.config.low_risk_threshold
            },
            "analysis_windows": {
                "analysis_window_months": self.config.analysis_window_months,
                "historical_data_years": self.config.historical_data_years
            },
            "min_sample_sizes": {
                "price_analysis": self.config.min_sample_size_price_analysis,
                "frequency_analysis": self.config.min_sample_size_frequency_analysis,
                "geographic_analysis": self.config.min_sample_size_geographic_analysis
            }
        }
    
    def update_configuration(self, new_config: Dict[str, Any]):
        """Update risk detection configuration"""
        
        # Update configuration
        for key, value in new_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Recreate composite scorer with new configuration
        self.composite_scorer = CompositeRiskScorer(self.config)
        
        logger.info("Risk detection configuration updated")
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current configuration"""
        
        issues = []
        warnings = []
        
        # Check thresholds
        if self.config.high_risk_threshold <= self.config.medium_risk_threshold:
            issues.append("High risk threshold must be greater than medium risk threshold")
        
        if self.config.medium_risk_threshold <= self.config.low_risk_threshold:
            issues.append("Medium risk threshold must be greater than low risk threshold")
        
        # Check weights
        total_weight = (self.config.single_bidder_weight + 
                       self.config.price_anomaly_weight + 
                       self.config.frequent_winner_weight + 
                       self.config.geographic_clustering_weight)
        
        if abs(total_weight - 1.0) > 0.01:
            warnings.append(f"Algorithm weights sum to {total_weight}, not 1.0")
        
        # Check sample sizes
        if self.config.min_sample_size_price_analysis < 5:
            warnings.append("Price analysis sample size is very small")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }