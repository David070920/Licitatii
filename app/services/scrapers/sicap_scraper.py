"""
SICAP (Sistema Informatic de Contracte pentru Achizitii Publice) scraper
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse, parse_qs
import json

from app.services.scrapers.base import BaseScraper, PaginatedScraper
from app.services.scrapers.utils import HTMLParser, TextCleaner, DataValidator
from app.core.logging import logger


class SICAPScraper(PaginatedScraper):
    """SICAP scraper for Romanian public procurement data"""
    
    def __init__(self):
        super().__init__(
            source_name="SICAP",
            base_url="https://sicap.e-licitatie.ro",
            rate_limit=30,  # 30 requests per minute
            timeout=45,
            retry_attempts=3
        )
        
        # SICAP specific URLs
        self.search_url = f"{self.base_url}/pub/notices/search"
        self.tender_detail_url = f"{self.base_url}/pub/notices/view"
        self.documents_url = f"{self.base_url}/pub/notices/documents"
        
        # Search parameters
        self.search_params = {
            'noticeType': 'CONTRACT',
            'sortBy': 'PUBLICATION_DATE',
            'sortOrder': 'DESC',
            'pageSize': 50
        }
    
    async def scrape_tender_list(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page_limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Scrape tender list from SICAP with date filtering"""
        
        logger.info(f"Starting SICAP tender list scraping from {date_from} to {date_to}")
        
        # Prepare search parameters
        params = self.search_params.copy()
        
        if date_from:
            params['publicationDateFrom'] = date_from.strftime('%Y-%m-%d')
        
        if date_to:
            params['publicationDateTo'] = date_to.strftime('%Y-%m-%d')
        
        # Scrape paginated data
        tenders = await self.scrape_paginated_data(
            base_url=self.search_url,
            params=params,
            page_param='page',
            start_page=1,
            max_pages=page_limit
        )
        
        logger.info(f"Scraped {len(tenders)} tenders from SICAP")
        return tenders
    
    async def get_page_data(self, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get tender data from a single search results page"""
        
        try:
            response = await self.make_request(url, params=params)
            content = await response.text()
            
            # Parse the HTML content
            soup = HTMLParser.parse_html(content)
            
            # Extract tender data from search results
            tenders = []
            tender_rows = soup.find_all('tr', class_='tender-row')
            
            for row in tender_rows:
                try:
                    tender_data = self._extract_tender_from_row(row)
                    if tender_data:
                        tenders.append(tender_data)
                except Exception as e:
                    logger.warning(f"Error extracting tender from row: {str(e)}")
                    continue
            
            return tenders
            
        except Exception as e:
            logger.error(f"Error getting page data from {url}: {str(e)}")
            return []
    
    def _extract_tender_from_row(self, row) -> Optional[Dict[str, Any]]:
        """Extract tender data from a table row"""
        
        try:
            # Extract tender ID from link
            link = row.find('a', href=True)
            if not link:
                return None
            
            tender_id = self._extract_tender_id(link['href'])
            if not tender_id:
                return None
            
            # Extract basic information
            columns = row.find_all('td')
            if len(columns) < 6:
                return None
            
            tender_data = {
                'source_system': 'SICAP',
                'external_id': tender_id,
                'title': HTMLParser.extract_text(columns[1]),
                'contracting_authority': HTMLParser.extract_text(columns[2]),
                'estimated_value': TextCleaner.extract_currency_amount(HTMLParser.extract_text(columns[3])),
                'currency': self._extract_currency(HTMLParser.extract_text(columns[3])),
                'publication_date': TextCleaner.extract_date(HTMLParser.extract_text(columns[4])),
                'submission_deadline': TextCleaner.extract_date(HTMLParser.extract_text(columns[5])),
                'status': self._determine_status(HTMLParser.extract_text(columns[6]) if len(columns) > 6 else ''),
                'tender_url': urljoin(self.base_url, link['href'])
            }
            
            # Validate required fields
            if not tender_data['title'] or not tender_data['contracting_authority']:
                return None
            
            return tender_data
            
        except Exception as e:
            logger.warning(f"Error extracting tender data from row: {str(e)}")
            return None
    
    def _extract_tender_id(self, href: str) -> Optional[str]:
        """Extract tender ID from URL"""
        try:
            # Parse URL to extract tender ID
            parsed = urlparse(href)
            query_params = parse_qs(parsed.query)
            
            if 'noticeId' in query_params:
                return query_params['noticeId'][0]
            
            # Try to extract from path
            match = re.search(r'/(\d+)/?$', parsed.path)
            if match:
                return match.group(1)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting tender ID from {href}: {str(e)}")
            return None
    
    def _extract_currency(self, value_text: str) -> str:
        """Extract currency from value text"""
        if not value_text:
            return "RON"
        
        value_text = value_text.upper()
        
        if 'EUR' in value_text:
            return "EUR"
        elif 'USD' in value_text:
            return "USD"
        else:
            return "RON"
    
    def _determine_status(self, status_text: str) -> str:
        """Determine tender status from text"""
        if not status_text:
            return "unknown"
        
        status_text = status_text.lower()
        
        if 'activ' in status_text or 'deschis' in status_text:
            return "active"
        elif 'inchis' in status_text or 'expirat' in status_text:
            return "closed"
        elif 'anulat' in status_text:
            return "cancelled"
        elif 'adjudecat' in status_text:
            return "awarded"
        else:
            return "unknown"
    
    async def has_next_page(self, page_data: List[Dict[str, Any]]) -> bool:
        """Check if there are more pages based on page data"""
        # If we got less than the page size, we're probably at the last page
        return len(page_data) >= self.search_params['pageSize']
    
    async def scrape_tender_details(self, tender_id: str) -> Dict[str, Any]:
        """Scrape detailed information for a specific tender"""
        
        logger.info(f"Scraping details for tender {tender_id}")
        
        try:
            # Construct detail URL
            detail_url = f"{self.tender_detail_url}?noticeId={tender_id}"
            
            # Get tender detail page
            response = await self.make_request(detail_url)
            content = await response.text()
            
            # Parse the HTML content
            soup = HTMLParser.parse_html(content)
            
            # Extract detailed information
            tender_details = await self._extract_tender_details(soup, tender_id)
            
            return tender_details
            
        except Exception as e:
            logger.error(f"Error scraping tender details for {tender_id}: {str(e)}")
            return {}
    
    async def _extract_tender_details(self, soup, tender_id: str) -> Dict[str, Any]:
        """Extract detailed tender information from detail page"""
        
        details = {
            'source_system': 'SICAP',
            'external_id': tender_id,
            'raw_data': {}
        }
        
        try:
            # Extract title
            title_element = soup.find('h1', class_='tender-title')
            if title_element:
                details['title'] = HTMLParser.extract_text(title_element)
            
            # Extract description
            description_element = soup.find('div', class_='tender-description')
            if description_element:
                details['description'] = HTMLParser.extract_text(description_element)
            
            # Extract contracting authority information
            authority_section = soup.find('div', class_='contracting-authority')
            if authority_section:
                details['contracting_authority_details'] = self._extract_authority_details(authority_section)
            
            # Extract tender specification
            spec_section = soup.find('div', class_='tender-specification')
            if spec_section:
                details['specification'] = self._extract_specification(spec_section)
            
            # Extract important dates
            dates_section = soup.find('div', class_='tender-dates')
            if dates_section:
                details.update(self._extract_dates(dates_section))
            
            # Extract financial information
            financial_section = soup.find('div', class_='tender-financial')
            if financial_section:
                details.update(self._extract_financial_info(financial_section))
            
            # Extract CPV codes
            cpv_section = soup.find('div', class_='cpv-codes')
            if cpv_section:
                details['cpv_codes'] = self._extract_cpv_codes(cpv_section)
            
            # Extract procedure information
            procedure_section = soup.find('div', class_='procedure-info')
            if procedure_section:
                details.update(self._extract_procedure_info(procedure_section))
            
            # Store raw HTML for debugging
            details['raw_data']['html_content'] = str(soup)
            
            return details
            
        except Exception as e:
            logger.error(f"Error extracting tender details: {str(e)}")
            return details
    
    def _extract_authority_details(self, authority_section) -> Dict[str, Any]:
        """Extract contracting authority details"""
        details = {}
        
        try:
            # Extract authority name
            name_element = authority_section.find('div', class_='authority-name')
            if name_element:
                details['name'] = HTMLParser.extract_text(name_element)
            
            # Extract CUI
            cui_element = authority_section.find('div', class_='authority-cui')
            if cui_element:
                details['cui'] = HTMLParser.extract_text(cui_element)
            
            # Extract address
            address_element = authority_section.find('div', class_='authority-address')
            if address_element:
                details['address'] = HTMLParser.extract_text(address_element)
            
            # Extract contact information
            contact_element = authority_section.find('div', class_='authority-contact')
            if contact_element:
                details['contact'] = HTMLParser.extract_text(contact_element)
            
        except Exception as e:
            logger.warning(f"Error extracting authority details: {str(e)}")
        
        return details
    
    def _extract_specification(self, spec_section) -> Dict[str, Any]:
        """Extract tender specification"""
        spec = {}
        
        try:
            # Extract specification details from tables or divs
            tables = spec_section.find_all('table')
            for table in tables:
                table_data = HTMLParser.extract_table_data(table)
                if table_data:
                    spec['table_data'] = table_data
            
            # Extract specification text
            spec_text = HTMLParser.extract_text(spec_section)
            if spec_text:
                spec['description'] = spec_text
            
        except Exception as e:
            logger.warning(f"Error extracting specification: {str(e)}")
        
        return spec
    
    def _extract_dates(self, dates_section) -> Dict[str, Any]:
        """Extract important dates"""
        dates = {}
        
        try:
            # Look for date fields
            date_fields = {
                'publication_date': ['publicare', 'publication'],
                'submission_deadline': ['depunere', 'submission', 'deadline'],
                'opening_date': ['deschidere', 'opening'],
                'contract_start_date': ['inceput', 'start'],
                'contract_end_date': ['sfarsit', 'end']
            }
            
            for field, keywords in date_fields.items():
                for keyword in keywords:
                    date_element = dates_section.find(text=re.compile(keyword, re.I))
                    if date_element:
                        parent = date_element.parent
                        if parent:
                            date_text = HTMLParser.extract_text(parent.next_sibling or parent)
                            date_value = TextCleaner.extract_date(date_text)
                            if date_value:
                                dates[field] = date_value
                                break
            
        except Exception as e:
            logger.warning(f"Error extracting dates: {str(e)}")
        
        return dates
    
    def _extract_financial_info(self, financial_section) -> Dict[str, Any]:
        """Extract financial information"""
        financial = {}
        
        try:
            # Extract estimated value
            value_element = financial_section.find(text=re.compile('valoare', re.I))
            if value_element:
                parent = value_element.parent
                if parent:
                    value_text = HTMLParser.extract_text(parent.next_sibling or parent)
                    financial['estimated_value'] = TextCleaner.extract_currency_amount(value_text)
                    financial['currency'] = self._extract_currency(value_text)
            
            # Extract budget information
            budget_element = financial_section.find(text=re.compile('buget', re.I))
            if budget_element:
                parent = budget_element.parent
                if parent:
                    budget_text = HTMLParser.extract_text(parent.next_sibling or parent)
                    financial['budget'] = TextCleaner.extract_currency_amount(budget_text)
            
        except Exception as e:
            logger.warning(f"Error extracting financial info: {str(e)}")
        
        return financial
    
    def _extract_cpv_codes(self, cpv_section) -> List[str]:
        """Extract CPV codes"""
        cpv_codes = []
        
        try:
            # Look for CPV code patterns
            cpv_pattern = r'\b\d{8}(?:-\d)?\b'
            
            text = HTMLParser.extract_text(cpv_section)
            matches = re.findall(cpv_pattern, text)
            
            cpv_codes.extend(matches)
            
        except Exception as e:
            logger.warning(f"Error extracting CPV codes: {str(e)}")
        
        return cpv_codes
    
    def _extract_procedure_info(self, procedure_section) -> Dict[str, Any]:
        """Extract procedure information"""
        procedure = {}
        
        try:
            # Extract procedure type
            type_element = procedure_section.find(text=re.compile('procedura', re.I))
            if type_element:
                parent = type_element.parent
                if parent:
                    procedure['procedure_type'] = HTMLParser.extract_text(parent.next_sibling or parent)
            
            # Extract tender type
            tender_type_element = procedure_section.find(text=re.compile('tip', re.I))
            if tender_type_element:
                parent = tender_type_element.parent
                if parent:
                    procedure['tender_type'] = HTMLParser.extract_text(parent.next_sibling or parent)
            
        except Exception as e:
            logger.warning(f"Error extracting procedure info: {str(e)}")
        
        return procedure
    
    async def scrape_tender_documents(self, tender_id: str) -> List[Dict[str, Any]]:
        """Scrape documents for a specific tender"""
        
        logger.info(f"Scraping documents for tender {tender_id}")
        
        try:
            # Construct documents URL
            documents_url = f"{self.documents_url}?noticeId={tender_id}"
            
            # Get documents page
            response = await self.make_request(documents_url)
            content = await response.text()
            
            # Parse the HTML content
            soup = HTMLParser.parse_html(content)
            
            # Extract document links
            documents = []
            document_links = soup.find_all('a', href=re.compile(r'download|document'))
            
            for link in document_links:
                try:
                    document_data = {
                        'title': HTMLParser.extract_text(link),
                        'url': urljoin(self.base_url, link['href']),
                        'type': self._determine_document_type(link['href'])
                    }
                    
                    # Extract file size if available
                    size_element = link.find_next('span', class_='file-size')
                    if size_element:
                        document_data['size'] = HTMLParser.extract_text(size_element)
                    
                    documents.append(document_data)
                    
                except Exception as e:
                    logger.warning(f"Error extracting document info: {str(e)}")
                    continue
            
            logger.info(f"Found {len(documents)} documents for tender {tender_id}")
            return documents
            
        except Exception as e:
            logger.error(f"Error scraping documents for {tender_id}: {str(e)}")
            return []
    
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
    
    async def scrape_recent_tenders(self, days: int = 7) -> List[Dict[str, Any]]:
        """Scrape recent tenders from the last N days"""
        
        date_to = datetime.now()
        date_from = date_to - timedelta(days=days)
        
        return await self.scrape_tender_list(date_from, date_to)
    
    async def scrape_tender_by_id(self, tender_id: str) -> Dict[str, Any]:
        """Scrape complete tender information by ID"""
        
        logger.info(f"Scraping complete tender data for {tender_id}")
        
        # Get basic details
        tender_data = await self.scrape_tender_details(tender_id)
        
        # Get documents
        documents = await self.scrape_tender_documents(tender_id)
        tender_data['documents'] = documents
        
        return tender_data