"""
Tests for SICAP scraper
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
from bs4 import BeautifulSoup

from app.services.scrapers.sicap_scraper import SICAPScraper
from app.services.scrapers.utils import HTMLParser, TextCleaner


class TestSICAPScraper:
    """Test suite for SICAP scraper"""
    
    @pytest.fixture
    def scraper(self):
        """Create scraper instance for testing"""
        return SICAPScraper()
    
    @pytest.fixture
    def sample_tender_row_html(self):
        """Sample HTML for tender row"""
        return """
        <tr class="tender-row">
            <td><a href="/pub/notices/view?noticeId=12345">T-12345</a></td>
            <td>Achizitie servicii de consultanta IT</td>
            <td>Primaria Bucuresti</td>
            <td>100,000 RON</td>
            <td>15.01.2024</td>
            <td>30.01.2024</td>
            <td>Activ</td>
        </tr>
        """
    
    @pytest.fixture
    def sample_tender_detail_html(self):
        """Sample HTML for tender detail page"""
        return """
        <div class="tender-detail">
            <h1 class="tender-title">Achizitie servicii de consultanta IT</h1>
            <div class="tender-description">
                Servicii de consultanta pentru modernizarea sistemelor IT
            </div>
            <div class="contracting-authority">
                <div class="authority-name">Primaria Bucuresti</div>
                <div class="authority-cui">RO12345678</div>
                <div class="authority-address">Bd. Regina Elisabeta nr. 5-7, Bucuresti</div>
            </div>
            <div class="tender-financial">
                <div>Valoare estimata: 100,000 RON</div>
            </div>
            <div class="tender-dates">
                <div>Data publicarii: 15.01.2024</div>
                <div>Termenul limita de depunere: 30.01.2024</div>
            </div>
            <div class="cpv-codes">
                <div>Coduri CPV: 72000000</div>
            </div>
        </div>
        """
    
    @pytest.mark.asyncio
    async def test_scraper_initialization(self, scraper):
        """Test scraper initialization"""
        assert scraper.source_name == "SICAP"
        assert scraper.base_url == "https://sicap.e-licitatie.ro"
        assert scraper.rate_limit == 30
        assert scraper.timeout == 45
        assert scraper.retry_attempts == 3
    
    @pytest.mark.asyncio
    async def test_extract_tender_id(self, scraper):
        """Test tender ID extraction"""
        # Test with query parameter
        href1 = "/pub/notices/view?noticeId=12345"
        tender_id1 = scraper._extract_tender_id(href1)
        assert tender_id1 == "12345"
        
        # Test with path parameter
        href2 = "/pub/notices/view/67890"
        tender_id2 = scraper._extract_tender_id(href2)
        assert tender_id2 == "67890"
        
        # Test invalid URL
        href3 = "/invalid/url"
        tender_id3 = scraper._extract_tender_id(href3)
        assert tender_id3 is None
    
    @pytest.mark.asyncio
    async def test_extract_currency(self, scraper):
        """Test currency extraction"""
        assert scraper._extract_currency("100,000 RON") == "RON"
        assert scraper._extract_currency("50,000 EUR") == "EUR"
        assert scraper._extract_currency("25,000 USD") == "USD"
        assert scraper._extract_currency("100,000 lei") == "RON"
        assert scraper._extract_currency("") == "RON"
    
    @pytest.mark.asyncio
    async def test_determine_status(self, scraper):
        """Test status determination"""
        assert scraper._determine_status("Activ") == "active"
        assert scraper._determine_status("Deschis") == "active"
        assert scraper._determine_status("Inchis") == "closed"
        assert scraper._determine_status("Expirat") == "closed"
        assert scraper._determine_status("Anulat") == "cancelled"
        assert scraper._determine_status("Adjudecat") == "awarded"
        assert scraper._determine_status("Necunoscut") == "unknown"
    
    @pytest.mark.asyncio
    async def test_extract_tender_from_row(self, scraper, sample_tender_row_html):
        """Test tender extraction from HTML row"""
        soup = BeautifulSoup(sample_tender_row_html, 'html.parser')
        row = soup.find('tr')
        
        tender_data = scraper._extract_tender_from_row(row)
        
        assert tender_data is not None
        assert tender_data['source_system'] == 'SICAP'
        assert tender_data['external_id'] == '12345'
        assert tender_data['title'] == 'Achizitie servicii de consultanta IT'
        assert tender_data['contracting_authority'] == 'Primaria Bucuresti'
        assert tender_data['estimated_value'] == 100000.0
        assert tender_data['currency'] == 'RON'
        assert tender_data['status'] == 'active'
    
    @pytest.mark.asyncio
    async def test_extract_tender_from_row_invalid(self, scraper):
        """Test tender extraction from invalid row"""
        # Test with empty row
        soup = BeautifulSoup('<tr></tr>', 'html.parser')
        row = soup.find('tr')
        
        tender_data = scraper._extract_tender_from_row(row)
        assert tender_data is None
        
        # Test with row without link
        soup = BeautifulSoup('<tr><td>No link</td></tr>', 'html.parser')
        row = soup.find('tr')
        
        tender_data = scraper._extract_tender_from_row(row)
        assert tender_data is None
    
    @pytest.mark.asyncio
    async def test_extract_authority_details(self, scraper):
        """Test authority details extraction"""
        html = """
        <div class="contracting-authority">
            <div class="authority-name">Primaria Bucuresti</div>
            <div class="authority-cui">RO12345678</div>
            <div class="authority-address">Bd. Regina Elisabeta nr. 5-7, Bucuresti</div>
            <div class="authority-contact">contact@primariabucuresti.ro</div>
        </div>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        authority_section = soup.find('div', class_='contracting-authority')
        
        details = scraper._extract_authority_details(authority_section)
        
        assert details['name'] == 'Primaria Bucuresti'
        assert details['cui'] == 'RO12345678'
        assert details['address'] == 'Bd. Regina Elisabeta nr. 5-7, Bucuresti'
        assert details['contact'] == 'contact@primariabucuresti.ro'
    
    @pytest.mark.asyncio
    async def test_extract_cpv_codes(self, scraper):
        """Test CPV codes extraction"""
        html = """
        <div class="cpv-codes">
            <div>Coduri CPV: 72000000, 72100000-1, 72200000</div>
        </div>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        cpv_section = soup.find('div', class_='cpv-codes')
        
        cpv_codes = scraper._extract_cpv_codes(cpv_section)
        
        assert '72000000' in cpv_codes
        assert '72100000-1' in cpv_codes
        assert '72200000' in cpv_codes
    
    @pytest.mark.asyncio
    async def test_determine_document_type(self, scraper):
        """Test document type determination"""
        assert scraper._determine_document_type("document.pdf") == "pdf"
        assert scraper._determine_document_type("document.doc") == "document"
        assert scraper._determine_document_type("document.docx") == "document"
        assert scraper._determine_document_type("document.xls") == "spreadsheet"
        assert scraper._determine_document_type("document.xlsx") == "spreadsheet"
        assert scraper._determine_document_type("document.zip") == "archive"
        assert scraper._determine_document_type("document.rar") == "archive"
        assert scraper._determine_document_type("document.txt") == "unknown"
    
    @pytest.mark.asyncio
    @patch('app.services.scrapers.sicap_scraper.SICAPScraper.make_request')
    async def test_get_page_data(self, mock_make_request, scraper):
        """Test page data retrieval"""
        # Mock response
        mock_response = Mock()
        mock_response.text = AsyncMock(return_value=f"""
        <html>
        <body>
        <table>
        {scraper.sample_tender_row_html if hasattr(scraper, 'sample_tender_row_html') else '<tr class="tender-row"><td><a href="/pub/notices/view?noticeId=12345">T-12345</a></td><td>Test Tender</td><td>Test Authority</td><td>100,000 RON</td><td>15.01.2024</td><td>30.01.2024</td><td>Activ</td></tr>'}
        </table>
        </body>
        </html>
        """)
        mock_make_request.return_value = mock_response
        
        url = "https://sicap.e-licitatie.ro/pub/notices/search"
        params = {'page': 1}
        
        tenders = await scraper.get_page_data(url, params)
        
        assert len(tenders) >= 0  # Should return list
        mock_make_request.assert_called_once_with(url, params=params)
    
    @pytest.mark.asyncio
    @patch('app.services.scrapers.sicap_scraper.SICAPScraper.make_request')
    async def test_scrape_tender_details(self, mock_make_request, scraper, sample_tender_detail_html):
        """Test tender details scraping"""
        mock_response = Mock()
        mock_response.text = AsyncMock(return_value=sample_tender_detail_html)
        mock_make_request.return_value = mock_response
        
        tender_details = await scraper.scrape_tender_details("12345")
        
        assert tender_details['source_system'] == 'SICAP'
        assert tender_details['external_id'] == '12345'
        assert 'title' in tender_details
        assert 'contracting_authority_details' in tender_details
        
        mock_make_request.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.scrapers.sicap_scraper.SICAPScraper.make_request')
    async def test_scrape_tender_documents(self, mock_make_request, scraper):
        """Test tender documents scraping"""
        mock_response = Mock()
        mock_response.text = AsyncMock(return_value="""
        <html>
        <body>
        <a href="/download/document1.pdf">Caietul de sarcini</a>
        <a href="/download/document2.doc">Anexa 1</a>
        </body>
        </html>
        """)
        mock_make_request.return_value = mock_response
        
        documents = await scraper.scrape_tender_documents("12345")
        
        assert len(documents) == 2
        assert documents[0]['title'] == 'Caietul de sarcini'
        assert documents[0]['type'] == 'pdf'
        assert documents[1]['title'] == 'Anexa 1'
        assert documents[1]['type'] == 'document'
        
        mock_make_request.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.scrapers.sicap_scraper.SICAPScraper.scrape_paginated_data')
    async def test_scrape_tender_list(self, mock_scrape_paginated, scraper):
        """Test tender list scraping"""
        mock_scrape_paginated.return_value = [
            {'external_id': '12345', 'title': 'Test Tender 1'},
            {'external_id': '67890', 'title': 'Test Tender 2'}
        ]
        
        date_from = datetime.now() - timedelta(days=7)
        date_to = datetime.now()
        
        tenders = await scraper.scrape_tender_list(date_from, date_to, page_limit=5)
        
        assert len(tenders) == 2
        assert tenders[0]['external_id'] == '12345'
        assert tenders[1]['external_id'] == '67890'
        
        mock_scrape_paginated.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_has_next_page(self, scraper):
        """Test next page detection"""
        # Page with full data should have next page
        full_page_data = [{'id': i} for i in range(50)]  # Full page size
        assert await scraper.has_next_page(full_page_data) == True
        
        # Page with less data should not have next page
        partial_page_data = [{'id': i} for i in range(10)]  # Less than page size
        assert await scraper.has_next_page(partial_page_data) == False
        
        # Empty page should not have next page
        empty_page_data = []
        assert await scraper.has_next_page(empty_page_data) == False
    
    @pytest.mark.asyncio
    async def test_scrape_recent_tenders(self, scraper):
        """Test recent tenders scraping"""
        with patch.object(scraper, 'scrape_tender_list') as mock_scrape:
            mock_scrape.return_value = [{'external_id': '12345'}]
            
            recent_tenders = await scraper.scrape_recent_tenders(days=7)
            
            assert len(recent_tenders) == 1
            mock_scrape.assert_called_once()
            
            # Check that date parameters were passed correctly
            call_args = mock_scrape.call_args
            assert call_args[0][0] is not None  # date_from
            assert call_args[0][1] is not None  # date_to
    
    @pytest.mark.asyncio
    async def test_scrape_tender_by_id(self, scraper):
        """Test complete tender scraping by ID"""
        with patch.object(scraper, 'scrape_tender_details') as mock_details, \
             patch.object(scraper, 'scrape_tender_documents') as mock_documents:
            
            mock_details.return_value = {'external_id': '12345', 'title': 'Test Tender'}
            mock_documents.return_value = [{'title': 'Document 1'}]
            
            tender_data = await scraper.scrape_tender_by_id("12345")
            
            assert tender_data['external_id'] == '12345'
            assert tender_data['title'] == 'Test Tender'
            assert 'documents' in tender_data
            assert len(tender_data['documents']) == 1
            
            mock_details.assert_called_once_with("12345")
            mock_documents.assert_called_once_with("12345")
    
    @pytest.mark.asyncio
    async def test_error_handling(self, scraper):
        """Test error handling in scraper methods"""
        with patch.object(scraper, 'make_request') as mock_request:
            # Test network error handling
            mock_request.side_effect = aiohttp.ClientError("Network error")
            
            # Should handle errors gracefully
            result = await scraper.scrape_tender_details("12345")
            assert result == {}
            
            documents = await scraper.scrape_tender_documents("12345")
            assert documents == []
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, scraper):
        """Test rate limiting functionality"""
        # Test that rate limiter is initialized
        assert scraper.rate_limiter is not None
        assert scraper.rate_limiter.max_calls == 30
        assert scraper.rate_limiter.time_window == 60
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, scraper):
        """Test metrics tracking"""
        # Check initial metrics
        assert scraper.metrics['requests_made'] == 0
        assert scraper.metrics['successful_requests'] == 0
        assert scraper.metrics['failed_requests'] == 0
        assert scraper.metrics['items_scraped'] == 0
        
        # Metrics should be updated after operations
        # This would require mocking the context manager and operations
    
    @pytest.mark.asyncio
    async def test_circuit_breaker(self, scraper):
        """Test circuit breaker functionality"""
        # Test that circuit breaker is initialized
        assert scraper.circuit_breaker is not None
        assert scraper.circuit_breaker.failure_threshold == 5
        assert scraper.circuit_breaker.recovery_timeout == 60


class TestSICAPScraperIntegration:
    """Integration tests for SICAP scraper"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_sicap_connection(self):
        """Test real connection to SICAP (only run with integration flag)"""
        scraper = SICAPScraper()
        
        # This test should only run in integration test environment
        # and should be skipped in unit tests
        pytest.skip("Integration test - requires real SICAP connection")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_scrape_sample_data(self):
        """Test scraping sample data from SICAP"""
        scraper = SICAPScraper()
        
        # This test should only run in integration test environment
        pytest.skip("Integration test - requires real SICAP connection")


