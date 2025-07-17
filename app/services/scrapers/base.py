"""
Base scraper classes and utilities for Romanian procurement data sources
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin, urlparse
import aiohttp
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from pybreaker import CircuitBreaker
import hashlib
import json

from app.core.config import settings
from app.core.logging import logger
from app.services.scrapers.utils import RateLimiter, ScrapingSession


class BaseScraper(ABC):
    """Abstract base class for all scrapers"""
    
    def __init__(
        self,
        source_name: str,
        base_url: str,
        rate_limit: int = 60,
        timeout: int = 30,
        retry_attempts: int = 3
    ):
        self.source_name = source_name
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        
        # Initialize components
        self.rate_limiter = RateLimiter(max_calls=rate_limit, time_window=60)
        self.session = ScrapingSession(timeout=timeout)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception
        )
        
        # Metrics tracking
        self.metrics = {
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'items_scraped': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }
        
        logger.info(f"Initialized {source_name} scraper")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.session.__aenter__()
        self.metrics['start_time'] = datetime.now()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.session.__aexit__(exc_type, exc_val, exc_tb)
        self.metrics['end_time'] = datetime.now()
        await self._log_metrics()
    
    @abstractmethod
    async def scrape_tender_list(
        self, 
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page_limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Scrape list of tenders"""
        pass
    
    @abstractmethod
    async def scrape_tender_details(self, tender_id: str) -> Dict[str, Any]:
        """Scrape detailed information for a specific tender"""
        pass
    
    @abstractmethod
    async def scrape_tender_documents(self, tender_id: str) -> List[Dict[str, Any]]:
        """Scrape documents for a specific tender"""
        pass
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def make_request(
        self,
        url: str,
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> aiohttp.ClientResponse:
        """Make HTTP request with rate limiting and retry logic"""
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        # Track request
        self.metrics['requests_made'] += 1
        
        try:
            # Use circuit breaker
            response = await self.circuit_breaker.call(
                self.session.request,
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data
            )
            
            if response.status == 200:
                self.metrics['successful_requests'] += 1
                logger.debug(f"Successful request to {url}")
                return response
            else:
                self.metrics['failed_requests'] += 1
                logger.warning(f"Request to {url} failed with status {response.status}")
                raise aiohttp.ClientError(f"HTTP {response.status}")
                
        except Exception as e:
            self.metrics['failed_requests'] += 1
            self.metrics['errors'].append({
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            logger.error(f"Request to {url} failed: {str(e)}")
            raise
    
    async def get_page_content(self, url: str) -> str:
        """Get page content as text"""
        response = await self.make_request(url)
        return await response.text()
    
    async def get_json_content(self, url: str) -> Dict[str, Any]:
        """Get JSON content from URL"""
        response = await self.make_request(url)
        return await response.json()
    
    def generate_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """Generate cache key for URL and parameters"""
        key_data = f"{url}_{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def _log_metrics(self):
        """Log scraping metrics"""
        if self.metrics['start_time'] and self.metrics['end_time']:
            duration = self.metrics['end_time'] - self.metrics['start_time']
            
            logger.info(
                f"Scraping metrics for {self.source_name}: "
                f"Duration: {duration.total_seconds():.2f}s, "
                f"Requests: {self.metrics['requests_made']}, "
                f"Successful: {self.metrics['successful_requests']}, "
                f"Failed: {self.metrics['failed_requests']}, "
                f"Items: {self.metrics['items_scraped']}"
            )
            
            if self.metrics['errors']:
                logger.warning(f"Errors encountered: {len(self.metrics['errors'])}")
                for error in self.metrics['errors'][-5:]:  # Log last 5 errors
                    logger.warning(f"Error: {error}")


class PaginatedScraper(BaseScraper):
    """Base class for scrapers that handle pagination"""
    
    async def scrape_paginated_data(
        self,
        base_url: str,
        params: Dict[str, Any],
        page_param: str = 'page',
        start_page: int = 1,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Scrape data from paginated endpoints"""
        
        all_items = []
        current_page = start_page
        
        while True:
            # Update page parameter
            current_params = params.copy()
            current_params[page_param] = current_page
            
            try:
                page_data = await self.get_page_data(base_url, current_params)
                
                if not page_data:
                    logger.info(f"No data found on page {current_page}, stopping pagination")
                    break
                
                all_items.extend(page_data)
                self.metrics['items_scraped'] += len(page_data)
                
                logger.info(f"Scraped {len(page_data)} items from page {current_page}")
                
                # Check if we should continue
                if max_pages and current_page >= max_pages:
                    logger.info(f"Reached maximum pages limit ({max_pages})")
                    break
                
                # Check if this was the last page
                if not await self.has_next_page(page_data):
                    logger.info(f"Reached last page at page {current_page}")
                    break
                
                current_page += 1
                
                # Add delay between page requests
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error scraping page {current_page}: {str(e)}")
                break
        
        return all_items
    
    @abstractmethod
    async def get_page_data(self, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get data from a single page"""
        pass
    
    @abstractmethod
    async def has_next_page(self, page_data: List[Dict[str, Any]]) -> bool:
        """Check if there are more pages to scrape"""
        pass


class DocumentScraper(BaseScraper):
    """Base class for scrapers that handle document downloads"""
    
    async def download_document(
        self,
        url: str,
        filename: str,
        max_size: int = 10 * 1024 * 1024  # 10MB
    ) -> Optional[str]:
        """Download document from URL"""
        
        try:
            response = await self.make_request(url)
            
            # Check content length
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > max_size:
                logger.warning(f"Document too large: {content_length} bytes")
                return None
            
            # Read content
            content = await response.read()
            
            if len(content) > max_size:
                logger.warning(f"Document too large: {len(content)} bytes")
                return None
            
            # Save to file (in production, use proper file storage)
            file_path = f"{settings.UPLOAD_FOLDER}/{filename}"
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"Downloaded document: {filename}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading document from {url}: {str(e)}")
            return None
    
    async def extract_text_from_pdf(self, file_path: str) -> Optional[str]:
        """Extract text from PDF file"""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                return text.strip()
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
            return None


class ScrapingError(Exception):
    """Base exception for scraping errors"""
    pass


class RateLimitError(ScrapingError):
    """Raised when rate limit is exceeded"""
    pass


class DataExtractionError(ScrapingError):
    """Raised when data extraction fails"""
    pass


class ValidationError(ScrapingError):
    """Raised when data validation fails"""
    pass