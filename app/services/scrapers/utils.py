"""
Utility classes and functions for web scraping
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import aiohttp
import random
import json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
import unicodedata
from unidecode import unidecode

from app.core.config import settings
from app.core.logging import logger


class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a call"""
        async with self.lock:
            now = time.time()
            
            # Remove old calls outside the time window
            self.calls = [call_time for call_time in self.calls 
                         if now - call_time < self.time_window]
            
            # Check if we can make a call
            if len(self.calls) >= self.max_calls:
                # Calculate wait time
                oldest_call = min(self.calls)
                wait_time = self.time_window - (now - oldest_call)
                
                if wait_time > 0:
                    logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    return await self.acquire()
            
            # Record this call
            self.calls.append(now)


class ScrapingSession:
    """HTTP session with scraping-specific configuration"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session = None
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
    
    async def __aenter__(self):
        """Create session with proper headers"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers=self._get_headers()
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close session"""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get randomized headers for requests"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ro-RO,ro;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make HTTP request with session"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        # Add randomized delay
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        return await self.session.request(method, url, **kwargs)


class HTMLParser:
    """HTML parsing utilities"""
    
    @staticmethod
    def parse_html(html_content: str) -> BeautifulSoup:
        """Parse HTML content with BeautifulSoup"""
        return BeautifulSoup(html_content, 'html.parser')
    
    @staticmethod
    def extract_text(element) -> str:
        """Extract and clean text from HTML element"""
        if element is None:
            return ""
        
        text = element.get_text(strip=True)
        return TextCleaner.clean_text(text)
    
    @staticmethod
    def extract_links(soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from HTML"""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('http'):
                links.append(href)
            elif href.startswith('/'):
                links.append(urljoin(base_url, href))
        
        return links
    
    @staticmethod
    def extract_table_data(table) -> List[Dict[str, str]]:
        """Extract data from HTML table"""
        if not table:
            return []
        
        rows = table.find_all('tr')
        if not rows:
            return []
        
        # Get headers
        header_row = rows[0]
        headers = [HTMLParser.extract_text(th) for th in header_row.find_all(['th', 'td'])]
        
        # Get data rows
        data_rows = []
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) == len(headers):
                row_data = {}
                for i, cell in enumerate(cells):
                    row_data[headers[i]] = HTMLParser.extract_text(cell)
                data_rows.append(row_data)
        
        return data_rows


