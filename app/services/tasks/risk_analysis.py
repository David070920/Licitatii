"""
Risk Analysis Background Tasks

This module provides background tasks for periodic risk assessment,
automated risk detection, and risk monitoring.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from celery import Celery
from celery.utils.log import get_task_logger
import redis

from app.core.database import SessionLocal
from app.db.models import Tender, TenderRiskScore, RiskAlert, DataIngestionLog
from app.services.risk_detection.risk_analyzer import RiskAnalyzer
from app.services.risk_detection.base import RiskDetectionConfig
from app.services.celery_app import celery_app

logger = get_task_logger(__name__)


# Risk analysis tasks
@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def analyze_new_tenders(self, batch_size: int = 100):
    """Analyze newly ingested tenders for risk factors"""
    
    db = SessionLocal()
    try:
        logger.info("Starting analysis of new tenders")
        
        # Get tenders without risk analysis
        unanalyzed_tenders = db.query(Tender).outerjoin(TenderRiskScore).filter(
            TenderRiskScore.id.is_(None)
        ).limit(batch_size).all()
        
        if not unanalyzed_tenders:
            logger.info("No new tenders to analyze")
            return {"message": "No new tenders to analyze", "processed": 0}
        
        # Initialize risk analyzer
        config = RiskDetectionConfig()
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        risk_analyzer = RiskAnalyzer(config, redis_client)
        
        # Analyze tenders
        results = risk_analyzer.analyze_batch(unanalyzed_tenders, db)
        
        # Count results by risk level
        risk_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "MINIMAL": 0}
        for result in results:
            risk_counts[result.risk_level] += 1
        
        logger.info(f"Analyzed {len(unanalyzed_tenders)} tenders: {risk_counts}")
        
        return {
            "message": "Analysis completed successfully",
            "processed": len(unanalyzed_tenders),
            "risk_distribution": risk_counts
        }
        
    except Exception as e:
        logger.error(f"Error analyzing new tenders: {str(e)}")
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def periodic_risk_assessment(self, days_lookback: int = 30):
    """Perform periodic risk assessment of recent tenders"""
    
    db = SessionLocal()
    try:
        logger.info(f"Starting periodic risk assessment for last {days_lookback} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_lookback)
        
        # Get tenders from the period
        recent_tenders = db.query(Tender).filter(
            Tender.publication_date >= cutoff_date
        ).all()
        
        if not recent_tenders:
            logger.info("No recent tenders found for assessment")
            return {"message": "No recent tenders found", "processed": 0}
        
        # Initialize risk analyzer
        config = RiskDetectionConfig()
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        risk_analyzer = RiskAnalyzer(config, redis_client)
        
        # Get statistics before analysis
        stats_before = risk_analyzer.get_risk_statistics(db, days_lookback)
        
        # Reanalyze tenders with updated algorithms
        processed = 0
        for tender in recent_tenders:
            try:
                risk_analyzer.analyze_tender(tender, db, force_refresh=True)
                processed += 1
            except Exception as e:
                logger.warning(f"Error analyzing tender {tender.id}: {str(e)}")
                continue
        
        # Get statistics after analysis
        stats_after = risk_analyzer.get_risk_statistics(db, days_lookback)
        
        logger.info(f"Periodic assessment completed: {processed} tenders processed")
        
        return {
            "message": "Periodic assessment completed",
            "processed": processed,
            "stats_before": stats_before,
            "stats_after": stats_after
        }
        
    except Exception as e:
        logger.error(f"Error in periodic risk assessment: {str(e)}")
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def analyze_high_value_tenders(self, value_threshold: float = 1000000.0):
    """Analyze high-value tenders with enhanced scrutiny"""
    
    db = SessionLocal()
    try:
        logger.info(f"Analyzing high-value tenders (threshold: {value_threshold} RON)")
        
        # Get high-value tenders from last 90 days
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        high_value_tenders = db.query(Tender).filter(
            and_(
                Tender.estimated_value >= value_threshold,
                Tender.publication_date >= cutoff_date
            )
        ).all()
        
        if not high_value_tenders:
            logger.info("No high-value tenders found")
            return {"message": "No high-value tenders found", "processed": 0}
        
        # Initialize risk analyzer with enhanced configuration
        config = RiskDetectionConfig()
        # Lower thresholds for high-value tenders
        config.high_risk_threshold = 60.0  # More sensitive
        config.medium_risk_threshold = 30.0
        
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        risk_analyzer = RiskAnalyzer(config, redis_client)
        
        # Analyze high-value tenders
        results = risk_analyzer.analyze_batch(high_value_tenders, db)
        
        # Count high-risk results
        high_risk_count = sum(1 for result in results if result.risk_level == "HIGH")
        medium_risk_count = sum(1 for result in results if result.risk_level == "MEDIUM")
        
        logger.info(f"High-value analysis completed: {high_risk_count} high-risk, {medium_risk_count} medium-risk")
        
        return {
            "message": "High-value tender analysis completed",
            "processed": len(high_value_tenders),
            "high_risk_count": high_risk_count,
            "medium_risk_count": medium_risk_count,
            "value_threshold": value_threshold
        }
        
    except Exception as e:
        logger.error(f"Error analyzing high-value tenders: {str(e)}")
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def monitor_risk_trends(self, period_days: int = 30):
    """Monitor risk trends and generate trend reports"""
    
    db = SessionLocal()
    try:
        logger.info(f"Monitoring risk trends for {period_days} days")
        
        # Get risk scores for the period
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        risk_scores = db.query(TenderRiskScore).filter(
            TenderRiskScore.analysis_date >= cutoff_date
        ).order_by(TenderRiskScore.analysis_date).all()
        
        if not risk_scores:
            logger.info("No risk scores found for trend analysis")
            return {"message": "No risk scores found", "processed": 0}
        
        # Analyze trends
        trends = _analyze_risk_trends(risk_scores)
        
        # Check for concerning trends
        alerts = _check_trend_alerts(trends)
        
        # Store trend analysis results
        _store_trend_analysis(trends, alerts, db)
        
        logger.info(f"Risk trend analysis completed: {len(alerts)} alerts generated")
        
        return {
            "message": "Risk trend monitoring completed",
            "processed": len(risk_scores),
            "trends": trends,
            "alerts_generated": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"Error monitoring risk trends: {str(e)}")
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def cleanup_old_risk_data(self, retention_days: int = 365):
    """Clean up old risk analysis data"""
    
    db = SessionLocal()
    try:
        logger.info(f"Cleaning up risk data older than {retention_days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Delete old risk scores
        old_scores = db.query(TenderRiskScore).filter(
            TenderRiskScore.analysis_date < cutoff_date
        ).delete()
        
        # Delete old risk alerts
        old_alerts = db.query(RiskAlert).filter(
            RiskAlert.created_at < cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleanup completed: {old_scores} scores, {old_alerts} alerts deleted")
        
        return {
            "message": "Risk data cleanup completed",
            "deleted_scores": old_scores,
            "deleted_alerts": old_alerts,
            "retention_days": retention_days
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old risk data: {str(e)}")
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def generate_risk_reports(self, report_type: str = "weekly"):
    """Generate periodic risk reports"""
    
    db = SessionLocal()
    try:
        logger.info(f"Generating {report_type} risk report")
        
        # Determine period based on report type
        if report_type == "daily":
            days = 1
        elif report_type == "weekly":
            days = 7
        elif report_type == "monthly":
            days = 30
        else:
            days = 7
        
        # Initialize risk analyzer
        config = RiskDetectionConfig()
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        risk_analyzer = RiskAnalyzer(config, redis_client)
        
        # Get risk statistics
        stats = risk_analyzer.get_risk_statistics(db, days)
        
        # Get high-risk tenders
        high_risk_tenders = risk_analyzer.get_high_risk_tenders(db, limit=20)
        
        # Get algorithm performance
        algorithm_performance = risk_analyzer.get_algorithm_performance(db)
        
        # Generate report
        report = {
            "report_type": report_type,
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat(),
            "statistics": stats,
            "high_risk_tenders": high_risk_tenders,
            "algorithm_performance": algorithm_performance
        }
        
        # Store report (in a real implementation, this would be saved to a reports table)
        logger.info(f"Generated {report_type} risk report with {len(high_risk_tenders)} high-risk tenders")
        
        return {
            "message": f"{report_type.capitalize()} risk report generated",
            "report": report
        }
        
    except Exception as e:
        logger.error(f"Error generating risk report: {str(e)}")
        raise self.retry(exc=e)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def update_risk_algorithm_weights(self, performance_data: Dict[str, float]):
    """Update algorithm weights based on performance data"""
    
    db = SessionLocal()
    try:
        logger.info("Updating risk algorithm weights")
        
        # Initialize risk analyzer
        config = RiskDetectionConfig()
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        risk_analyzer = RiskAnalyzer(config, redis_client)
        
        # Get current algorithm performance
        current_performance = risk_analyzer.get_algorithm_performance(db)
        
        # Calculate new weights based on performance
        new_weights = _calculate_optimal_weights(current_performance, performance_data)
        
        # Update configuration
        risk_analyzer.update_configuration(new_weights)
        
        logger.info(f"Updated algorithm weights: {new_weights}")
        
        return {
            "message": "Algorithm weights updated",
            "new_weights": new_weights,
            "previous_performance": current_performance
        }
        
    except Exception as e:
        logger.error(f"Error updating algorithm weights: {str(e)}")
        raise self.retry(exc=e)
    finally:
        db.close()


# Helper functions
def _analyze_risk_trends(risk_scores: List[TenderRiskScore]) -> Dict[str, Any]:
    """Analyze risk trends from historical data"""
    
    # Group by time periods
    daily_stats = {}
    weekly_stats = {}
    
    for score in risk_scores:
        date_key = score.analysis_date.date()
        week_key = score.analysis_date.strftime("%Y-W%U")
        
        # Daily stats
        if date_key not in daily_stats:
            daily_stats[date_key] = {"total": 0, "high": 0, "medium": 0, "avg_score": 0}
        
        daily_stats[date_key]["total"] += 1
        if score.risk_level == "HIGH":
            daily_stats[date_key]["high"] += 1
        elif score.risk_level == "MEDIUM":
            daily_stats[date_key]["medium"] += 1
        daily_stats[date_key]["avg_score"] += float(score.overall_risk_score)
        
        # Weekly stats
        if week_key not in weekly_stats:
            weekly_stats[week_key] = {"total": 0, "high": 0, "medium": 0, "avg_score": 0}
        
        weekly_stats[week_key]["total"] += 1
        if score.risk_level == "HIGH":
            weekly_stats[week_key]["high"] += 1
        elif score.risk_level == "MEDIUM":
            weekly_stats[week_key]["medium"] += 1
        weekly_stats[week_key]["avg_score"] += float(score.overall_risk_score)
    
    # Calculate averages
    for stats in daily_stats.values():
        if stats["total"] > 0:
            stats["avg_score"] /= stats["total"]
            stats["high_rate"] = stats["high"] / stats["total"]
            stats["medium_rate"] = stats["medium"] / stats["total"]
    
    for stats in weekly_stats.values():
        if stats["total"] > 0:
            stats["avg_score"] /= stats["total"]
            stats["high_rate"] = stats["high"] / stats["total"]
            stats["medium_rate"] = stats["medium"] / stats["total"]
    
    return {
        "daily_trends": daily_stats,
        "weekly_trends": weekly_stats
    }


def _check_trend_alerts(trends: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check for concerning trends and generate alerts"""
    
    alerts = []
    
    # Check daily trends
    daily_trends = trends.get("daily_trends", {})
    if daily_trends:
        recent_days = sorted(daily_trends.keys())[-7:]  # Last 7 days
        recent_high_rates = [daily_trends[day]["high_rate"] for day in recent_days]
        
        # Alert if high-risk rate is consistently increasing
        if len(recent_high_rates) >= 3:
            if all(recent_high_rates[i] <= recent_high_rates[i+1] for i in range(len(recent_high_rates)-1)):
                alerts.append({
                    "type": "trend_alert",
                    "severity": "HIGH",
                    "message": "High-risk tender rate is consistently increasing",
                    "data": {"recent_high_rates": recent_high_rates}
                })
        
        # Alert if average risk score is too high
        recent_avg_scores = [daily_trends[day]["avg_score"] for day in recent_days]
        if recent_avg_scores and max(recent_avg_scores) > 60:
            alerts.append({
                "type": "score_alert",
                "severity": "MEDIUM",
                "message": "Average risk score is elevated",
                "data": {"max_avg_score": max(recent_avg_scores)}
            })
    
    return alerts


