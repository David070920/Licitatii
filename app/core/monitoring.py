"""
Monitoring and alerting system for data ingestion pipeline
"""

import asyncio
import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.core.database import get_async_session
from app.core.config import settings
from app.core.logging import logger
from app.db.models import DataIngestionLog, Tender
from app.core.data_quality.monitor import DataQualityMonitor, DataQualityReport


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Alert types"""
    PIPELINE_FAILURE = "pipeline_failure"
    DATA_QUALITY = "data_quality"
    PERFORMANCE = "performance"
    RESOURCE = "resource"
    SECURITY = "security"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    source: str
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class PipelineMonitor:
    """Pipeline monitoring and alerting system"""
    
    def __init__(self):
        self.data_quality_monitor = DataQualityMonitor()
        self.alert_handlers = {
            'email': EmailAlertHandler(),
            'webhook': WebhookAlertHandler(),
            'log': LogAlertHandler()
        }
        
        # Alert thresholds
        self.thresholds = {
            'failure_rate': 0.1,  # 10% failure rate
            'processing_time': 3600,  # 1 hour
            'data_freshness': 86400,  # 24 hours
            'error_count': 10,  # 10 errors
            'duplicate_rate': 0.3,  # 30% duplicate rate
        }
    
    async def monitor_pipeline_health(self) -> Dict[str, Any]:
        """Monitor overall pipeline health"""
        
        logger.info("Starting pipeline health monitoring")
        
        health_report = {
            'overall_status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'alerts': []
        }
        
        try:
            # Check ingestion job status
            ingestion_health = await self._check_ingestion_health()
            health_report['checks']['ingestion'] = ingestion_health
            
            # Check data quality
            quality_health = await self._check_data_quality()
            health_report['checks']['data_quality'] = quality_health
            
            # Check performance metrics
            performance_health = await self._check_performance()
            health_report['checks']['performance'] = performance_health
            
            # Check resource usage
            resource_health = await self._check_resource_usage()
            health_report['checks']['resource'] = resource_health
            
            # Check data freshness
            freshness_health = await self._check_data_freshness()
            health_report['checks']['data_freshness'] = freshness_health
            
            # Determine overall status
            overall_status = self._determine_overall_status(health_report['checks'])
            health_report['overall_status'] = overall_status
            
            # Generate alerts if needed
            alerts = await self._generate_alerts(health_report['checks'])
            health_report['alerts'] = alerts
            
            # Send alerts
            for alert in alerts:
                await self._send_alert(alert)
            
            logger.info(f"Pipeline health monitoring completed. Status: {overall_status}")
            return health_report
            
        except Exception as e:
            logger.error(f"Error in pipeline health monitoring: {str(e)}")
            
            # Create critical alert for monitoring failure
            critical_alert = Alert(
                id=f"monitor_failure_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                type=AlertType.PIPELINE_FAILURE,
                severity=AlertSeverity.CRITICAL,
                title="Pipeline Monitoring Failure",
                message=f"Pipeline monitoring system failed: {str(e)}",
                source="pipeline_monitor",
                timestamp=datetime.now(),
                metadata={'error': str(e)}
            )
            
            await self._send_alert(critical_alert)
            
            health_report['overall_status'] = 'critical'
            health_report['error'] = str(e)
            
            return health_report
    
    async def _check_ingestion_health(self) -> Dict[str, Any]:
        """Check ingestion job health"""
        
        try:
            async with get_async_session() as session:
                # Check recent ingestion jobs
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                result = await session.execute(
                    select(
                        DataIngestionLog.status,
                        func.count(DataIngestionLog.id).label('count')
                    ).where(
                        DataIngestionLog.started_at >= cutoff_time
                    ).group_by(DataIngestionLog.status)
                )
                
                status_counts = {row.status: row.count for row in result}
                
                total_jobs = sum(status_counts.values())
                failed_jobs = status_counts.get('failed', 0)
                
                failure_rate = failed_jobs / total_jobs if total_jobs > 0 else 0
                
                # Check for stuck jobs
                stuck_jobs = await session.execute(
                    select(func.count(DataIngestionLog.id)).where(
                        and_(
                            DataIngestionLog.status == 'running',
                            DataIngestionLog.started_at < datetime.now() - timedelta(hours=2)
                        )
                    )
                )
                
                stuck_count = stuck_jobs.scalar()
                
                health_status = 'healthy'
                if failure_rate > self.thresholds['failure_rate']:
                    health_status = 'degraded'
                if stuck_count > 0:
                    health_status = 'critical'
                
                return {
                    'status': health_status,
                    'total_jobs': total_jobs,
                    'failed_jobs': failed_jobs,
                    'failure_rate': failure_rate,
                    'stuck_jobs': stuck_count,
                    'details': status_counts
                }
                
        except Exception as e:
            logger.error(f"Error checking ingestion health: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def _check_data_quality(self) -> Dict[str, Any]:
        """Check data quality health"""
        
        try:
            # Check data quality for each source
            sources = ['SICAP', 'ANRMAP']
            quality_results = {}
            
            overall_quality = 'healthy'
            
            for source in sources:
                quality_report = await self.data_quality_monitor.generate_quality_report(
                    source, days_back=1
                )
                
                quality_results[source] = {
                    'overall_score': quality_report.overall_score,
                    'overall_level': quality_report.overall_level.value,
                    'metrics_count': len(quality_report.metrics),
                    'recommendations_count': len(quality_report.recommendations)
                }
                
                # Determine if quality is concerning
                if quality_report.overall_score < 0.7:
                    overall_quality = 'degraded'
                if quality_report.overall_score < 0.5:
                    overall_quality = 'critical'
            
            return {
                'status': overall_quality,
                'sources': quality_results,
                'checked_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking data quality: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def _check_performance(self) -> Dict[str, Any]:
        """Check performance metrics"""
        
        try:
            async with get_async_session() as session:
                # Check average processing time
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                result = await session.execute(
                    select(
                        func.avg(
                            func.extract('epoch', DataIngestionLog.completed_at - DataIngestionLog.started_at)
                        ).label('avg_duration'),
                        func.max(
                            func.extract('epoch', DataIngestionLog.completed_at - DataIngestionLog.started_at)
                        ).label('max_duration'),
                        func.count(DataIngestionLog.id).label('total_jobs')
                    ).where(
                        and_(
                            DataIngestionLog.started_at >= cutoff_time,
                            DataIngestionLog.status == 'completed',
                            DataIngestionLog.completed_at.isnot(None)
                        )
                    )
                )
                
                performance_data = result.first()
                
                if performance_data and performance_data.total_jobs > 0:
                    avg_duration = performance_data.avg_duration or 0
                    max_duration = performance_data.max_duration or 0
                    
                    status = 'healthy'
                    if avg_duration > self.thresholds['processing_time']:
                        status = 'degraded'
                    if max_duration > self.thresholds['processing_time'] * 2:
                        status = 'critical'
                    
                    return {
                        'status': status,
                        'avg_duration_seconds': avg_duration,
                        'max_duration_seconds': max_duration,
                        'total_jobs': performance_data.total_jobs,
                        'threshold_seconds': self.thresholds['processing_time']
                    }
                else:
                    return {
                        'status': 'no_data',
                        'message': 'No completed jobs in the last 24 hours'
                    }
                    
        except Exception as e:
            logger.error(f"Error checking performance: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def _check_resource_usage(self) -> Dict[str, Any]:
        """Check resource usage"""
        
        try:
            # In a real implementation, this would check:
            # - CPU usage
            # - Memory usage
            # - Disk space
            # - Network usage
            # - Database connections
            
            # For now, return a basic health check
            return {
                'status': 'healthy',
                'cpu_usage': 'normal',
                'memory_usage': 'normal',
                'disk_usage': 'normal',
                'database_connections': 'normal'
            }
            
        except Exception as e:
            logger.error(f"Error checking resource usage: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def _check_data_freshness(self) -> Dict[str, Any]:
        """Check data freshness"""
        
        try:
            async with get_async_session() as session:
                # Check when data was last updated for each source
                sources = ['SICAP', 'ANRMAP']
                freshness_results = {}
                
                overall_freshness = 'healthy'
                
                for source in sources:
                    result = await session.execute(
                        select(
                            func.max(Tender.last_scraped_at).label('last_update'),
                            func.count(Tender.id).label('total_records')
                        ).where(Tender.source_system == source)
                    )
                    
                    data = result.first()
                    
                    if data and data.last_update:
                        hours_since_update = (datetime.now() - data.last_update).total_seconds() / 3600
                        
                        status = 'healthy'
                        if hours_since_update > 24:
                            status = 'stale'
                            overall_freshness = 'degraded'
                        if hours_since_update > 48:
                            status = 'very_stale'
                            overall_freshness = 'critical'
                        
                        freshness_results[source] = {
                            'status': status,
                            'last_update': data.last_update.isoformat(),
                            'hours_since_update': hours_since_update,
                            'total_records': data.total_records
                        }
                    else:
                        freshness_results[source] = {
                            'status': 'no_data',
                            'message': 'No data available for this source'
                        }
                        overall_freshness = 'critical'
                
                return {
                    'status': overall_freshness,
                    'sources': freshness_results,
                    'threshold_hours': self.thresholds['data_freshness'] / 3600
                }
                
        except Exception as e:
            logger.error(f"Error checking data freshness: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _determine_overall_status(self, checks: Dict[str, Any]) -> str:
        """Determine overall pipeline status"""
        
        statuses = [check.get('status', 'unknown') for check in checks.values()]
        
        if 'critical' in statuses or 'error' in statuses:
            return 'critical'
        elif 'degraded' in statuses or 'stale' in statuses:
            return 'degraded'
        elif 'no_data' in statuses:
            return 'warning'
        else:
            return 'healthy'
    
    async def _generate_alerts(self, checks: Dict[str, Any]) -> List[Alert]:
        """Generate alerts based on health checks"""
        
        alerts = []
        
        for check_name, check_data in checks.items():
            status = check_data.get('status', 'unknown')
            
            if status in ['critical', 'error']:
                severity = AlertSeverity.CRITICAL
            elif status in ['degraded', 'stale']:
                severity = AlertSeverity.HIGH
            elif status == 'no_data':
                severity = AlertSeverity.MEDIUM
            else:
                continue  # No alert needed for healthy status
            
            alert = Alert(
                id=f"{check_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                type=AlertType.PIPELINE_FAILURE,
                severity=severity,
                title=f"Pipeline {check_name.replace('_', ' ').title()} Issue",
                message=self._generate_alert_message(check_name, check_data),
                source=check_name,
                timestamp=datetime.now(),
                metadata=check_data
            )
            
            alerts.append(alert)
        
        return alerts
    
    def _generate_alert_message(self, check_name: str, check_data: Dict[str, Any]) -> str:
        """Generate alert message based on check data"""
        
        status = check_data.get('status', 'unknown')
        
        if check_name == 'ingestion':
            if status == 'critical':
                return f"Ingestion pipeline has {check_data.get('stuck_jobs', 0)} stuck jobs"
            elif status == 'degraded':
                failure_rate = check_data.get('failure_rate', 0)
                return f"Ingestion failure rate is {failure_rate:.1%} (threshold: {self.thresholds['failure_rate']:.1%})"
        
        elif check_name == 'data_quality':
            if status == 'critical':
                return "Data quality has fallen below acceptable levels"
            elif status == 'degraded':
                return "Data quality metrics show concerning trends"
        
        elif check_name == 'performance':
            if status == 'critical':
                max_duration = check_data.get('max_duration_seconds', 0)
                return f"Processing time exceeded {max_duration:.0f} seconds"
            elif status == 'degraded':
                avg_duration = check_data.get('avg_duration_seconds', 0)
                return f"Average processing time is {avg_duration:.0f} seconds"
        
        elif check_name == 'data_freshness':
            if status == 'critical':
                return "Data has not been updated in over 48 hours"
            elif status == 'degraded':
                return "Data is becoming stale (over 24 hours since last update)"
        
        return f"Pipeline check '{check_name}' has status: {status}"
    
    async def _send_alert(self, alert: Alert):
        """Send alert through configured channels"""
        
        logger.warning(f"Sending alert: {alert.title} - {alert.message}")
        
        # Send through all configured handlers
        for handler_name, handler in self.alert_handlers.items():
            try:
                await handler.send_alert(alert)
                logger.info(f"Alert sent via {handler_name}")
            except Exception as e:
                logger.error(f"Failed to send alert via {handler_name}: {str(e)}")
    
    async def monitor_specific_job(self, job_id: str) -> Dict[str, Any]:
        """Monitor a specific ingestion job"""
        
        try:
            async with get_async_session() as session:
                result = await session.execute(
                    select(DataIngestionLog).where(
                        DataIngestionLog.job_id == job_id
                    )
                )
                
                job_log = result.scalar_one_or_none()
                
                if not job_log:
                    return {
                        'status': 'not_found',
                        'message': f'Job {job_id} not found'
                    }
                
                job_status = {
                    'job_id': job_id,
                    'status': job_log.status,
                    'source_system': job_log.source_system,
                    'started_at': job_log.started_at.isoformat(),
                    'completed_at': job_log.completed_at.isoformat() if job_log.completed_at else None,
                    'records_processed': job_log.records_processed,
                    'records_created': job_log.records_created,
                    'records_updated': job_log.records_updated,
                    'records_failed': job_log.records_failed,
                    'error_message': job_log.error_message
                }
                
                # Calculate duration if completed
                if job_log.completed_at:
                    duration = (job_log.completed_at - job_log.started_at).total_seconds()
                    job_status['duration_seconds'] = duration
                
                return job_status
                
        except Exception as e:
            logger.error(f"Error monitoring job {job_id}: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }


class AlertHandler:
    """Base class for alert handlers"""
    
    async def send_alert(self, alert: Alert):
        """Send alert - to be implemented by subclasses"""
        raise NotImplementedError


class EmailAlertHandler(AlertHandler):
    """Email alert handler"""
    
    async def send_alert(self, alert: Alert):
        """Send alert via email"""
        
        if not all([settings.SMTP_HOST, settings.SMTP_USER, settings.SMTP_PASSWORD]):
            logger.warning("Email settings not configured, skipping email alert")
            return
        
        try:
            # Create message
            msg = MimeMultipart()
            msg['From'] = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER
            msg['To'] = settings.EMAILS_FROM_EMAIL or settings.SMTP_USER  # In production, use admin emails
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            # Create email body
            body = self._create_email_body(alert)
            msg.attach(MimeText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Email alert sent for: {alert.title}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")
            raise
    
    def _create_email_body(self, alert: Alert) -> str:
        """Create HTML email body"""
        
        severity_colors = {
            AlertSeverity.LOW: '#28a745',
            AlertSeverity.MEDIUM: '#ffc107',
            AlertSeverity.HIGH: '#fd7e14',
            AlertSeverity.CRITICAL: '#dc3545'
        }
        
        color = severity_colors.get(alert.severity, '#6c757d')
        
        return f"""
        <html>
        <body>
        <h2 style="color: {color};">{alert.title}</h2>
        <p><strong>Severity:</strong> {alert.severity.value.upper()}</p>
        <p><strong>Type:</strong> {alert.type.value}</p>
        <p><strong>Source:</strong> {alert.source}</p>
        <p><strong>Timestamp:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Message:</strong></p>
        <p>{alert.message}</p>
        
        <h3>Additional Details:</h3>
        <pre>{json.dumps(alert.metadata, indent=2)}</pre>
        
        <p><em>This is an automated alert from the Romanian Procurement Platform monitoring system.</em></p>
        </body>
        </html>
        """


class WebhookAlertHandler(AlertHandler):
    """Webhook alert handler"""
    
    async def send_alert(self, alert: Alert):
        """Send alert via webhook"""
        
        webhook_url = getattr(settings, 'WEBHOOK_URL', None)
        if not webhook_url:
            logger.warning("Webhook URL not configured, skipping webhook alert")
            return
        
        try:
            payload = {
                'id': alert.id,
                'type': alert.type.value,
                'severity': alert.severity.value,
                'title': alert.title,
                'message': alert.message,
                'source': alert.source,
                'timestamp': alert.timestamp.isoformat(),
                'metadata': alert.metadata
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Webhook alert sent for: {alert.title}")
                    else:
                        logger.error(f"Webhook alert failed with status {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {str(e)}")
            raise


class LogAlertHandler(AlertHandler):
    """Log alert handler"""
    
    async def send_alert(self, alert: Alert):
        """Send alert to logs"""
        
        log_level = {
            AlertSeverity.LOW: logger.info,
            AlertSeverity.MEDIUM: logger.warning,
            AlertSeverity.HIGH: logger.error,
            AlertSeverity.CRITICAL: logger.critical
        }.get(alert.severity, logger.info)
        
        log_message = f"ALERT [{alert.severity.value.upper()}] {alert.title}: {alert.message}"
        log_level(log_message)
        
        # Log additional metadata
        logger.info(f"Alert metadata: {json.dumps(alert.metadata, indent=2)}")


class MetricsCollector:
    """Collect and store metrics for monitoring"""
    
    def __init__(self):
        self.metrics = {}
    
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric value"""
        
        timestamp = datetime.now()
        
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            'value': value,
            'timestamp': timestamp,
            'tags': tags or {}
        })
        
        # Keep only last 1000 entries per metric
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]
    
    def get_metric(self, name: str, time_window: timedelta = None) -> List[Dict[str, Any]]:
        """Get metric values within time window"""
        
        if name not in self.metrics:
            return []
        
        if time_window is None:
            return self.metrics[name]
        
        cutoff_time = datetime.now() - time_window
        
        return [
            entry for entry in self.metrics[name]
            if entry['timestamp'] >= cutoff_time
        ]
    
    def get_metric_summary(self, name: str, time_window: timedelta = None) -> Dict[str, Any]:
        """Get metric summary statistics"""
        
        values = self.get_metric(name, time_window)
        
        if not values:
            return {
                'count': 0,
                'min': None,
                'max': None,
                'avg': None,
                'sum': None
            }
        
        numeric_values = [entry['value'] for entry in values]
        
        return {
            'count': len(numeric_values),
            'min': min(numeric_values),
            'max': max(numeric_values),
            'avg': sum(numeric_values) / len(numeric_values),
            'sum': sum(numeric_values)
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()