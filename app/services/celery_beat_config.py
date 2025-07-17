"""
Celery Beat configuration for scheduled tasks
"""

from datetime import timedelta
from celery.schedules import crontab

from app.core.config import settings

# Celery Beat schedule configuration
CELERY_BEAT_SCHEDULE = {
    # Data ingestion tasks
    'sicap-full-sync': {
        'task': 'app.services.tasks.data_ingestion.sync_sicap_data',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        'kwargs': {
            'job_id': 'sicap_daily_sync'
        }
    },
    
    'sicap-incremental-sync': {
        'task': 'app.services.tasks.data_ingestion.incremental_sync',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
        'kwargs': {
            'source_system': 'SICAP',
            'hours_back': 2
        }
    },
    
    'anrmap-daily-sync': {
        'task': 'app.services.tasks.data_ingestion.sync_anrmap_data',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
        'kwargs': {
            'job_id': 'anrmap_daily_sync'
        }
    },
    
    'anrmap-incremental-sync': {
        'task': 'app.services.tasks.data_ingestion.incremental_sync',
        'schedule': crontab(minute='0', hour='*/6'),  # Every 6 hours
        'kwargs': {
            'source_system': 'ANRMAP',
            'hours_back': 8
        }
    },
    
    # Weekly full synchronization
    'weekly-full-sync': {
        'task': 'app.services.tasks.data_ingestion.sync_all_sources',
        'schedule': crontab(hour=1, minute=0, day_of_week=1),  # Monday at 1 AM
        'kwargs': {
            'job_id': 'weekly_full_sync'
        }
    },
    
    # Data quality monitoring
    'data-quality-monitoring': {
        'task': 'app.services.tasks.monitoring.monitor_data_quality',
        'schedule': crontab(hour='*/4', minute=0),  # Every 4 hours
    },
    
    # Pipeline health monitoring
    'pipeline-health-check': {
        'task': 'app.services.tasks.monitoring.monitor_pipeline_health',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    
    # Risk analysis tasks
    'analyze-tender-risks': {
        'task': 'app.services.tasks.risk_analysis.analyze_tender_risks',
        'schedule': crontab(hour='*/2', minute=0),  # Every 2 hours
    },
    
    # Notification tasks
    'send-daily-alerts': {
        'task': 'app.services.tasks.notifications.send_daily_alerts',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
    },
    
    'send-weekly-report': {
        'task': 'app.services.tasks.notifications.send_weekly_report',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),  # Monday at 9 AM
    },
    
    # Maintenance tasks
    'cleanup-old-sessions': {
        'task': 'app.services.tasks.maintenance.cleanup_old_sessions',
        'schedule': crontab(hour=4, minute=0),  # Daily at 4 AM
    },
    
    'cleanup-old-logs': {
        'task': 'app.services.tasks.data_ingestion.cleanup_old_logs',
        'schedule': crontab(hour=5, minute=0, day_of_week=0),  # Sunday at 5 AM
        'kwargs': {
            'days_to_keep': 30
        }
    },
    
    'database-maintenance': {
        'task': 'app.services.tasks.maintenance.database_maintenance',
        'schedule': crontab(hour=6, minute=0, day_of_week=0),  # Sunday at 6 AM
    },
    
    # Health check tasks
    'health-check': {
        'task': 'app.services.tasks.data_ingestion.health_check',
        'schedule': timedelta(minutes=5),  # Every 5 minutes
    },
    
    # Performance monitoring
    'performance-monitoring': {
        'task': 'app.services.tasks.monitoring.collect_performance_metrics',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    
    # Document processing
    'process-tender-documents': {
        'task': 'app.services.tasks.documents.process_pending_documents',
        'schedule': crontab(hour='*/3', minute=30),  # Every 3 hours at 30 minutes
    },
    
    # Data enrichment tasks
    'enrich-missing-data': {
        'task': 'app.services.tasks.enrichment.enrich_missing_data',
        'schedule': crontab(hour=7, minute=0),  # Daily at 7 AM
    },
    
    # Backup tasks
    'backup-critical-data': {
        'task': 'app.services.tasks.backup.backup_critical_data',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
    
    # Statistics generation
    'generate-daily-statistics': {
        'task': 'app.services.tasks.statistics.generate_daily_statistics',
        'schedule': crontab(hour=23, minute=0),  # Daily at 11 PM
    },
    
    # Tender status updates
    'update-tender-statuses': {
        'task': 'app.services.tasks.maintenance.update_tender_statuses',
        'schedule': crontab(hour=12, minute=0),  # Daily at noon
    },
    
    # API rate limit reset
    'reset-api-rate-limits': {
        'task': 'app.services.tasks.maintenance.reset_api_rate_limits',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}

# Task routing configuration
CELERY_TASK_ROUTES = {
    'app.services.tasks.data_ingestion.*': {
        'queue': 'data_ingestion',
        'routing_key': 'data_ingestion'
    },
    'app.services.tasks.monitoring.*': {
        'queue': 'monitoring',
        'routing_key': 'monitoring'
    },
    'app.services.tasks.risk_analysis.*': {
        'queue': 'risk_analysis',
        'routing_key': 'risk_analysis'
    },
    'app.services.tasks.notifications.*': {
        'queue': 'notifications',
        'routing_key': 'notifications'
    },
    'app.services.tasks.maintenance.*': {
        'queue': 'maintenance',
        'routing_key': 'maintenance'
    },
    'app.services.tasks.documents.*': {
        'queue': 'documents',
        'routing_key': 'documents'
    },
    'app.services.tasks.enrichment.*': {
        'queue': 'enrichment',
        'routing_key': 'enrichment'
    },
    'app.services.tasks.backup.*': {
        'queue': 'backup',
        'routing_key': 'backup'
    },
    'app.services.tasks.statistics.*': {
        'queue': 'statistics',
        'routing_key': 'statistics'
    },
}

# Queue configuration
CELERY_QUEUE_CONFIG = {
    'data_ingestion': {
        'exchange': 'data_ingestion',
        'exchange_type': 'direct',
        'routing_key': 'data_ingestion',
        'durable': True,
        'auto_delete': False,
        'arguments': {
            'x-max-priority': 10
        }
    },
    'monitoring': {
        'exchange': 'monitoring',
        'exchange_type': 'direct',
        'routing_key': 'monitoring',
        'durable': True,
        'auto_delete': False,
        'arguments': {
            'x-max-priority': 5
        }
    },
    'risk_analysis': {
        'exchange': 'risk_analysis',
        'exchange_type': 'direct',
        'routing_key': 'risk_analysis',
        'durable': True,
        'auto_delete': False,
        'arguments': {
            'x-max-priority': 8
        }
    },
    'notifications': {
        'exchange': 'notifications',
        'exchange_type': 'direct',
        'routing_key': 'notifications',
        'durable': True,
        'auto_delete': False,
        'arguments': {
            'x-max-priority': 6
        }
    },
    'maintenance': {
        'exchange': 'maintenance',
        'exchange_type': 'direct',
        'routing_key': 'maintenance',
        'durable': True,
        'auto_delete': False,
        'arguments': {
            'x-max-priority': 3
        }
    },
    'documents': {
        'exchange': 'documents',
        'exchange_type': 'direct',
        'routing_key': 'documents',
        'durable': True,
        'auto_delete': False,
        'arguments': {
            'x-max-priority': 4
        }
    },
    'enrichment': {
        'exchange': 'enrichment',
        'exchange_type': 'direct',
        'routing_key': 'enrichment',
        'durable': True,
        'auto_delete': False,
        'arguments': {
            'x-max-priority': 5
        }
    },
    'backup': {
        'exchange': 'backup',
        'exchange_type': 'direct',
        'routing_key': 'backup',
        'durable': True,
        'auto_delete': False,
        'arguments': {
            'x-max-priority': 2
        }
    },
    'statistics': {
        'exchange': 'statistics',
        'exchange_type': 'direct',
        'routing_key': 'statistics',
        'durable': True,
        'auto_delete': False,
        'arguments': {
            'x-max-priority': 4
        }
    },
}

# Task priority configuration
CELERY_TASK_PRIORITY = {
    # High priority tasks
    'app.services.tasks.monitoring.monitor_pipeline_health': 9,
    'app.services.tasks.data_ingestion.health_check': 8,
    'app.services.tasks.monitoring.monitor_data_quality': 7,
    
    # Medium priority tasks
    'app.services.tasks.data_ingestion.sync_sicap_data': 6,
    'app.services.tasks.data_ingestion.sync_anrmap_data': 6,
    'app.services.tasks.data_ingestion.incremental_sync': 5,
    'app.services.tasks.risk_analysis.analyze_tender_risks': 5,
    
    # Low priority tasks
    'app.services.tasks.notifications.send_daily_alerts': 4,
    'app.services.tasks.documents.process_pending_documents': 3,
    'app.services.tasks.enrichment.enrich_missing_data': 3,
    'app.services.tasks.statistics.generate_daily_statistics': 2,
    'app.services.tasks.maintenance.cleanup_old_sessions': 1,
    'app.services.tasks.backup.backup_critical_data': 1,
}

# Environment-specific configurations
if settings.ENVIRONMENT == 'development':
    # More frequent monitoring in development
    CELERY_BEAT_SCHEDULE['pipeline-health-check']['schedule'] = crontab(minute='*/5')
    CELERY_BEAT_SCHEDULE['data-quality-monitoring']['schedule'] = crontab(hour='*/2', minute=0)
    
    # Reduced frequency for heavy tasks
    CELERY_BEAT_SCHEDULE['sicap-full-sync']['schedule'] = crontab(hour=2, minute=0, day_of_week=1)
    CELERY_BEAT_SCHEDULE['anrmap-daily-sync']['schedule'] = crontab(hour=3, minute=0, day_of_week=1)

elif settings.ENVIRONMENT == 'production':
    # More conservative settings for production
    CELERY_BEAT_SCHEDULE['sicap-incremental-sync']['schedule'] = crontab(minute='*/45')
    CELERY_BEAT_SCHEDULE['anrmap-incremental-sync']['schedule'] = crontab(minute='0', hour='*/8')
    
    # Additional production-specific tasks
    CELERY_BEAT_SCHEDULE['production-health-check'] = {
        'task': 'app.services.tasks.monitoring.production_health_check',
        'schedule': crontab(minute='*/2'),  # Every 2 minutes
    }

# Worker configuration
CELERY_WORKER_CONFIG = {
    'worker_concurrency': 4,
    'worker_prefetch_multiplier': 1,
    'worker_max_tasks_per_child': 1000,
    'worker_disable_rate_limits': False,
    'worker_send_task_events': True,
    'task_send_sent_event': True,
    'task_track_started': True,
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'result_expires': 3600,  # 1 hour
    'timezone': 'Europe/Bucharest',
    'enable_utc': True,
}

# Monitoring configuration
CELERY_MONITORING_CONFIG = {
    'flower_port': 5555,
    'flower_basic_auth': ['admin:admin'],  # Change in production
    'flower_url_prefix': '/flower',
    'flower_persistent': True,
    'flower_db': 'flower.db',
    'flower_max_workers': 5000,
    'flower_max_tasks': 10000,
}

# Error handling configuration
CELERY_ERROR_CONFIG = {
    'task_soft_time_limit': 25 * 60,  # 25 minutes
    'task_time_limit': 30 * 60,  # 30 minutes
    'task_max_retries': 3,
    'task_default_retry_delay': 60 * 5,  # 5 minutes
    'task_retry_jitter': True,
    'worker_hijack_root_logger': False,
    'worker_log_color': True,
}

# Result backend configuration
CELERY_RESULT_CONFIG = {
    'result_backend': settings.CELERY_RESULT_BACKEND,
    'result_expires': 3600,  # 1 hour
    'result_compression': 'gzip',
    'result_serializer': 'json',
    'result_cache_max': 10000,
    'result_persistent': True,
}

# Security configuration
CELERY_SECURITY_CONFIG = {
    'worker_enable_remote_control': False,
    'worker_send_task_events': True,
    'task_send_sent_event': True,
    'task_always_eager': False,
    'task_eager_propagates': True,
    'task_ignore_result': False,
    'task_store_eager_result': True,
}

def get_celery_config():
    """Get complete Celery configuration"""
    config = {}
    
    # Add all configurations
    config.update({
        'beat_schedule': CELERY_BEAT_SCHEDULE,
        'task_routes': CELERY_TASK_ROUTES,
        'task_default_queue': 'data_ingestion',
        'task_default_exchange': 'data_ingestion',
        'task_default_exchange_type': 'direct',
        'task_default_routing_key': 'data_ingestion',
    })
    
    config.update(CELERY_WORKER_CONFIG)
    config.update(CELERY_ERROR_CONFIG)
    config.update(CELERY_RESULT_CONFIG)
    config.update(CELERY_SECURITY_CONFIG)
    
    return config