class TextCleaner:
    """Text cleaning and normalization utilities"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Normalize Unicode characters
        text = unicodedata.normalize('NFKD', text)
        
        # Remove non-printable characters
        text = ''.join(char for char in text if char.isprintable() or char.isspace())
        
        return text.strip()
    
    @staticmethod
    def normalize_romanian_text(text: str) -> str:
        """Normalize Romanian text (handle diacritics)"""
        if not text:
            return ""
        
        # Romanian diacritics mapping
        diacritics_map = {
            'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ț': 't',
            'Ă': 'A', 'Â': 'A', 'Î': 'I', 'Ș': 'S', 'Ț': 'T'
        }
        
        # Replace diacritics
        for diacritic, replacement in diacritics_map.items():
            text = text.replace(diacritic, replacement)
        
        return TextCleaner.clean_text(text)
    
    @staticmethod
    def extract_currency_amount(text: str) -> Optional[float]:
        """Extract currency amount from text"""
        if not text:
            return None
        
        # Remove common currency symbols and words
        text = re.sub(r'(RON|EUR|USD|lei|euro|dolari)', '', text, flags=re.IGNORECASE)
        
        # Find number patterns
        pattern = r'[\d,.\s]+(?:\d{2})?'
        matches = re.findall(pattern, text)
        
        if not matches:
            return None
        
        # Process the first match
        amount_str = matches[0].replace(',', '').replace(' ', '')
        
        try:
            return float(amount_str)
        except ValueError:
            return None
    
    @staticmethod
    def extract_date(text: str) -> Optional[datetime]:
        """Extract date from Romanian text"""
        if not text:
            return None
        
        # Common Romanian date patterns
        patterns = [
            r'(\d{1,2})[./](\d{1,2})[./](\d{4})',  # dd.mm.yyyy or dd/mm/yyyy
            r'(\d{4})[.-](\d{1,2})[.-](\d{1,2})',  # yyyy-mm-dd
            r'(\d{1,2})\s+(ianuarie|februarie|martie|aprilie|mai|iunie|iulie|august|septembrie|octombrie|noiembrie|decembrie)\s+(\d{4})'
        ]
        
        # Romanian months mapping
        months_map = {
            'ianuarie': 1, 'februarie': 2, 'martie': 3, 'aprilie': 4,
            'mai': 5, 'iunie': 6, 'iulie': 7, 'august': 8,
            'septembrie': 9, 'octombrie': 10, 'noiembrie': 11, 'decembrie': 12
        }
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if 'ianuarie' in pattern:  # Month name pattern
                        day = int(match.group(1))
                        month = months_map[match.group(2).lower()]
                        year = int(match.group(3))
                    elif pattern.startswith(r'(\d{4})'):  # yyyy-mm-dd pattern
                        year = int(match.group(1))
                        month = int(match.group(2))
                        day = int(match.group(3))
                    else:  # dd.mm.yyyy pattern
                        day = int(match.group(1))
                        month = int(match.group(2))
                        year = int(match.group(3))
                    
                    return datetime(year, month, day)
                except (ValueError, KeyError):
                    continue
        
        return None


class DataValidator:
    """Data validation utilities"""
    
    @staticmethod
    def validate_tender_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tender data and return cleaned version"""
        validated = {}
        
        # Required fields
        required_fields = ['title', 'source_system', 'external_id']
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValueError(f"Missing required field: {field}")
            validated[field] = str(data[field]).strip()
        
        # Optional fields with cleaning
        optional_fields = {
            'description': str,
            'estimated_value': float,
            'currency': str,
            'tender_type': str,
            'procedure_type': str,
            'status': str
        }
        
        for field, field_type in optional_fields.items():
            if field in data and data[field]:
                try:
                    if field_type == float:
                        validated[field] = TextCleaner.extract_currency_amount(str(data[field]))
                    else:
                        validated[field] = field_type(data[field]).strip()
                except (ValueError, TypeError):
                    logger.warning(f"Invalid value for field {field}: {data[field]}")
        
        # Date fields
        date_fields = ['publication_date', 'submission_deadline', 'opening_date']
        for field in date_fields:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    validated[field] = TextCleaner.extract_date(data[field])
                elif isinstance(data[field], datetime):
                    validated[field] = data[field]
        
        return validated
    
    @staticmethod
    def validate_cui(cui: str) -> bool:
        """Validate Romanian CUI (Cod Unic de Identificare)"""
        if not cui:
            return False
        
        # Remove spaces and convert to uppercase
        cui = cui.replace(' ', '').upper()
        
        # Remove RO prefix if present
        if cui.startswith('RO'):
            cui = cui[2:]
        
        # Check if it's numeric and has correct length
        if not cui.isdigit() or len(cui) < 2 or len(cui) > 10:
            return False
        
        return True
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address"""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None


class CacheManager:
    """Simple in-memory cache for scraping results"""
    
    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache"""
        self.cache[key] = (value, time.time())
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
    
    def cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp >= self.ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]


class ScrapingMetrics:
    """Metrics collection for scraping operations"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all metrics"""
        self.start_time = time.time()
        self.requests_made = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.items_scraped = 0
        self.errors = []
        self.response_times = []
    
    def record_request(self, success: bool, response_time: float):
        """Record a request"""
        self.requests_made += 1
        self.response_times.append(response_time)
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
    
    def record_error(self, error: str, url: str = None):
        """Record an error"""
        self.errors.append({
            'error': error,
            'url': url,
            'timestamp': time.time()
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        duration = time.time() - self.start_time
        
        return {
            'duration': duration,
            'requests_made': self.requests_made,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.successful_requests / max(self.requests_made, 1) * 100,
            'items_scraped': self.items_scraped,
            'avg_response_time': sum(self.response_times) / max(len(self.response_times), 1),
            'errors_count': len(self.errors),
            'requests_per_second': self.requests_made / max(duration, 1)
        }