def _store_trend_analysis(trends: Dict[str, Any], alerts: List[Dict[str, Any]], db: Session):
    """Store trend analysis results"""
    
    # In a real implementation, this would save to a trends table
    # For now, we'll log the results
    logger.info(f"Trend analysis completed with {len(alerts)} alerts")
    
    for alert in alerts:
        logger.warning(f"Trend alert: {alert['message']}")


def _calculate_optimal_weights(current_performance: Dict[str, Any], 
                             performance_data: Dict[str, float]) -> Dict[str, float]:
    """Calculate optimal algorithm weights based on performance"""
    
    # Simple weight adjustment based on performance
    base_weights = {
        "single_bidder_weight": 0.25,
        "price_anomaly_weight": 0.30,
        "frequent_winner_weight": 0.25,
        "geographic_clustering_weight": 0.20
    }
    
    # Adjust weights based on performance (simplified approach)
    for algorithm, performance in performance_data.items():
        weight_key = f"{algorithm}_weight"
        if weight_key in base_weights:
            # Increase weight for better performing algorithms
            if performance > 0.8:
                base_weights[weight_key] *= 1.1
            elif performance < 0.6:
                base_weights[weight_key] *= 0.9
    
    # Normalize weights
    total_weight = sum(base_weights.values())
    normalized_weights = {k: v/total_weight for k, v in base_weights.items()}
    
    return normalized_weights


# Scheduled task configurations
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Set up periodic tasks"""
    
    # Analyze new tenders every 30 minutes
    sender.add_periodic_task(
        1800.0,  # 30 minutes
        analyze_new_tenders.s(),
        name='analyze_new_tenders'
    )
    
    # Periodic risk assessment daily at 2 AM
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        periodic_risk_assessment.s(),
        name='periodic_risk_assessment'
    )
    
    # High-value tender analysis every 6 hours
    sender.add_periodic_task(
        21600.0,  # 6 hours
        analyze_high_value_tenders.s(),
        name='analyze_high_value_tenders'
    )
    
    # Risk trend monitoring daily at 3 AM
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        monitor_risk_trends.s(),
        name='monitor_risk_trends'
    )
    
    # Generate weekly reports on Mondays at 9 AM
    sender.add_periodic_task(
        crontab(hour=9, minute=0, day_of_week=1),
        generate_risk_reports.s("weekly"),
        name='generate_weekly_reports'
    )
    
    # Cleanup old data monthly
    sender.add_periodic_task(
        crontab(hour=1, minute=0, day_of_month=1),
        cleanup_old_risk_data.s(),
        name='cleanup_old_risk_data'
    )


from celery.schedules import crontab