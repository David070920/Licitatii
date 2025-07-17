"""
Data quality monitoring and alerting system
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import statistics
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.core.logging import logger
from app.db.models import (
    Tender, DataIngestionLog, ContractingAuthority, 
    Company, TenderBid, TenderAward
)


class DataQualityLevel(Enum):
    """Data quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class DataQualityMetric:
    """Data quality metric"""
    name: str
    value: float
    threshold: float
    level: DataQualityLevel
    description: str
    details: Dict[str, Any]
    measured_at: datetime


@dataclass
class DataQualityReport:
    """Data quality report"""
    source_system: str
    overall_score: float
    overall_level: DataQualityLevel
    metrics: List[DataQualityMetric]
    recommendations: List[str]
    generated_at: datetime
    time_period: Tuple[datetime, datetime]


class DataQualityMonitor:
    """Comprehensive data quality monitoring system"""
    
    def __init__(self):
        self.quality_thresholds = {
            'completeness': {
                'excellent': 0.95,
                'good': 0.85,
                'fair': 0.70,
                'poor': 0.50,
                'critical': 0.0
            },
            'accuracy': {
                'excellent': 0.98,
                'good': 0.90,
                'fair': 0.80,
                'poor': 0.60,
                'critical': 0.0
            },
            'consistency': {
                'excellent': 0.95,
                'good': 0.85,
                'fair': 0.75,
                'poor': 0.60,
                'critical': 0.0
            },
            'timeliness': {
                'excellent': 0.90,
                'good': 0.80,
                'fair': 0.70,
                'poor': 0.50,
                'critical': 0.0
            },
            'uniqueness': {
                'excellent': 0.98,
                'good': 0.90,
                'fair': 0.80,
                'poor': 0.60,
                'critical': 0.0
            }
        }
    
    async def generate_quality_report(
        self,
        source_system: str,
        days_back: int = 7
    ) -> DataQualityReport:
        """Generate comprehensive data quality report"""
        
        logger.info(f"Generating data quality report for {source_system}")
        
        # Define time period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Calculate all quality metrics
        metrics = []
        
        # Completeness metrics
        completeness_metrics = await self._calculate_completeness_metrics(
            source_system, start_date, end_date
        )
        metrics.extend(completeness_metrics)
        
        # Accuracy metrics
        accuracy_metrics = await self._calculate_accuracy_metrics(
            source_system, start_date, end_date
        )
        metrics.extend(accuracy_metrics)
        
        # Consistency metrics
        consistency_metrics = await self._calculate_consistency_metrics(
            source_system, start_date, end_date
        )
        metrics.extend(consistency_metrics)
        
        # Timeliness metrics
        timeliness_metrics = await self._calculate_timeliness_metrics(
            source_system, start_date, end_date
        )
        metrics.extend(timeliness_metrics)
        
        # Uniqueness metrics
        uniqueness_metrics = await self._calculate_uniqueness_metrics(
            source_system, start_date, end_date
        )
        metrics.extend(uniqueness_metrics)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(metrics)
        overall_level = self._determine_quality_level(overall_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics)
        
        return DataQualityReport(
            source_system=source_system,
            overall_score=overall_score,
            overall_level=overall_level,
            metrics=metrics,
            recommendations=recommendations,
            generated_at=datetime.now(),
            time_period=(start_date, end_date)
        )
    
    async def _calculate_completeness_metrics(
        self,
        source_system: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[DataQualityMetric]:
        """Calculate data completeness metrics"""
        
        metrics = []
        
        try:
            async with get_async_session() as session:
                # Get all tenders in the period
                result = await session.execute(
                    select(Tender).where(
                        and_(
                            Tender.source_system == source_system,
                            Tender.created_at >= start_date,
                            Tender.created_at <= end_date
                        )
                    )
                )
                
                tenders = result.scalars().all()
                total_tenders = len(tenders)
                
                if total_tenders == 0:
                    return metrics
                
                # Check completeness of key fields
                required_fields = {
                    'title': 'Title completeness',
                    'description': 'Description completeness',
                    'estimated_value': 'Estimated value completeness',
                    'publication_date': 'Publication date completeness',
                    'submission_deadline': 'Submission deadline completeness',
                    'contracting_authority_id': 'Contracting authority completeness'
                }
                
                for field, description in required_fields.items():
                    complete_count = sum(
                        1 for tender in tenders 
                        if getattr(tender, field) is not None and getattr(tender, field) != ''
                    )
                    
                    completeness_score = complete_count / total_tenders
                    level = self._determine_completeness_level(completeness_score)
                    
                    metrics.append(DataQualityMetric(
                        name=f"{field}_completeness",
                        value=completeness_score,
                        threshold=self.quality_thresholds['completeness']['good'],
                        level=level,
                        description=description,
                        details={
                            'total_records': total_tenders,
                            'complete_records': complete_count,
                            'incomplete_records': total_tenders - complete_count
                        },
                        measured_at=datetime.now()
                    ))
                
        except Exception as e:
            logger.error(f"Error calculating completeness metrics: {str(e)}")
        
        return metrics
    
    async def _calculate_accuracy_metrics(
        self,
        source_system: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[DataQualityMetric]:
        """Calculate data accuracy metrics"""
        
        metrics = []
        
        try:
            async with get_async_session() as session:
                # Get tenders with validation data
                result = await session.execute(
                    select(Tender).where(
                        and_(
                            Tender.source_system == source_system,
                            Tender.created_at >= start_date,
                            Tender.created_at <= end_date
                        )
                    )
                )
                
                tenders = result.scalars().all()
                total_tenders = len(tenders)
                
                if total_tenders == 0:
                    return metrics
                
                # Check data format accuracy
                valid_email_count = 0
                total_emails = 0
                
                valid_cui_count = 0
                total_cui = 0
                
                valid_date_count = 0
                total_dates = 0
                
                for tender in tenders:
                    # Check contracting authority data
                    if tender.contracting_authority:
                        if tender.contracting_authority.contact_email:
                            total_emails += 1
                            if self._is_valid_email(tender.contracting_authority.contact_email):
                                valid_email_count += 1
                        
                        if tender.contracting_authority.cui:
                            total_cui += 1
                            if self._is_valid_cui(tender.contracting_authority.cui):
                                valid_cui_count += 1
                    
                    # Check date consistency
                    if tender.publication_date and tender.submission_deadline:
                        total_dates += 1
                        if tender.submission_deadline > tender.publication_date:
                            valid_date_count += 1
                
                # Email accuracy
                if total_emails > 0:
                    email_accuracy = valid_email_count / total_emails
                    metrics.append(DataQualityMetric(
                        name="email_accuracy",
                        value=email_accuracy,
                        threshold=self.quality_thresholds['accuracy']['good'],
                        level=self._determine_accuracy_level(email_accuracy),
                        description="Email format accuracy",
                        details={
                            'total_emails': total_emails,
                            'valid_emails': valid_email_count,
                            'invalid_emails': total_emails - valid_email_count
                        },
                        measured_at=datetime.now()
                    ))
                
                # CUI accuracy
                if total_cui > 0:
                    cui_accuracy = valid_cui_count / total_cui
                    metrics.append(DataQualityMetric(
                        name="cui_accuracy",
                        value=cui_accuracy,
                        threshold=self.quality_thresholds['accuracy']['good'],
                        level=self._determine_accuracy_level(cui_accuracy),
                        description="CUI format accuracy",
                        details={
                            'total_cui': total_cui,
                            'valid_cui': valid_cui_count,
                            'invalid_cui': total_cui - valid_cui_count
                        },
                        measured_at=datetime.now()
                    ))
                
                # Date consistency accuracy
                if total_dates > 0:
                    date_accuracy = valid_date_count / total_dates
                    metrics.append(DataQualityMetric(
                        name="date_consistency",
                        value=date_accuracy,
                        threshold=self.quality_thresholds['accuracy']['good'],
                        level=self._determine_accuracy_level(date_accuracy),
                        description="Date consistency accuracy",
                        details={
                            'total_date_pairs': total_dates,
                            'consistent_dates': valid_date_count,
                            'inconsistent_dates': total_dates - valid_date_count
                        },
                        measured_at=datetime.now()
                    ))
                
        except Exception as e:
            logger.error(f"Error calculating accuracy metrics: {str(e)}")
        
        return metrics
    
    async def _calculate_consistency_metrics(
        self,
        source_system: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[DataQualityMetric]:
        """Calculate data consistency metrics"""
        
        metrics = []
        
        try:
            async with get_async_session() as session:
                # Check for duplicate external IDs
                result = await session.execute(
                    select(
                        Tender.external_id,
                        func.count(Tender.id).label('count')
                    ).where(
                        and_(
                            Tender.source_system == source_system,
                            Tender.created_at >= start_date,
                            Tender.created_at <= end_date
                        )
                    ).group_by(Tender.external_id)
                )
                
                id_counts = result.all()
                total_unique_ids = len(id_counts)
                duplicate_ids = sum(1 for count in id_counts if count.count > 1)
                
                if total_unique_ids > 0:
                    uniqueness_score = (total_unique_ids - duplicate_ids) / total_unique_ids
                    
                    metrics.append(DataQualityMetric(
                        name="external_id_uniqueness",
                        value=uniqueness_score,
                        threshold=self.quality_thresholds['uniqueness']['good'],
                        level=self._determine_uniqueness_level(uniqueness_score),
                        description="External ID uniqueness",
                        details={
                            'total_unique_ids': total_unique_ids,
                            'duplicate_ids': duplicate_ids,
                            'uniqueness_percentage': uniqueness_score * 100
                        },
                        measured_at=datetime.now()
                    ))
                
                # Check status consistency
                result = await session.execute(
                    select(Tender).where(
                        and_(
                            Tender.source_system == source_system,
                            Tender.created_at >= start_date,
                            Tender.created_at <= end_date,
                            Tender.status.isnot(None)
                        )
                    )
                )
                
                tenders = result.scalars().all()
                total_with_status = len(tenders)
                
                if total_with_status > 0:
                    # Check for consistent status transitions
                    consistent_status_count = 0
                    
                    for tender in tenders:
                        is_consistent = self._is_status_consistent(tender)
                        if is_consistent:
                            consistent_status_count += 1
                    
                    status_consistency = consistent_status_count / total_with_status
                    
                    metrics.append(DataQualityMetric(
                        name="status_consistency",
                        value=status_consistency,
                        threshold=self.quality_thresholds['consistency']['good'],
                        level=self._determine_consistency_level(status_consistency),
                        description="Status consistency",
                        details={
                            'total_tenders': total_with_status,
                            'consistent_status': consistent_status_count,
                            'inconsistent_status': total_with_status - consistent_status_count
                        },
                        measured_at=datetime.now()
                    ))
                
        except Exception as e:
            logger.error(f"Error calculating consistency metrics: {str(e)}")
        
        return metrics
    
    async def _calculate_timeliness_metrics(
        self,
        source_system: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[DataQualityMetric]:
        """Calculate data timeliness metrics"""
        
        metrics = []
        
        try:
            async with get_async_session() as session:
                # Get ingestion logs
                result = await session.execute(
                    select(DataIngestionLog).where(
                        and_(
                            DataIngestionLog.source_system == source_system,
                            DataIngestionLog.started_at >= start_date,
                            DataIngestionLog.started_at <= end_date,
                            DataIngestionLog.status == 'completed'
                        )
                    )
                )
                
                logs = result.scalars().all()
                
                if logs:
                    # Calculate average ingestion time
                    ingestion_times = []
                    for log in logs:
                        if log.completed_at and log.started_at:
                            duration = (log.completed_at - log.started_at).total_seconds()
                            ingestion_times.append(duration)
                    
                    if ingestion_times:
                        avg_ingestion_time = statistics.mean(ingestion_times)
                        max_acceptable_time = 3600  # 1 hour
                        
                        timeliness_score = max(0, 1 - (avg_ingestion_time / max_acceptable_time))
                        
                        metrics.append(DataQualityMetric(
                            name="ingestion_timeliness",
                            value=timeliness_score,
                            threshold=self.quality_thresholds['timeliness']['good'],
                            level=self._determine_timeliness_level(timeliness_score),
                            description="Data ingestion timeliness",
                            details={
                                'average_ingestion_time': avg_ingestion_time,
                                'max_ingestion_time': max(ingestion_times),
                                'min_ingestion_time': min(ingestion_times),
                                'total_ingestions': len(ingestion_times)
                            },
                            measured_at=datetime.now()
                        ))
                
                # Check data freshness
                result = await session.execute(
                    select(Tender).where(
                        and_(
                            Tender.source_system == source_system,
                            Tender.created_at >= start_date,
                            Tender.created_at <= end_date
                        )
                    ).order_by(Tender.last_scraped_at.desc()).limit(1)
                )
                
                latest_tender = result.scalar_one_or_none()
                
                if latest_tender and latest_tender.last_scraped_at:
                    hours_since_last_scrape = (
                        datetime.now() - latest_tender.last_scraped_at
                    ).total_seconds() / 3600
                    
                    max_acceptable_hours = 24  # 24 hours
                    freshness_score = max(0, 1 - (hours_since_last_scrape / max_acceptable_hours))
                    
                    metrics.append(DataQualityMetric(
                        name="data_freshness",
                        value=freshness_score,
                        threshold=self.quality_thresholds['timeliness']['good'],
                        level=self._determine_timeliness_level(freshness_score),
                        description="Data freshness",
                        details={
                            'hours_since_last_scrape': hours_since_last_scrape,
                            'last_scrape_time': latest_tender.last_scraped_at.isoformat(),
                            'max_acceptable_hours': max_acceptable_hours
                        },
                        measured_at=datetime.now()
                    ))
                
        except Exception as e:
            logger.error(f"Error calculating timeliness metrics: {str(e)}")
        
        return metrics
    
    async def _calculate_uniqueness_metrics(
        self,
        source_system: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[DataQualityMetric]:
        """Calculate data uniqueness metrics"""
        
        metrics = []
        
        try:
            async with get_async_session() as session:
                # Check for duplicate tenders based on similarity
                result = await session.execute(
                    select(Tender).where(
                        and_(
                            Tender.source_system == source_system,
                            Tender.created_at >= start_date,
                            Tender.created_at <= end_date
                        )
                    ).options(selectinload(Tender.contracting_authority))
                )
                
                tenders = result.scalars().all()
                total_tenders = len(tenders)
                
                if total_tenders > 0:
                    # Simple duplicate detection based on title similarity
                    potential_duplicates = 0
                    
                    for i, tender1 in enumerate(tenders):
                        for tender2 in tenders[i+1:]:
                            if self._are_tenders_similar(tender1, tender2):
                                potential_duplicates += 1
                                break
                    
                    uniqueness_score = max(0, 1 - (potential_duplicates / total_tenders))
                    
                    metrics.append(DataQualityMetric(
                        name="tender_uniqueness",
                        value=uniqueness_score,
                        threshold=self.quality_thresholds['uniqueness']['good'],
                        level=self._determine_uniqueness_level(uniqueness_score),
                        description="Tender uniqueness",
                        details={
                            'total_tenders': total_tenders,
                            'potential_duplicates': potential_duplicates,
                            'unique_tenders': total_tenders - potential_duplicates
                        },
                        measured_at=datetime.now()
                    ))
                
        except Exception as e:
            logger.error(f"Error calculating uniqueness metrics: {str(e)}")
        
        return metrics
    
    def _determine_completeness_level(self, score: float) -> DataQualityLevel:
        """Determine completeness quality level"""
        return self._determine_quality_level_by_thresholds(score, 'completeness')
    
    def _determine_accuracy_level(self, score: float) -> DataQualityLevel:
        """Determine accuracy quality level"""
        return self._determine_quality_level_by_thresholds(score, 'accuracy')
    
    def _determine_consistency_level(self, score: float) -> DataQualityLevel:
        """Determine consistency quality level"""
        return self._determine_quality_level_by_thresholds(score, 'consistency')
    
    def _determine_timeliness_level(self, score: float) -> DataQualityLevel:
        """Determine timeliness quality level"""
        return self._determine_quality_level_by_thresholds(score, 'timeliness')
    
    def _determine_uniqueness_level(self, score: float) -> DataQualityLevel:
        """Determine uniqueness quality level"""
        return self._determine_quality_level_by_thresholds(score, 'uniqueness')
    
    def _determine_quality_level_by_thresholds(self, score: float, metric_type: str) -> DataQualityLevel:
        """Determine quality level based on thresholds"""
        thresholds = self.quality_thresholds[metric_type]
        
        if score >= thresholds['excellent']:
            return DataQualityLevel.EXCELLENT
        elif score >= thresholds['good']:
            return DataQualityLevel.GOOD
        elif score >= thresholds['fair']:
            return DataQualityLevel.FAIR
        elif score >= thresholds['poor']:
            return DataQualityLevel.POOR
        else:
            return DataQualityLevel.CRITICAL
    
    def _determine_quality_level(self, score: float) -> DataQualityLevel:
        """Determine overall quality level"""
        if score >= 0.90:
            return DataQualityLevel.EXCELLENT
        elif score >= 0.80:
            return DataQualityLevel.GOOD
        elif score >= 0.70:
            return DataQualityLevel.FAIR
        elif score >= 0.50:
            return DataQualityLevel.POOR
        else:
            return DataQualityLevel.CRITICAL
    
    def _calculate_overall_score(self, metrics: List[DataQualityMetric]) -> float:
        """Calculate overall quality score"""
        if not metrics:
            return 0.0
        
        # Weight different metric types
        weights = {
            'completeness': 0.3,
            'accuracy': 0.25,
            'consistency': 0.2,
            'timeliness': 0.15,
            'uniqueness': 0.1
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for metric in metrics:
            # Determine metric type from name
            metric_type = None
            for mtype in weights.keys():
                if mtype in metric.name:
                    metric_type = mtype
                    break
            
            if metric_type:
                weight = weights[metric_type]
                weighted_sum += metric.value * weight
                total_weight += weight
        
        if total_weight > 0:
            return weighted_sum / total_weight
        else:
            return sum(metric.value for metric in metrics) / len(metrics)
    
    def _generate_recommendations(self, metrics: List[DataQualityMetric]) -> List[str]:
        """Generate recommendations based on quality metrics"""
        recommendations = []
        
        for metric in metrics:
            if metric.level in [DataQualityLevel.POOR, DataQualityLevel.CRITICAL]:
                if 'completeness' in metric.name:
                    recommendations.append(
                        f"Improve {metric.description.lower()} by implementing better data validation rules"
                    )
                elif 'accuracy' in metric.name:
                    recommendations.append(
                        f"Enhance {metric.description.lower()} through improved data cleansing processes"
                    )
                elif 'consistency' in metric.name:
                    recommendations.append(
                        f"Address {metric.description.lower()} issues by implementing data standardization"
                    )
                elif 'timeliness' in metric.name:
                    recommendations.append(
                        f"Optimize {metric.description.lower()} by improving ingestion pipeline performance"
                    )
                elif 'uniqueness' in metric.name:
                    recommendations.append(
                        f"Reduce duplicate data by enhancing duplicate detection algorithms"
                    )
        
        # Remove duplicates
        return list(set(recommendations))
    
    def _is_valid_email(self, email: str) -> bool:
        """Check if email format is valid"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _is_valid_cui(self, cui: str) -> bool:
        """Check if CUI format is valid"""
        import re
        # Remove RO prefix if present
        cui_clean = cui.replace('RO', '').strip()
        # Check if it's numeric and has reasonable length
        return cui_clean.isdigit() and 2 <= len(cui_clean) <= 10
    
    def _is_status_consistent(self, tender: Tender) -> bool:
        """Check if tender status is consistent with dates"""
        if not tender.status:
            return False
        
        now = datetime.now()
        
        # If tender is active, submission deadline should be in the future
        if tender.status == 'active':
            if tender.submission_deadline and tender.submission_deadline < now:
                return False
        
        # If tender is closed, submission deadline should be in the past
        elif tender.status == 'closed':
            if tender.submission_deadline and tender.submission_deadline > now:
                return False
        
        return True
    
    def _are_tenders_similar(self, tender1: Tender, tender2: Tender) -> bool:
        """Check if two tenders are similar (potential duplicates)"""
        # Simple similarity check
        if not tender1.title or not tender2.title:
            return False
        
        # Check title similarity
        title1_words = set(tender1.title.lower().split())
        title2_words = set(tender2.title.lower().split())
        
        if len(title1_words) == 0 or len(title2_words) == 0:
            return False
        
        similarity = len(title1_words.intersection(title2_words)) / len(title1_words.union(title2_words))
        
        # Check if similar and from same authority
        if similarity > 0.7:
            if tender1.contracting_authority_id == tender2.contracting_authority_id:
                return True
        
        return False


class DataQualityAlerter:
    """Data quality alerting system"""
    
    def __init__(self):
        self.alert_thresholds = {
            DataQualityLevel.CRITICAL: True,
            DataQualityLevel.POOR: True,
            DataQualityLevel.FAIR: False,
            DataQualityLevel.GOOD: False,
            DataQualityLevel.EXCELLENT: False
        }
    
    async def check_and_alert(self, report: DataQualityReport):
        """Check quality report and send alerts if needed"""
        
        alerts_to_send = []
        
        # Check overall quality
        if self.alert_thresholds.get(report.overall_level, False):
            alerts_to_send.append({
                'type': 'overall_quality',
                'level': report.overall_level.value,
                'score': report.overall_score,
                'message': f"Overall data quality for {report.source_system} is {report.overall_level.value}"
            })
        
        # Check individual metrics
        for metric in report.metrics:
            if self.alert_thresholds.get(metric.level, False):
                alerts_to_send.append({
                    'type': 'metric_quality',
                    'metric_name': metric.name,
                    'level': metric.level.value,
                    'score': metric.value,
                    'threshold': metric.threshold,
                    'message': f"{metric.description} is {metric.level.value} ({metric.value:.2%})"
                })
        
        # Send alerts
        for alert in alerts_to_send:
            await self._send_alert(alert, report)
    
    async def _send_alert(self, alert: Dict[str, Any], report: DataQualityReport):
        """Send quality alert"""
        
        logger.warning(f"Data Quality Alert: {alert['message']}")
        
        # In production, this would send email, Slack, or other notifications
        # For now, just log the alert
        
        alert_details = {
            'source_system': report.source_system,
            'alert_type': alert['type'],
            'level': alert['level'],
            'timestamp': datetime.now().isoformat(),
            'details': alert
        }
        
        logger.info(f"Alert details: {json.dumps(alert_details, indent=2)}")