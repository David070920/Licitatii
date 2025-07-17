"""
Data processing and ingestion pipeline for Romanian procurement data
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import json
import hashlib

from app.core.database import get_async_session
from app.core.logging import logger
from app.db.models import (
    Tender, Company, ContractingAuthority, TenderBid, TenderAward,
    DataIngestionLog, CPVCode
)
from app.services.ingestion.data_validator import DataTransformationPipeline, ValidationResult
from app.services.ingestion.data_enricher import DataEnricher
from app.services.ingestion.duplicate_detector import DuplicateDetector


class DataProcessor:
    """Main data processing pipeline"""
    
    def __init__(self):
        self.transformer = DataTransformationPipeline()
        self.enricher = DataEnricher()
        self.duplicate_detector = DuplicateDetector()
        
        # Processing statistics
        self.stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'failed': 0,
            'duplicates': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def process_tender_batch(
        self,
        raw_tenders: List[Dict[str, Any]],
        source_system: str,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a batch of tender data"""
        
        logger.info(f"Processing batch of {len(raw_tenders)} tenders from {source_system}")
        self.stats['start_time'] = datetime.now()
        
        # Log ingestion start
        async with get_async_session() as session:
            ingestion_log = DataIngestionLog(
                source_system=source_system,
                job_id=job_id,
                job_type='tender_ingestion',
                started_at=self.stats['start_time'],
                status='running'
            )
            session.add(ingestion_log)
            await session.commit()
            log_id = ingestion_log.id
        
        try:
            # Transform and validate data
            validation_results = self.transformer.transform_batch(raw_tenders, 'tender')
            
            # Process valid tenders
            valid_tenders = [
                result.cleaned_data for result in validation_results 
                if result.is_valid
            ]
            
            # Enrich data
            enriched_tenders = await self.enricher.enrich_tender_batch(valid_tenders)
            
            # Detect duplicates and process
            processed_tenders = await self._process_tender_duplicates(enriched_tenders)
            
            # Store in database
            await self._store_tenders_in_database(processed_tenders)
            
            self.stats['end_time'] = datetime.now()
            
            # Update ingestion log
            async with get_async_session() as session:
                await session.execute(
                    select(DataIngestionLog).where(DataIngestionLog.id == log_id)
                )
                log_entry = await session.scalar(
                    select(DataIngestionLog).where(DataIngestionLog.id == log_id)
                )
                
                if log_entry:
                    log_entry.completed_at = self.stats['end_time']
                    log_entry.status = 'completed'
                    log_entry.records_processed = len(raw_tenders)
                    log_entry.records_created = self.stats['created']
                    log_entry.records_updated = self.stats['updated']
                    log_entry.records_failed = self.stats['failed']
                    log_entry.metadata = self.stats
                    
                    await session.commit()
            
            logger.info(f"Batch processing completed: {self.stats}")
            return self.stats
            
        except Exception as e:
            logger.error(f"Error processing tender batch: {str(e)}")
            
            # Update ingestion log with error
            async with get_async_session() as session:
                log_entry = await session.scalar(
                    select(DataIngestionLog).where(DataIngestionLog.id == log_id)
                )
                
                if log_entry:
                    log_entry.completed_at = datetime.now()
                    log_entry.status = 'failed'
                    log_entry.error_message = str(e)
                    log_entry.records_failed = len(raw_tenders)
                    
                    await session.commit()
            
            raise
    
    async def _process_tender_duplicates(
        self, 
        tenders: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process tender duplicates"""
        
        processed_tenders = []
        
        for tender in tenders:
            try:
                # Check for duplicates
                existing_tender = await self.duplicate_detector.find_duplicate_tender(tender)
                
                if existing_tender:
                    logger.info(f"Found duplicate tender: {tender['external_id']}")
                    
                    # Merge data
                    merged_tender = await self.duplicate_detector.merge_tender_data(
                        existing_tender, tender
                    )
                    
                    merged_tender['_operation'] = 'update'
                    merged_tender['_existing_id'] = existing_tender.id
                    processed_tenders.append(merged_tender)
                    
                    self.stats['duplicates'] += 1
                    
                else:
                    tender['_operation'] = 'create'
                    processed_tenders.append(tender)
                
                self.stats['processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing tender {tender.get('external_id', 'unknown')}: {str(e)}")
                self.stats['failed'] += 1
                continue
        
        return processed_tenders
    
    async def _store_tenders_in_database(self, tenders: List[Dict[str, Any]]):
        """Store processed tenders in database"""
        
        async with get_async_session() as session:
            for tender_data in tenders:
                try:
                    if tender_data['_operation'] == 'create':
                        await self._create_tender(session, tender_data)
                        self.stats['created'] += 1
                    elif tender_data['_operation'] == 'update':
                        await self._update_tender(session, tender_data)
                        self.stats['updated'] += 1
                        
                except Exception as e:
                    logger.error(f"Error storing tender: {str(e)}")
                    self.stats['failed'] += 1
                    continue
            
            await session.commit()
    
    async def _create_tender(self, session: AsyncSession, tender_data: Dict[str, Any]):
        """Create new tender in database"""
        
        # Get or create contracting authority
        contracting_authority = await self._get_or_create_contracting_authority(
            session, tender_data
        )
        
        # Get or create CPV code
        cpv_code = await self._get_or_create_cpv_code(session, tender_data)
        
        # Create tender
        tender = Tender(
            source_system=tender_data['source_system'],
            external_id=tender_data['external_id'],
            title=tender_data['title'],
            description=tender_data.get('description'),
            contracting_authority_id=contracting_authority.id if contracting_authority else None,
            cpv_code=cpv_code if cpv_code else None,
            tender_type=tender_data.get('tender_type'),
            procedure_type=tender_data.get('procedure_type'),
            estimated_value=tender_data.get('estimated_value'),
            currency=tender_data.get('currency', 'RON'),
            publication_date=tender_data.get('publication_date'),
            submission_deadline=tender_data.get('submission_deadline'),
            opening_date=tender_data.get('opening_date'),
            contract_start_date=tender_data.get('contract_start_date'),
            contract_end_date=tender_data.get('contract_end_date'),
            status=tender_data.get('status', 'unknown'),
            raw_data=tender_data.get('raw_data', {}),
            processed_data=tender_data.get('processed_data', {}),
            last_scraped_at=datetime.now()
        )
        
        session.add(tender)
        logger.info(f"Created tender: {tender.external_id}")
    
    async def _update_tender(self, session: AsyncSession, tender_data: Dict[str, Any]):
        """Update existing tender in database"""
        
        existing_id = tender_data['_existing_id']
        
        # Get existing tender
        existing_tender = await session.scalar(
            select(Tender).where(Tender.id == existing_id)
        )
        
        if not existing_tender:
            logger.warning(f"Tender {existing_id} not found for update")
            return
        
        # Update fields
        for field in ['title', 'description', 'tender_type', 'procedure_type', 
                     'estimated_value', 'currency', 'publication_date', 
                     'submission_deadline', 'opening_date', 'contract_start_date',
                     'contract_end_date', 'status']:
            if field in tender_data:
                setattr(existing_tender, field, tender_data[field])
        
        # Update metadata
        existing_tender.updated_at = datetime.now()
        existing_tender.last_scraped_at = datetime.now()
        
        # Merge processed data
        if tender_data.get('processed_data'):
            existing_processed = existing_tender.processed_data or {}
            existing_processed.update(tender_data['processed_data'])
            existing_tender.processed_data = existing_processed
        
        logger.info(f"Updated tender: {existing_tender.external_id}")
    
    async def _get_or_create_contracting_authority(
        self, 
        session: AsyncSession, 
        tender_data: Dict[str, Any]
    ) -> Optional[ContractingAuthority]:
        """Get or create contracting authority"""
        
        authority_name = tender_data.get('contracting_authority')
        if not authority_name:
            return None
        
        # Try to find existing authority
        authority = await session.scalar(
            select(ContractingAuthority).where(
                ContractingAuthority.name == authority_name
            )
        )
        
        if authority:
            return authority
        
        # Create new authority
        authority_data = tender_data.get('contracting_authority_details', {})
        
        authority = ContractingAuthority(
            name=authority_name,
            cui=authority_data.get('cui'),
            address=authority_data.get('address'),
            county=authority_data.get('county'),
            city=authority_data.get('city'),
            contact_email=authority_data.get('contact_email'),
            contact_phone=authority_data.get('contact_phone'),
            website=authority_data.get('website'),
            authority_type=authority_data.get('authority_type')
        )
        
        session.add(authority)
        await session.flush()  # Get the ID
        
        logger.info(f"Created contracting authority: {authority.name}")
        return authority
    
    async def _get_or_create_cpv_code(
        self, 
        session: AsyncSession, 
        tender_data: Dict[str, Any]
    ) -> Optional[str]:
        """Get or create CPV code"""
        
        cpv_code = tender_data.get('cpv_code')
        if not cpv_code:
            return None
        
        # Check if CPV code exists
        existing_cpv = await session.scalar(
            select(CPVCode).where(CPVCode.code == cpv_code)
        )
        
        if existing_cpv:
            return cpv_code
        
        # Create new CPV code entry
        cpv_description = tender_data.get('cpv_description', f"CPV Code {cpv_code}")
        level = len(cpv_code.split('-')[0]) // 2  # Rough calculation
        
        cpv_entry = CPVCode(
            code=cpv_code,
            description=cpv_description,
            level=level
        )
        
        session.add(cpv_entry)
        logger.info(f"Created CPV code: {cpv_code}")
        
        return cpv_code
    
    async def process_company_batch(
        self,
        raw_companies: List[Dict[str, Any]],
        source_system: str,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a batch of company data"""
        
        logger.info(f"Processing batch of {len(raw_companies)} companies from {source_system}")
        
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'failed': 0,
            'duplicates': 0
        }
        
        try:
            # Transform and validate data
            validation_results = self.transformer.transform_batch(raw_companies, 'company')
            
            # Process valid companies
            valid_companies = [
                result.cleaned_data for result in validation_results 
                if result.is_valid
            ]
            
            # Enrich data
            enriched_companies = await self.enricher.enrich_company_batch(valid_companies)
            
            # Store in database
            async with get_async_session() as session:
                for company_data in enriched_companies:
                    try:
                        # Check for duplicates
                        existing_company = await self.duplicate_detector.find_duplicate_company(
                            company_data
                        )
                        
                        if existing_company:
                            # Update existing company
                            await self._update_company(session, existing_company, company_data)
                            stats['updated'] += 1
                            stats['duplicates'] += 1
                        else:
                            # Create new company
                            await self._create_company(session, company_data)
                            stats['created'] += 1
                        
                        stats['processed'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing company {company_data.get('name', 'unknown')}: {str(e)}")
                        stats['failed'] += 1
                        continue
                
                await session.commit()
            
            logger.info(f"Company batch processing completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error processing company batch: {str(e)}")
            raise
    
    async def _create_company(self, session: AsyncSession, company_data: Dict[str, Any]):
        """Create new company in database"""
        
        company = Company(
            name=company_data['name'],
            cui=company_data['cui'],
            registration_number=company_data.get('registration_number'),
            address=company_data.get('address'),
            county=company_data.get('county'),
            city=company_data.get('city'),
            contact_email=company_data.get('contact_email'),
            contact_phone=company_data.get('contact_phone'),
            company_type=company_data.get('company_type'),
            company_size=company_data.get('company_size')
        )
        
        session.add(company)
        logger.info(f"Created company: {company.name}")
    
    async def _update_company(
        self, 
        session: AsyncSession, 
        existing_company: Company,
        company_data: Dict[str, Any]
    ):
        """Update existing company"""
        
        # Update fields
        for field in ['name', 'registration_number', 'address', 'county', 'city',
                     'contact_email', 'contact_phone', 'company_type', 'company_size']:
            if field in company_data and company_data[field]:
                setattr(existing_company, field, company_data[field])
        
        existing_company.updated_at = datetime.now()
        logger.info(f"Updated company: {existing_company.name}")
    
    async def process_incremental_update(
        self,
        source_system: str,
        last_update: datetime,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process incremental updates since last sync"""
        
        logger.info(f"Processing incremental update for {source_system} since {last_update}")
        
        # This would be implemented based on the specific scraper
        # For now, return empty stats
        return {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'failed': 0,
            'duplicates': 0
        }
    
    def reset_stats(self):
        """Reset processing statistics"""
        self.stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'failed': 0,
            'duplicates': 0,
            'start_time': None,
            'end_time': None
        }