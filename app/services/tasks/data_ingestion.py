"""
Celery tasks for data ingestion from Romanian procurement sources
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from celery import Task
from celery.utils.log import get_task_logger
import uuid

from app.services.celery_app import celery_app
from app.services.scrapers.sicap_scraper import SICAPScraper
from app.services.scrapers.anrmap_scraper import ANRMAPScraper
from app.services.ingestion.data_processor import DataProcessor
from app.core.logging import logger

# Task logger
task_logger = get_task_logger(__name__)


class CallbackTask(Task):
    """Base task class with callback support"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        task_logger.info(f"Task {task_id} succeeded with result: {retval}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        task_logger.error(f"Task {task_id} failed with exception: {exc}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        task_logger.warning(f"Task {task_id} retried due to: {exc}")


@celery_app.task(
    bind=True,
    base=CallbackTask,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    rate_limit='10/m'  # 10 tasks per minute
)
def sync_sicap_data(
    self,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page_limit: Optional[int] = None,
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """Sync data from SICAP"""
    
    task_logger.info(f"Starting SICAP data sync task: {self.request.id}")
    
    try:
        # Generate job ID if not provided
        if not job_id:
            job_id = str(uuid.uuid4())
        
        # Parse dates
        date_from_obj = datetime.fromisoformat(date_from) if date_from else None
        date_to_obj = datetime.fromisoformat(date_to) if date_to else None
        
        # Run the sync
        result = asyncio.run(_sync_sicap_data_async(
            date_from_obj, date_to_obj, page_limit, job_id
        ))
        
        task_logger.info(f"SICAP sync completed: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"SICAP sync failed: {str(exc)}")
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=self.default_retry_delay)
        
        raise


async def _sync_sicap_data_async(
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    page_limit: Optional[int],
    job_id: str
) -> Dict[str, Any]:
    """Async implementation of SICAP data sync"""
    
    processor = DataProcessor()
    
    async with SICAPScraper() as scraper:
        # Scrape tender data
        tenders = await scraper.scrape_tender_list(
            date_from=date_from,
            date_to=date_to,
            page_limit=page_limit
        )
        
        # Process the data
        if tenders:
            result = await processor.process_tender_batch(
                tenders, 
                source_system='SICAP',
                job_id=job_id
            )
            
            return {
                'job_id': job_id,
                'source': 'SICAP',
                'scraped_count': len(tenders),
                'processing_result': result,
                'status': 'success'
            }
        else:
            return {
                'job_id': job_id,
                'source': 'SICAP',
                'scraped_count': 0,
                'processing_result': {},
                'status': 'no_data'
            }


@celery_app.task(
    bind=True,
    base=CallbackTask,
    max_retries=3,
    default_retry_delay=600,  # 10 minutes
    rate_limit='5/m'  # 5 tasks per minute
)
def sync_anrmap_data(
    self,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """Sync data from ANRMAP"""
    
    task_logger.info(f"Starting ANRMAP data sync task: {self.request.id}")
    
    try:
        # Generate job ID if not provided
        if not job_id:
            job_id = str(uuid.uuid4())
        
        # Parse dates
        date_from_obj = datetime.fromisoformat(date_from) if date_from else None
        date_to_obj = datetime.fromisoformat(date_to) if date_to else None
        
        # Run the sync
        result = asyncio.run(_sync_anrmap_data_async(
            date_from_obj, date_to_obj, job_id
        ))
        
        task_logger.info(f"ANRMAP sync completed: {result}")
        return result
        
    except Exception as exc:
        task_logger.error(f"ANRMAP sync failed: {str(exc)}")
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=self.default_retry_delay)
        
        raise


async def _sync_anrmap_data_async(
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    job_id: str
) -> Dict[str, Any]:
    """Async implementation of ANRMAP data sync"""
    
    processor = DataProcessor()
    
    async with ANRMAPScraper() as scraper:
        # Scrape tender data
        tenders = await scraper.scrape_tender_list(
            date_from=date_from,
            date_to=date_to
        )
        
        # Process the data
        if tenders:
            result = await processor.process_tender_batch(
                tenders, 
                source_system='ANRMAP',
                job_id=job_id
            )
            
            return {
                'job_id': job_id,
                'source': 'ANRMAP',
                'scraped_count': len(tenders),
                'processing_result': result,
                'status': 'success'
            }
        else:
            return {
                'job_id': job_id,
                'source': 'ANRMAP',
                'scraped_count': 0,
                'processing_result': {},
                'status': 'no_data'
            }


@celery_app.task(
    bind=True,
    base=CallbackTask,
    max_retries=2,
    default_retry_delay=1800,  # 30 minutes
    rate_limit='1/h'  # 1 task per hour
)
def sync_all_sources(
    self,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """Sync data from all sources"""
    
    task_logger.info(f"Starting full data sync task: {self.request.id}")
    
    try:
        # Generate job ID if not provided
        if not job_id:
            job_id = str(uuid.uuid4())
        
        results = {}
        
        # Sync SICAP
        try:
            sicap_result = sync_sicap_data.delay(
                date_from=date_from,
                date_to=date_to,
                job_id=f"{job_id}_sicap"
            ).get(timeout=3600)  # 1 hour timeout
            
            results['sicap'] = sicap_result
            
        except Exception as e:
            task_logger.error(f"SICAP sync failed in full sync: {str(e)}")
            results['sicap'] = {'status': 'failed', 'error': str(e)}
        
        # Sync ANRMAP
        try:
            anrmap_result = sync_anrmap_data.delay(
                date_from=date_from,
                date_to=date_to,
                job_id=f"{job_id}_anrmap"
            ).get(timeout=3600)  # 1 hour timeout
            
            results['anrmap'] = anrmap_result
            
        except Exception as e:
            task_logger.error(f"ANRMAP sync failed in full sync: {str(e)}")
            results['anrmap'] = {'status': 'failed', 'error': str(e)}
        
        # Calculate overall status
        successful_sources = sum(1 for result in results.values() if result.get('status') == 'success')
        total_sources = len(results)
        
        overall_status = 'success' if successful_sources == total_sources else 'partial'
        
        return {
            'job_id': job_id,
            'overall_status': overall_status,
            'successful_sources': successful_sources,
            'total_sources': total_sources,
            'results': results,
            'completed_at': datetime.now().isoformat()
        }
        
    except Exception as exc:
        task_logger.error(f"Full sync failed: {str(exc)}")
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=self.default_retry_delay)
        
        raise


@celery_app.task(
    bind=True,
    base=CallbackTask,
    max_retries=3,
    default_retry_delay=300,
    rate_limit='20/m'
)
def scrape_tender_details(
    self,
    source_system: str,
    tender_id: str,
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """Scrape detailed information for a specific tender"""
    
    task_logger.info(f"Starting tender details scraping: {tender_id} from {source_system}")
    
    try:
        # Generate job ID if not provided
        if not job_id:
            job_id = str(uuid.uuid4())
        
        result = asyncio.run(_scrape_tender_details_async(
            source_system, tender_id, job_id
        ))
        
        task_logger.info(f"Tender details scraping completed: {tender_id}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Tender details scraping failed: {str(exc)}")
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=self.default_retry_delay)
        
        raise


async def _scrape_tender_details_async(
    source_system: str,
    tender_id: str,
    job_id: str
) -> Dict[str, Any]:
    """Async implementation of tender details scraping"""
    
    processor = DataProcessor()
    
    if source_system == 'SICAP':
        async with SICAPScraper() as scraper:
            tender_data = await scraper.scrape_tender_details(tender_id)
            
            if tender_data:
                # Process the detailed data
                result = await processor.process_tender_batch(
                    [tender_data], 
                    source_system='SICAP',
                    job_id=job_id
                )
                
                return {
                    'job_id': job_id,
                    'source': source_system,
                    'tender_id': tender_id,
                    'processing_result': result,
                    'status': 'success'
                }
    
    elif source_system == 'ANRMAP':
        async with ANRMAPScraper() as scraper:
            tender_data = await scraper.scrape_tender_details(tender_id)
            
            if tender_data:
                # Process the detailed data
                result = await processor.process_tender_batch(
                    [tender_data], 
                    source_system='ANRMAP',
                    job_id=job_id
                )
                
                return {
                    'job_id': job_id,
                    'source': source_system,
                    'tender_id': tender_id,
                    'processing_result': result,
                    'status': 'success'
                }
    
    return {
        'job_id': job_id,
        'source': source_system,
        'tender_id': tender_id,
        'processing_result': {},
        'status': 'no_data'
    }


@celery_app.task(
    bind=True,
    base=CallbackTask,
    max_retries=2,
    default_retry_delay=900,  # 15 minutes
    rate_limit='1/5m'  # 1 task per 5 minutes
)
def incremental_sync(
    self,
    source_system: str,
    hours_back: int = 24,
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """Perform incremental sync for recent data"""
    
    task_logger.info(f"Starting incremental sync for {source_system}")
    
    try:
        # Generate job ID if not provided
        if not job_id:
            job_id = str(uuid.uuid4())
        
        # Calculate date range
        date_to = datetime.now()
        date_from = date_to - timedelta(hours=hours_back)
        
        # Run incremental sync based on source
        if source_system == 'SICAP':
            result = sync_sicap_data.delay(
                date_from=date_from.isoformat(),
                date_to=date_to.isoformat(),
                page_limit=10,  # Limit pages for incremental sync
                job_id=job_id
            ).get(timeout=1800)  # 30 minutes timeout
            
        elif source_system == 'ANRMAP':
            result = sync_anrmap_data.delay(
                date_from=date_from.isoformat(),
                date_to=date_to.isoformat(),
                job_id=job_id
            ).get(timeout=1800)  # 30 minutes timeout
            
        else:
            raise ValueError(f"Unknown source system: {source_system}")
        
        task_logger.info(f"Incremental sync completed for {source_system}")
        return result
        
    except Exception as exc:
        task_logger.error(f"Incremental sync failed for {source_system}: {str(exc)}")
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=self.default_retry_delay)
        
        raise


@celery_app.task(
    bind=True,
    base=CallbackTask,
    max_retries=1,
    default_retry_delay=3600,  # 1 hour
    rate_limit='1/30m'  # 1 task per 30 minutes
)
def bulk_process_tender_documents(
    self,
    tender_ids: List[str],
    source_system: str,
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """Bulk process documents for multiple tenders"""
    
    task_logger.info(f"Starting bulk document processing for {len(tender_ids)} tenders")
    
    try:
        # Generate job ID if not provided
        if not job_id:
            job_id = str(uuid.uuid4())
        
        result = asyncio.run(_bulk_process_documents_async(
            tender_ids, source_system, job_id
        ))
        
        task_logger.info(f"Bulk document processing completed")
        return result
        
    except Exception as exc:
        task_logger.error(f"Bulk document processing failed: {str(exc)}")
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=self.default_retry_delay)
        
        raise


async def _bulk_process_documents_async(
    tender_ids: List[str],
    source_system: str,
    job_id: str
) -> Dict[str, Any]:
    """Async implementation of bulk document processing"""
    
    processed_count = 0
    failed_count = 0
    
    if source_system == 'SICAP':
        async with SICAPScraper() as scraper:
            for tender_id in tender_ids:
                try:
                    documents = await scraper.scrape_tender_documents(tender_id)
                    
                    if documents:
                        # Process documents (store metadata, download if needed)
                        # This would involve additional processing logic
                        processed_count += 1
                    
                except Exception as e:
                    task_logger.error(f"Failed to process documents for tender {tender_id}: {str(e)}")
                    failed_count += 1
                    continue
    
    elif source_system == 'ANRMAP':
        async with ANRMAPScraper() as scraper:
            for tender_id in tender_ids:
                try:
                    documents = await scraper.scrape_tender_documents(tender_id)
                    
                    if documents:
                        processed_count += 1
                    
                except Exception as e:
                    task_logger.error(f"Failed to process documents for tender {tender_id}: {str(e)}")
                    failed_count += 1
                    continue
    
    return {
        'job_id': job_id,
        'source': source_system,
        'total_tenders': len(tender_ids),
        'processed_count': processed_count,
        'failed_count': failed_count,
        'status': 'success' if failed_count == 0 else 'partial'
    }


# Periodic tasks for regular data synchronization
@celery_app.task(
    bind=True,
    base=CallbackTask,
    max_retries=1
)
def daily_full_sync(self) -> Dict[str, Any]:
    """Daily full synchronization of all sources"""
    
    task_logger.info("Starting daily full sync")
    
    try:
        # Run full sync for yesterday's data
        date_to = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        date_from = date_to - timedelta(days=1)
        
        result = sync_all_sources.delay(
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
            job_id=f"daily_sync_{date_from.strftime('%Y%m%d')}"
        ).get(timeout=7200)  # 2 hours timeout
        
        task_logger.info("Daily full sync completed")
        return result
        
    except Exception as exc:
        task_logger.error(f"Daily full sync failed: {str(exc)}")
        raise


@celery_app.task(
    bind=True,
    base=CallbackTask,
    max_retries=1
)
def hourly_incremental_sync(self) -> Dict[str, Any]:
    """Hourly incremental synchronization"""
    
    task_logger.info("Starting hourly incremental sync")
    
    try:
        results = {}
        
        # Sync SICAP incrementally
        sicap_result = incremental_sync.delay(
            source_system='SICAP',
            hours_back=2,  # 2 hours back to ensure overlap
            job_id=f"hourly_sicap_{datetime.now().strftime('%Y%m%d_%H')}"
        ).get(timeout=1800)
        
        results['sicap'] = sicap_result
        
        task_logger.info("Hourly incremental sync completed")
        return results
        
    except Exception as exc:
        task_logger.error(f"Hourly incremental sync failed: {str(exc)}")
        raise


# Task monitoring and management
@celery_app.task(bind=True, base=CallbackTask)
def health_check(self) -> Dict[str, Any]:
    """Health check task for monitoring"""
    
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'task_id': self.request.id,
        'worker_id': self.request.hostname
    }


@celery_app.task(bind=True, base=CallbackTask)
def cleanup_old_logs(self, days_to_keep: int = 30) -> Dict[str, Any]:
    """Cleanup old ingestion logs"""
    
    task_logger.info(f"Starting cleanup of logs older than {days_to_keep} days")
    
    try:
        # This would implement cleanup logic
        # For now, return success
        return {
            'status': 'success',
            'days_to_keep': days_to_keep,
            'cleaned_at': datetime.now().isoformat()
        }
        
    except Exception as exc:
        task_logger.error(f"Log cleanup failed: {str(exc)}")
        raise