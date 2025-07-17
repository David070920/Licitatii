"""
Tests for data processor and ingestion pipeline
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal

from app.services.ingestion.data_processor import DataProcessor
from app.services.ingestion.data_validator import DataTransformationPipeline, ValidationResult
from app.services.ingestion.data_enricher import DataEnricher
from app.services.ingestion.duplicate_detector import DuplicateDetector
from app.db.models import Tender, Company, ContractingAuthority


class TestDataProcessor:
    """Test suite for DataProcessor"""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance for testing"""
        return DataProcessor()
    
    @pytest.fixture
    def sample_raw_tenders(self):
        """Sample raw tender data for testing"""
        return [
            {
                'source_system': 'SICAP',
                'external_id': '12345',
                'title': 'Achizitie servicii de consultanta IT',
                'contracting_authority': 'Primaria Bucuresti',
                'estimated_value': 100000.0,
                'currency': 'RON',
                'publication_date': datetime.now(),
                'submission_deadline': datetime.now() + timedelta(days=15),
                'status': 'active'
            },
            {
                'source_system': 'SICAP',
                'external_id': '67890',
                'title': 'Achizitie echipamente IT',
                'contracting_authority': 'Ministerul Sanatatii',
                'estimated_value': 250000.0,
                'currency': 'RON',
                'publication_date': datetime.now() - timedelta(days=1),
                'submission_deadline': datetime.now() + timedelta(days=10),
                'status': 'active'
            }
        ]
    
    @pytest.fixture
    def sample_validation_results(self):
        """Sample validation results for testing"""
        return [
            ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                cleaned_data={
                    'source_system': 'SICAP',
                    'external_id': '12345',
                    'title': 'Achizitie servicii de consultanta IT',
                    'contracting_authority': 'Primaria Bucuresti',
                    'estimated_value': 100000.0,
                    'currency': 'RON',
                    'status': 'active'
                }
            ),
            ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                cleaned_data={
                    'source_system': 'SICAP',
                    'external_id': '67890',
                    'title': 'Achizitie echipamente IT',
                    'contracting_authority': 'Ministerul Sanatatii',
                    'estimated_value': 250000.0,
                    'currency': 'RON',
                    'status': 'active'
                }
            )
        ]
    
    def test_processor_initialization(self, processor):
        """Test processor initialization"""
        assert isinstance(processor.transformer, DataTransformationPipeline)
        assert isinstance(processor.enricher, DataEnricher)
        assert isinstance(processor.duplicate_detector, DuplicateDetector)
        assert processor.stats['processed'] == 0
        assert processor.stats['created'] == 0
        assert processor.stats['updated'] == 0
        assert processor.stats['failed'] == 0
    
    @pytest.mark.asyncio
    @patch('app.services.ingestion.data_processor.get_async_session')
    async def test_process_tender_batch(self, mock_session, processor, sample_raw_tenders):
        """Test tender batch processing"""
        # Mock session and database operations
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock transformer
        with patch.object(processor.transformer, 'transform_batch') as mock_transform:
            mock_transform.return_value = [
                ValidationResult(
                    is_valid=True,
                    errors=[],
                    warnings=[],
                    cleaned_data=tender
                ) for tender in sample_raw_tenders
            ]
            
            # Mock enricher
            with patch.object(processor.enricher, 'enrich_tender_batch') as mock_enrich:
                mock_enrich.return_value = sample_raw_tenders
                
                # Mock duplicate detector
                with patch.object(processor, '_process_tender_duplicates') as mock_duplicates:
                    mock_duplicates.return_value = [
                        {**tender, '_operation': 'create'} for tender in sample_raw_tenders
                    ]
                    
                    # Mock database storage
                    with patch.object(processor, '_store_tenders_in_database') as mock_store:
                        mock_store.return_value = None
                        
                        result = await processor.process_tender_batch(
                            sample_raw_tenders,
                            source_system='SICAP',
                            job_id='test-job-123'
                        )
                        
                        assert result['processed'] == 2
                        assert result['start_time'] is not None
                        assert result['end_time'] is not None
                        
                        mock_transform.assert_called_once()
                        mock_enrich.assert_called_once()
                        mock_duplicates.assert_called_once()
                        mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_tender_duplicates(self, processor):
        """Test tender duplicate processing"""
        sample_tenders = [
            {
                'source_system': 'SICAP',
                'external_id': '12345',
                'title': 'Test Tender',
                'contracting_authority': 'Test Authority'
            }
        ]
        
        # Mock duplicate detector
        with patch.object(processor.duplicate_detector, 'find_duplicate_tender') as mock_find:
            mock_find.return_value = None  # No duplicates found
            
            result = await processor._process_tender_duplicates(sample_tenders)
            
            assert len(result) == 1
            assert result[0]['_operation'] == 'create'
            assert processor.stats['processed'] == 1
            assert processor.stats['duplicates'] == 0
    
    @pytest.mark.asyncio
    async def test_process_tender_duplicates_with_merge(self, processor):
        """Test tender duplicate processing with merge"""
        sample_tenders = [
            {
                'source_system': 'SICAP',
                'external_id': '12345',
                'title': 'Test Tender',
                'contracting_authority': 'Test Authority'
            }
        ]
        
        # Mock existing tender
        existing_tender = Mock()
        existing_tender.id = 'existing-id'
        
        # Mock duplicate detector
        with patch.object(processor.duplicate_detector, 'find_duplicate_tender') as mock_find:
            mock_find.return_value = existing_tender
            
            with patch.object(processor.duplicate_detector, 'merge_tender_data') as mock_merge:
                mock_merge.return_value = {
                    **sample_tenders[0],
                    'merged_field': 'merged_value'
                }
                
                result = await processor._process_tender_duplicates(sample_tenders)
                
                assert len(result) == 1
                assert result[0]['_operation'] == 'update'
                assert result[0]['_existing_id'] == 'existing-id'
                assert processor.stats['duplicates'] == 1
    
    @pytest.mark.asyncio
    @patch('app.services.ingestion.data_processor.get_async_session')
    async def test_create_tender(self, mock_session, processor):
        """Test tender creation"""
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        tender_data = {
            'source_system': 'SICAP',
            'external_id': '12345',
            'title': 'Test Tender',
            'contracting_authority': 'Test Authority',
            'estimated_value': 100000.0,
            'currency': 'RON',
            'status': 'active'
        }
        
        # Mock authority creation
        with patch.object(processor, '_get_or_create_contracting_authority') as mock_auth:
            mock_authority = Mock()
            mock_authority.id = 'auth-id'
            mock_auth.return_value = mock_authority
            
            # Mock CPV code creation
            with patch.object(processor, '_get_or_create_cpv_code') as mock_cpv:
                mock_cpv.return_value = '72000000'
                
                await processor._create_tender(mock_session_instance, tender_data)
                
                # Verify tender was added to session
                mock_session_instance.add.assert_called_once()
                
                # Verify the tender object was created with correct data
                added_tender = mock_session_instance.add.call_args[0][0]
                assert added_tender.source_system == 'SICAP'
                assert added_tender.external_id == '12345'
                assert added_tender.title == 'Test Tender'
    
    @pytest.mark.asyncio
    @patch('app.services.ingestion.data_processor.get_async_session')
    async def test_update_tender(self, mock_session, processor):
        """Test tender update"""
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock existing tender
        existing_tender = Mock()
        existing_tender.id = 'existing-id'
        existing_tender.external_id = '12345'
        existing_tender.processed_data = {}
        
        mock_session_instance.scalar.return_value = existing_tender
        
        tender_data = {
            '_existing_id': 'existing-id',
            'title': 'Updated Title',
            'estimated_value': 150000.0,
            'processed_data': {'updated_field': 'updated_value'}
        }
        
        await processor._update_tender(mock_session_instance, tender_data)
        
        # Verify tender was updated
        assert existing_tender.title == 'Updated Title'
        assert existing_tender.estimated_value == 150000.0
        assert existing_tender.processed_data['updated_field'] == 'updated_value'
    
    @pytest.mark.asyncio
    @patch('app.services.ingestion.data_processor.get_async_session')
    async def test_get_or_create_contracting_authority_existing(self, mock_session, processor):
        """Test getting existing contracting authority"""
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock existing authority
        existing_authority = Mock()
        existing_authority.name = 'Test Authority'
        mock_session_instance.scalar.return_value = existing_authority
        
        tender_data = {
            'contracting_authority': 'Test Authority'
        }
        
        result = await processor._get_or_create_contracting_authority(
            mock_session_instance, tender_data
        )
        
        assert result == existing_authority
        mock_session_instance.add.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('app.services.ingestion.data_processor.get_async_session')
    async def test_get_or_create_contracting_authority_new(self, mock_session, processor):
        """Test creating new contracting authority"""
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        # Mock no existing authority
        mock_session_instance.scalar.return_value = None
        
        tender_data = {
            'contracting_authority': 'New Authority',
            'contracting_authority_details': {
                'cui': 'RO12345678',
                'address': 'Test Address',
                'contact_email': 'test@example.com'
            }
        }
        
        result = await processor._get_or_create_contracting_authority(
            mock_session_instance, tender_data
        )
        
        assert result is not None
        mock_session_instance.add.assert_called_once()
        mock_session_instance.flush.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.ingestion.data_processor.get_async_session')
    async def test_process_company_batch(self, mock_session, processor):
        """Test company batch processing"""
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        
        raw_companies = [
            {
                'name': 'Test Company',
                'cui': '12345678',
                'address': 'Test Address'
            }
        ]
        
        # Mock transformer
        with patch.object(processor.transformer, 'transform_batch') as mock_transform:
            mock_transform.return_value = [
                ValidationResult(
                    is_valid=True,
                    errors=[],
                    warnings=[],
                    cleaned_data=raw_companies[0]
                )
            ]
            
            # Mock enricher
            with patch.object(processor.enricher, 'enrich_company_batch') as mock_enrich:
                mock_enrich.return_value = raw_companies
                
                # Mock duplicate detector
                with patch.object(processor.duplicate_detector, 'find_duplicate_company') as mock_find:
                    mock_find.return_value = None
                    
                    # Mock company creation
                    with patch.object(processor, '_create_company') as mock_create:
                        result = await processor.process_company_batch(
                            raw_companies,
                            source_system='SICAP',
                            job_id='test-job-123'
                        )
                        
                        assert result['processed'] == 1
                        assert result['created'] == 1
                        assert result['updated'] == 0
                        assert result['failed'] == 0
                        
                        mock_transform.assert_called_once()
                        mock_enrich.assert_called_once()
                        mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_company(self, processor):
        """Test company creation"""
        mock_session = AsyncMock()
        
        company_data = {
            'name': 'Test Company',
            'cui': '12345678',
            'address': 'Test Address',
            'contact_email': 'test@example.com'
        }
        
        await processor._create_company(mock_session, company_data)
        
        # Verify company was added to session
        mock_session.add.assert_called_once()
        
        # Verify the company object was created with correct data
        added_company = mock_session.add.call_args[0][0]
        assert added_company.name == 'Test Company'
        assert added_company.cui == '12345678'
        assert added_company.address == 'Test Address'
        assert added_company.contact_email == 'test@example.com'
    
    @pytest.mark.asyncio
    async def test_update_company(self, processor):
        """Test company update"""
        mock_session = AsyncMock()
        
        existing_company = Mock()
        existing_company.name = 'Old Name'
        existing_company.address = 'Old Address'
        
        company_data = {
            'name': 'Updated Company',
            'address': 'Updated Address',
            'contact_email': 'updated@example.com'
        }
        
        await processor._update_company(mock_session, existing_company, company_data)
        
        # Verify company was updated
        assert existing_company.name == 'Updated Company'
        assert existing_company.address == 'Updated Address'
        assert existing_company.contact_email == 'updated@example.com'
    
    def test_reset_stats(self, processor):
        """Test statistics reset"""
        # Set some stats
        processor.stats['processed'] = 10
        processor.stats['created'] = 5
        processor.stats['updated'] = 3
        processor.stats['failed'] = 2
        
        # Reset stats
        processor.reset_stats()
        
        # Verify stats were reset
        assert processor.stats['processed'] == 0
        assert processor.stats['created'] == 0
        assert processor.stats['updated'] == 0
        assert processor.stats['failed'] == 0
        assert processor.stats['duplicates'] == 0
    
    @pytest.mark.asyncio
    async def test_error_handling_in_batch_processing(self, processor):
        """Test error handling in batch processing"""
        sample_tenders = [
            {
                'source_system': 'SICAP',
                'external_id': '12345',
                'title': 'Test Tender'
            }
        ]
        
        # Mock transformer to raise exception
        with patch.object(processor.transformer, 'transform_batch') as mock_transform:
            mock_transform.side_effect = Exception("Transformation error")
            
            with pytest.raises(Exception, match="Transformation error"):
                await processor.process_tender_batch(
                    sample_tenders,
                    source_system='SICAP',
                    job_id='test-job-123'
                )


