"""
ANRMAP (Autoritatea Nationala pentru Reglementarea si Monitorizarea Achizitiilor Publice) scraper
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
import json

from app.services.scrapers.base import BaseScraper, DocumentScraper
from app.services.scrapers.utils import HTMLParser, TextCleaner, DataValidator
from app.core.logging import logger


class ANRMAPScraper(DocumentScraper):
    """ANRMAP scraper for Romanian procurement regulatory data"""
    
    def __init__(self):
        super().__init__(
            source_name="ANRMAP",
            base_url="http://anrmap.gov.ro",
            rate_limit=20,  # 20 requests per minute (more conservative)
            timeout=60,     # Longer timeout for PDF processing
            retry_attempts=3
        )
        
        # ANRMAP specific URLs
        self.reports_url = f"{self.base_url}/rapoarte"
        self.statistics_url = f"{self.base_url}/statistici"
        self.monitoring_url = f"{self.base_url}/monitorizare"
        self.legislation_url = f"{self.base_url}/legislatie"
        
        # Document types we're interested in
        self.document_types = {
            'reports': 'rapoarte',
            'statistics': 'statistici',
            'monitoring': 'monitorizare',
            'legislation': 'legislatie'
        }
    
    async def scrape_tender_list(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page_limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Scrape tender data from ANRMAP reports and monitoring"""
        
        logger.info(f"Starting ANRMAP data scraping from {date_from} to {date_to}")
        
        all_tenders = []
        
        # Scrape from different sections
        sections = [
            ('reports', self.reports_url),
            ('monitoring', self.monitoring_url),
            ('statistics', self.statistics_url)
        ]
        
        for section_name, section_url in sections:
            try:
                logger.info(f"Scraping {section_name} from {section_url}")
                
                section_data = await self.scrape_section(
                    section_url,
                    section_name,
                    date_from,
                    date_to
                )
                
                all_tenders.extend(section_data)
                
            except Exception as e:
                logger.error(f"Error scraping {section_name}: {str(e)}")
                continue
        
        logger.info(f"Scraped {len(all_tenders)} items from ANRMAP")
        return all_tenders
    
    async def scrape_section(
        self,
        section_url: str,
        section_name: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Scrape data from a specific ANRMAP section"""
        
        try:
            response = await self.make_request(section_url)
            content = await response.text()
            
            soup = HTMLParser.parse_html(content)
            
            # Extract documents and reports
            items = []
            
            # Look for document links
            document_links = soup.find_all('a', href=re.compile(r'\.(pdf|doc|docx|xls|xlsx)$', re.I))
            
            for link in document_links:
                try:
                    item_data = await self._extract_item_from_link(link, section_name)
                    
                    if item_data:
                        # Filter by date if specified
                        if self._is_within_date_range(item_data, date_from, date_to):
                            items.append(item_data)
                            
                except Exception as e:
                    logger.warning(f"Error extracting item from link: {str(e)}")
                    continue
            
            # Look for structured data in tables
            tables = soup.find_all('table')
            for table in tables:
                try:
                    table_items = await self._extract_items_from_table(table, section_name)
                    
                    for item in table_items:
                        if self._is_within_date_range(item, date_from, date_to):
                            items.append(item)
                            
                except Exception as e:
                    logger.warning(f"Error extracting items from table: {str(e)}")
                    continue
            
            return items
            
        except Exception as e:
            logger.error(f"Error scraping section {section_url}: {str(e)}")
            return []
    
    async def _extract_item_from_link(self, link, section_name: str) -> Optional[Dict[str, Any]]:
        """Extract item data from document link"""
        
        try:
            href = link.get('href', '')
            if not href:
                return None
            
            # Make URL absolute
            if not href.startswith('http'):
                href = urljoin(self.base_url, href)
            
            # Extract title
            title = HTMLParser.extract_text(link)
            if not title:
                # Try to get title from parent elements
                parent = link.parent
                if parent:
                    title = HTMLParser.extract_text(parent)
            
            # Extract date from title or surrounding text
            date_value = self._extract_date_from_context(link)
            
            # Determine document type
            doc_type = self._determine_document_type(href)
            
            item_data = {
                'source_system': 'ANRMAP',
                'external_id': self._generate_external_id(href),
                'title': title,
                'description': f"ANRMAP {section_name} document",
                'section': section_name,
                'document_url': href,
                'document_type': doc_type,
                'publication_date': date_value,
                'status': 'published',
                'raw_data': {
                    'section': section_name,
                    'original_url': href
                }
            }
            
            return item_data
            
        except Exception as e:
            logger.warning(f"Error extracting item from link: {str(e)}")
            return None
    
    async def _extract_items_from_table(self, table, section_name: str) -> List[Dict[str, Any]]:
        """Extract items from HTML table"""
        
        items = []
        
        try:
            table_data = HTMLParser.extract_table_data(table)
            
            for row in table_data:
                try:
                    # Look for tender-related information
                    item_data = self._process_table_row(row, section_name)
                    
                    if item_data:
                        items.append(item_data)
                        
                except Exception as e:
                    logger.warning(f"Error processing table row: {str(e)}")
                    continue
            
        except Exception as e:
            logger.warning(f"Error extracting items from table: {str(e)}")
        
        return items
    
    def _process_table_row(self, row: Dict[str, str], section_name: str) -> Optional[Dict[str, Any]]:
        """Process a single table row into item data"""
        
        try:
            # Look for key fields
            title = ""
            description = ""
            date_value = None
            value_amount = None
            
            # Extract information from row columns
            for key, value in row.items():
                key_lower = key.lower()
                
                if any(keyword in key_lower for keyword in ['titlu', 'denumire', 'obiect']):
                    title = value
                elif any(keyword in key_lower for keyword in ['descriere', 'detalii']):
                    description = value
                elif any(keyword in key_lower for keyword in ['data', 'perioada']):
                    date_value = TextCleaner.extract_date(value)
                elif any(keyword in key_lower for keyword in ['valoare', 'suma']):
                    value_amount = TextCleaner.extract_currency_amount(value)
            
            # Only create item if we have meaningful data
            if not title and not description:
                return None
            
            item_data = {
                'source_system': 'ANRMAP',
                'external_id': self._generate_external_id(f"{section_name}_{title}_{date_value}"),
                'title': title or f"ANRMAP {section_name} entry",
                'description': description,
                'section': section_name,
                'estimated_value': value_amount,
                'currency': 'RON',
                'publication_date': date_value,
                'status': 'published',
                'raw_data': {
                    'section': section_name,
                    'table_row': row
                }
            }
            
            return item_data
            
        except Exception as e:
            logger.warning(f"Error processing table row: {str(e)}")
            return None
    
    def _extract_date_from_context(self, link) -> Optional[datetime]:
        """Extract date from link context"""
        
        try:
            # Check link text
            link_text = HTMLParser.extract_text(link)
            date_value = TextCleaner.extract_date(link_text)
            
            if date_value:
                return date_value
            
            # Check parent elements
            parent = link.parent
            for _ in range(3):  # Check up to 3 levels up
                if parent:
                    parent_text = HTMLParser.extract_text(parent)
                    date_value = TextCleaner.extract_date(parent_text)
                    
                    if date_value:
                        return date_value
                    
                    parent = parent.parent
                else:
                    break
            
            # Check siblings
            if link.parent:
                siblings = link.parent.find_all(text=True)
                for sibling in siblings:
                    date_value = TextCleaner.extract_date(sibling)
                    if date_value:
                        return date_value
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting date from context: {str(e)}")
            return None
    
    def _generate_external_id(self, source: str) -> str:
        """Generate external ID from source"""
        import hashlib
        
        # Create a hash of the source string
        return hashlib.md5(source.encode()).hexdigest()[:16]
    
    def _determine_document_type(self, url: str) -> str:
        """Determine document type from URL"""
        url_lower = url.lower()
        
        if '.pdf' in url_lower:
            return 'pdf'
        elif '.doc' in url_lower or '.docx' in url_lower:
            return 'document'
        elif '.xls' in url_lower or '.xlsx' in url_lower:
            return 'spreadsheet'
        elif '.zip' in url_lower or '.rar' in url_lower:
            return 'archive'
        else:
            return 'unknown'
    
    def _is_within_date_range(
        self,
        item: Dict[str, Any],
        date_from: Optional[datetime],
        date_to: Optional[datetime]
    ) -> bool:
        """Check if item is within specified date range"""
        
        item_date = item.get('publication_date')
        
        if not item_date:
            return True  # Include items without dates
        
        if date_from and item_date < date_from:
            return False
        
        if date_to and item_date > date_to:
            return False
        
        return True
    
    async def scrape_tender_details(self, tender_id: str) -> Dict[str, Any]:
        """Scrape detailed information for a specific ANRMAP item"""
        
        logger.info(f"Scraping ANRMAP details for item {tender_id}")
        
        try:
            # For ANRMAP, we need to handle different types of detailed data
            # This could involve downloading and processing documents
            
            # Try to find the item in our scraped data
            # In a real implementation, we'd need to store the original URL
            # and re-scrape the specific document or page
            
            details = {
                'source_system': 'ANRMAP',
                'external_id': tender_id,
                'scraped_at': datetime.now().isoformat(),
                'raw_data': {}
            }
            
            # If we have a document URL, try to process it
            # This would require additional logic to handle different document types
            
            return details
            
        except Exception as e:
            logger.error(f"Error scraping ANRMAP details for {tender_id}: {str(e)}")
            return {}
    
    async def scrape_tender_documents(self, tender_id: str) -> List[Dict[str, Any]]:
        """Scrape documents for a specific ANRMAP item"""
        
        logger.info(f"Scraping ANRMAP documents for item {tender_id}")
        
        try:
            # For ANRMAP, documents are typically the main content
            # We'd need to download and process the actual documents
            
            documents = []
            
            # This would involve:
            # 1. Finding the document URL for the tender_id
            # 2. Downloading the document
            # 3. Extracting text content
            # 4. Processing the content for structured data
            
            return documents
            
        except Exception as e:
            logger.error(f"Error scraping ANRMAP documents for {tender_id}: {str(e)}")
            return []
    
    async def scrape_reports(self, report_type: str = 'all') -> List[Dict[str, Any]]:
        """Scrape specific types of reports from ANRMAP"""
        
        logger.info(f"Scraping ANRMAP reports of type: {report_type}")
        
        try:
            reports = []
            
            if report_type == 'all' or report_type == 'annual':
                annual_reports = await self._scrape_annual_reports()
                reports.extend(annual_reports)
            
            if report_type == 'all' or report_type == 'monthly':
                monthly_reports = await self._scrape_monthly_reports()
                reports.extend(monthly_reports)
            
            if report_type == 'all' or report_type == 'statistics':
                statistics = await self._scrape_statistics()
                reports.extend(statistics)
            
            return reports
            
        except Exception as e:
            logger.error(f"Error scraping ANRMAP reports: {str(e)}")
            return []
    
    async def _scrape_annual_reports(self) -> List[Dict[str, Any]]:
        """Scrape annual reports from ANRMAP"""
        
        try:
            annual_reports_url = f"{self.reports_url}/anuale"
            
            response = await self.make_request(annual_reports_url)
            content = await response.text()
            
            soup = HTMLParser.parse_html(content)
            
            reports = []
            
            # Look for annual report links
            report_links = soup.find_all('a', href=re.compile(r'raport.*anual', re.I))
            
            for link in report_links:
                try:
                    report_data = await self._extract_report_data(link, 'annual')
                    if report_data:
                        reports.append(report_data)
                        
                except Exception as e:
                    logger.warning(f"Error extracting annual report: {str(e)}")
                    continue
            
            return reports
            
        except Exception as e:
            logger.error(f"Error scraping annual reports: {str(e)}")
            return []
    
    async def _scrape_monthly_reports(self) -> List[Dict[str, Any]]:
        """Scrape monthly reports from ANRMAP"""
        
        try:
            monthly_reports_url = f"{self.reports_url}/lunare"
            
            response = await self.make_request(monthly_reports_url)
            content = await response.text()
            
            soup = HTMLParser.parse_html(content)
            
            reports = []
            
            # Look for monthly report links
            report_links = soup.find_all('a', href=re.compile(r'raport.*lunar', re.I))
            
            for link in report_links:
                try:
                    report_data = await self._extract_report_data(link, 'monthly')
                    if report_data:
                        reports.append(report_data)
                        
                except Exception as e:
                    logger.warning(f"Error extracting monthly report: {str(e)}")
                    continue
            
            return reports
            
        except Exception as e:
            logger.error(f"Error scraping monthly reports: {str(e)}")
            return []
    
    async def _scrape_statistics(self) -> List[Dict[str, Any]]:
        """Scrape statistics from ANRMAP"""
        
        try:
            response = await self.make_request(self.statistics_url)
            content = await response.text()
            
            soup = HTMLParser.parse_html(content)
            
            statistics = []
            
            # Look for statistics tables and data
            tables = soup.find_all('table')
            
            for table in tables:
                try:
                    table_data = HTMLParser.extract_table_data(table)
                    
                    if table_data:
                        stat_data = {
                            'source_system': 'ANRMAP',
                            'external_id': self._generate_external_id(f"statistics_{len(statistics)}"),
                            'title': 'ANRMAP Statistics',
                            'description': 'Statistical data from ANRMAP',
                            'section': 'statistics',
                            'data_type': 'statistics',
                            'table_data': table_data,
                            'scraped_at': datetime.now().isoformat(),
                            'raw_data': {
                                'section': 'statistics',
                                'table_html': str(table)
                            }
                        }
                        
                        statistics.append(stat_data)
                        
                except Exception as e:
                    logger.warning(f"Error extracting statistics table: {str(e)}")
                    continue
            
            return statistics
            
        except Exception as e:
            logger.error(f"Error scraping statistics: {str(e)}")
            return []
    
    async def _extract_report_data(self, link, report_type: str) -> Optional[Dict[str, Any]]:
        """Extract data from a report link"""
        
        try:
            href = link.get('href', '')
            if not href:
                return None
            
            # Make URL absolute
            if not href.startswith('http'):
                href = urljoin(self.base_url, href)
            
            title = HTMLParser.extract_text(link)
            date_value = self._extract_date_from_context(link)
            
            report_data = {
                'source_system': 'ANRMAP',
                'external_id': self._generate_external_id(href),
                'title': title or f"ANRMAP {report_type} report",
                'description': f"ANRMAP {report_type} report",
                'section': 'reports',
                'report_type': report_type,
                'document_url': href,
                'document_type': self._determine_document_type(href),
                'publication_date': date_value,
                'status': 'published',
                'raw_data': {
                    'section': 'reports',
                    'report_type': report_type,
                    'original_url': href
                }
            }
            
            return report_data
            
        except Exception as e:
            logger.warning(f"Error extracting report data: {str(e)}")
            return None
    
    async def download_and_process_document(self, document_url: str) -> Optional[Dict[str, Any]]:
        """Download and process a document from ANRMAP"""
        
        try:
            # Extract filename from URL
            parsed_url = urlparse(document_url)
            filename = parsed_url.path.split('/')[-1]
            
            if not filename:
                filename = f"anrmap_doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            # Download document
            file_path = await self.download_document(document_url, filename)
            
            if not file_path:
                return None
            
            # Extract text content
            text_content = None
            
            if filename.lower().endswith('.pdf'):
                text_content = await self.extract_text_from_pdf(file_path)
            
            document_data = {
                'url': document_url,
                'filename': filename,
                'file_path': file_path,
                'text_content': text_content,
                'processed_at': datetime.now().isoformat()
            }
            
            return document_data
            
        except Exception as e:
            logger.error(f"Error downloading and processing document {document_url}: {str(e)}")
            return None