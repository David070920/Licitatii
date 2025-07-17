"""
Celery application configuration with comprehensive task scheduling
"""

from celery import Celery
from app.core.config import settings
from app.services.celery_beat_config import get_celery_config

# Create Celery instance
celery_app = Celery(
    "procurement_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.services.tasks.data_ingestion",
        "app.services.tasks.risk_analysis",
        "app.services.tasks.notifications",
        "app.services.tasks.reports",
        "app.services.tasks.monitoring",
        "app.services.tasks.maintenance",
        "app.services.tasks.documents",
        "app.services.tasks.enrichment",
        "app.services.tasks.backup",
        "app.services.tasks.statistics"
    ]
)

# Apply configuration
celery_config = get_celery_config()
celery_app.conf.update(celery_config)

# Additional Celery configuration
celery_app.conf.update(
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_send_sent_event=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    worker_send_task_events=True,
    
    # Monitoring settings
    worker_hijack_root_logger=False,
    worker_log_color=True,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
    
    # Security settings
    worker_enable_remote_control=False,
    
    # Result settings
    result_expires=3600,  # 1 hour
    result_compression='gzip',
    result_persistent=True,
    
    # Error handling
    task_soft_time_limit=25 * 60,  # 25 minutes
    task_time_limit=30 * 60,  # 30 minutes
    task_max_retries=3,
    task_default_retry_delay=60 * 5,  # 5 minutes
    task_retry_jitter=True,
    
    # Timezone settings
    timezone='Europe/Bucharest',
    enable_utc=True,
)

# Queue definitions
from kombu import Queue, Exchange

# Define exchanges
data_ingestion_exchange = Exchange('data_ingestion', type='direct')
monitoring_exchange = Exchange('monitoring', type='direct')
risk_analysis_exchange = Exchange('risk_analysis', type='direct')
notifications_exchange = Exchange('notifications', type='direct')
maintenance_exchange = Exchange('maintenance', type='direct')
documents_exchange = Exchange('documents', type='direct')
enrichment_exchange = Exchange('enrichment', type='direct')
backup_exchange = Exchange('backup', type='direct')
statistics_exchange = Exchange('statistics', type='direct')

# Define queues
celery_app.conf.task_queues = (
    Queue('data_ingestion', 
          exchange=data_ingestion_exchange, 
          routing_key='data_ingestion',
          queue_arguments={'x-max-priority': 10}),
    Queue('monitoring', 
          exchange=monitoring_exchange, 
          routing_key='monitoring',
          queue_arguments={'x-max-priority': 9}),
    Queue('risk_analysis', 
          exchange=risk_analysis_exchange, 
          routing_key='risk_analysis',
          queue_arguments={'x-max-priority': 8}),
    Queue('notifications', 
          exchange=notifications_exchange, 
          routing_key='notifications',
          queue_arguments={'x-max-priority': 6}),
    Queue('maintenance', 
          exchange=maintenance_exchange, 
          routing_key='maintenance',
          queue_arguments={'x-max-priority': 3}),
    Queue('documents', 
          exchange=documents_exchange, 
          routing_key='documents',
          queue_arguments={'x-max-priority': 4}),
    Queue('enrichment', 
          exchange=enrichment_exchange, 
          routing_key='enrichment',
          queue_arguments={'x-max-priority': 5}),
    Queue('backup', 
          exchange=backup_exchange, 
          routing_key='backup',
          queue_arguments={'x-max-priority': 2}),
    Queue('statistics', 
          exchange=statistics_exchange, 
          routing_key='statistics',
          queue_arguments={'x-max-priority': 4}),
)

# Task annotations for priority
celery_app.conf.task_annotations = {
    'app.services.tasks.monitoring.monitor_pipeline_health': {'priority': 9},
    'app.services.tasks.data_ingestion.health_check': {'priority': 8},
    'app.services.tasks.monitoring.monitor_data_quality': {'priority': 7},
    'app.services.tasks.data_ingestion.sync_sicap_data': {'priority': 6},
    'app.services.tasks.data_ingestion.sync_anrmap_data': {'priority': 6},
    'app.services.tasks.data_ingestion.incremental_sync': {'priority': 5},
    'app.services.tasks.risk_analysis.analyze_tender_risks': {'priority': 5},
    'app.services.tasks.notifications.send_daily_alerts': {'priority': 4},
    'app.services.tasks.documents.process_pending_documents': {'priority': 3},
    'app.services.tasks.enrichment.enrich_missing_data': {'priority': 3},
    'app.services.tasks.statistics.generate_daily_statistics': {'priority': 2},
    'app.services.tasks.maintenance.cleanup_old_sessions': {'priority': 1},
    'app.services.tasks.backup.backup_critical_data': {'priority': 1},
}