class TestDataProcessorIntegration:
    """Integration tests for DataProcessor"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_processing_pipeline(self):
        """Test complete data processing pipeline"""
        # This would test the full pipeline with real database
        # Skip for unit tests
        pytest.skip("Integration test - requires database connection")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_processing(self):
        """Test concurrent processing of multiple batches"""
        # This would test concurrent processing
        # Skip for unit tests
        pytest.skip("Integration test - requires database connection")


# Performance tests
class TestDataProcessorPerformance:
    """Performance tests for DataProcessor"""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_large_batch_processing(self):
        """Test processing of large batches"""
        # This would test performance with large datasets
        # Skip for unit tests
        pytest.skip("Performance test - requires large dataset")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_memory_usage(self):
        """Test memory usage during processing"""
        # This would test memory usage
        # Skip for unit tests
        pytest.skip("Performance test - requires memory profiling")


# Error scenarios
class TestDataProcessorErrorScenarios:
    """Test error scenarios in DataProcessor"""
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self):
        """Test handling of database connection errors"""
        processor = DataProcessor()
        
        with patch('app.services.ingestion.data_processor.get_async_session') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            with pytest.raises(Exception, match="Database connection failed"):
                await processor.process_tender_batch(
                    [{'external_id': '12345'}],
                    source_system='SICAP'
                )
    
    @pytest.mark.asyncio
    async def test_validation_failure(self):
        """Test handling of validation failures"""
        processor = DataProcessor()
        
        invalid_tenders = [
            {
                'source_system': 'SICAP',
                'external_id': '',  # Invalid: empty external_id
                'title': '',  # Invalid: empty title
            }
        ]
        
        # Mock transformer to return validation errors
        with patch.object(processor.transformer, 'transform_batch') as mock_transform:
            mock_transform.return_value = [
                ValidationResult(
                    is_valid=False,
                    errors=['Missing required field: external_id', 'Missing required field: title'],
                    warnings=[],
                    cleaned_data={}
                )
            ]
            
            with patch.object(processor.enricher, 'enrich_tender_batch') as mock_enrich:
                mock_enrich.return_value = []  # No valid tenders to enrich
                
                with patch.object(processor, '_process_tender_duplicates') as mock_duplicates:
                    mock_duplicates.return_value = []
                    
                    with patch.object(processor, '_store_tenders_in_database') as mock_store:
                        with patch('app.services.ingestion.data_processor.get_async_session'):
                            result = await processor.process_tender_batch(
                                invalid_tenders,
                                source_system='SICAP',
                                job_id='test-job-123'
                            )
                            
                            assert result['processed'] == 0
                            assert result['created'] == 0
                            assert result['failed'] == 0  # No processing attempted for invalid data
    
    @pytest.mark.asyncio
    async def test_enrichment_failure(self):
        """Test handling of enrichment failures"""
        processor = DataProcessor()
        
        sample_tenders = [
            {
                'source_system': 'SICAP',
                'external_id': '12345',
                'title': 'Test Tender'
            }
        ]
        
        # Mock transformer to return valid data
        with patch.object(processor.transformer, 'transform_batch') as mock_transform:
            mock_transform.return_value = [
                ValidationResult(
                    is_valid=True,
                    errors=[],
                    warnings=[],
                    cleaned_data=sample_tenders[0]
                )
            ]
            
            # Mock enricher to fail
            with patch.object(processor.enricher, 'enrich_tender_batch') as mock_enrich:
                mock_enrich.side_effect = Exception("Enrichment failed")
                
                with pytest.raises(Exception, match="Enrichment failed"):
                    await processor.process_tender_batch(
                        sample_tenders,
                        source_system='SICAP',
                        job_id='test-job-123'
                    )