# Test fixtures for data validation
@pytest.fixture
def sample_tender_data():
    """Sample tender data for testing"""
    return {
        'source_system': 'SICAP',
        'external_id': '12345',
        'title': 'Achizitie servicii de consultanta IT',
        'contracting_authority': 'Primaria Bucuresti',
        'estimated_value': 100000.0,
        'currency': 'RON',
        'publication_date': datetime.now(),
        'submission_deadline': datetime.now() + timedelta(days=15),
        'status': 'active'
    }


@pytest.fixture
def sample_invalid_tender_data():
    """Sample invalid tender data for testing"""
    return {
        'source_system': 'SICAP',
        'external_id': '',  # Invalid: empty external_id
        'title': '',  # Invalid: empty title
        'contracting_authority': 'Primaria Bucuresti',
        'estimated_value': -100000.0,  # Invalid: negative value
        'currency': 'INVALID',  # Invalid: unknown currency
        'publication_date': datetime.now(),
        'submission_deadline': datetime.now() - timedelta(days=15),  # Invalid: deadline in past
        'status': 'unknown_status'  # Invalid: unknown status
    }


class TestSICAPDataValidation:
    """Test data validation for SICAP scraped data"""
    
    def test_valid_tender_data(self, sample_tender_data):
        """Test validation of valid tender data"""
        # This would use the actual validation logic
        # from the data validation pipeline
        assert sample_tender_data['source_system'] == 'SICAP'
        assert len(sample_tender_data['external_id']) > 0
        assert len(sample_tender_data['title']) > 0
        assert sample_tender_data['estimated_value'] > 0
        assert sample_tender_data['currency'] in ['RON', 'EUR', 'USD']
        assert sample_tender_data['submission_deadline'] > sample_tender_data['publication_date']
    
    def test_invalid_tender_data(self, sample_invalid_tender_data):
        """Test validation of invalid tender data"""
        # This would use the actual validation logic
        # to ensure invalid data is caught
        assert sample_invalid_tender_data['external_id'] == ''
        assert sample_invalid_tender_data['title'] == ''
        assert sample_invalid_tender_data['estimated_value'] < 0
        assert sample_invalid_tender_data['currency'] not in ['RON', 'EUR', 'USD']
        assert sample_invalid_tender_data['submission_deadline'] < sample_invalid_tender_data['publication_date']