# Environment-specific configurations
if settings.is_development:
    # Development settings
    celery_app.conf.update(
        task_always_eager=False,
        task_eager_propagates=True,
        worker_concurrency=2,
        worker_prefetch_multiplier=1,
    )
elif settings.is_production:
    # Production settings
    celery_app.conf.update(
        task_always_eager=False,
        task_eager_propagates=False,
        worker_concurrency=4,
        worker_prefetch_multiplier=1,
        worker_max_memory_per_child=200000,  # 200MB
    )

# Signal handlers
from celery.signals import task_prerun, task_postrun, task_failure, task_success
from app.core.logging import logger
from app.core.monitoring import metrics_collector

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task prerun signal"""
    logger.info(f"Task {task.name} started with ID: {task_id}")
    metrics_collector.record_metric('task_started', 1, {'task_name': task.name})

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handle task postrun signal"""
    logger.info(f"Task {task.name} completed with ID: {task_id}, State: {state}")
    metrics_collector.record_metric('task_completed', 1, {'task_name': task.name, 'state': state})

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, **kwds):
    """Handle task failure signal"""
    logger.error(f"Task {sender.name} failed with ID: {task_id}, Exception: {exception}")
    metrics_collector.record_metric('task_failed', 1, {'task_name': sender.name})

@task_success.connect
def task_success_handler(sender=None, result=None, **kwds):
    """Handle task success signal"""
    logger.info(f"Task {sender.name} succeeded")
    metrics_collector.record_metric('task_succeeded', 1, {'task_name': sender.name})

# Periodic task to check Celery worker health
@celery_app.task(bind=True)
def celery_health_check(self):
    """Check Celery worker health"""
    try:
        # Basic health check
        active_workers = celery_app.control.inspect().active()
        registered_tasks = celery_app.control.inspect().registered()
        
        health_status = {
            'status': 'healthy',
            'active_workers': len(active_workers) if active_workers else 0,
            'registered_tasks': len(registered_tasks) if registered_tasks else 0,
            'timestamp': str(datetime.now()),
            'worker_id': self.request.hostname
        }
        
        logger.info(f"Celery health check: {health_status}")
        metrics_collector.record_metric('celery_health_check', 1, health_status)
        
        return health_status
        
    except Exception as e:
        logger.error(f"Celery health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': str(datetime.now())
        }

# Custom task base class with enhanced error handling
from celery import Task
from datetime import datetime
import traceback

class CallbackTask(Task):
    """Enhanced task class with better error handling and monitoring"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        logger.info(f"Task {self.name} succeeded with ID: {task_id}")
        metrics_collector.record_metric(f'task_success_{self.name}', 1)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        logger.error(f"Task {self.name} failed with ID: {task_id}, Exception: {exc}")
        logger.error(f"Traceback: {einfo}")
        metrics_collector.record_metric(f'task_failure_{self.name}', 1)
        
        # Send alert for critical task failures
        if self.name in ['monitor_pipeline_health', 'sync_sicap_data', 'sync_anrmap_data']:
            from app.core.monitoring import PipelineMonitor, Alert, AlertType, AlertSeverity
            
            alert = Alert(
                id=f"task_failure_{task_id}",
                type=AlertType.PIPELINE_FAILURE,
                severity=AlertSeverity.HIGH,
                title=f"Critical Task Failure: {self.name}",
                message=f"Task {self.name} failed with exception: {exc}",
                source="celery_worker",
                timestamp=datetime.now(),
                metadata={
                    'task_id': task_id,
                    'task_name': self.name,
                    'exception': str(exc),
                    'traceback': str(einfo)
                }
            )
            
            # This would send the alert asynchronously
            # For now, just log it
            logger.critical(f"Critical task failure alert: {alert}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        logger.warning(f"Task {self.name} retried with ID: {task_id}, Exception: {exc}")
        metrics_collector.record_metric(f'task_retry_{self.name}', 1)
    
    def apply_async(self, args=None, kwargs=None, **options):
        """Override apply_async to add default options"""
        # Add task metadata
        if 'headers' not in options:
            options['headers'] = {}
        
        options['headers'].update({
            'submitted_at': datetime.now().isoformat(),
            'task_version': '1.0'
        })
        
        return super().apply_async(args, kwargs, **options)

# Set default task base class
celery_app.Task = CallbackTask

# Auto-discovery of tasks
celery_app.autodiscover_tasks([
    'app.services.tasks'
])

if __name__ == "__main__":
    celery_app.start()