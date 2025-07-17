"""
Duplicate detection and data merging for Romanian procurement data
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from fuzzywuzzy import fuzz, process
import hashlib
import json

from app.core.database import get_async_session
from app.core.logging import logger
from app.db.models import Tender, Company, ContractingAuthority
from app.services.scrapers.utils import TextCleaner


class DuplicateDetector:
    """Service for detecting and handling duplicate data"""
    
    def __init__(self):
        self.similarity_threshold = 85  # Minimum similarity score for duplicates
        self.fuzzy_threshold = 80       # Fuzzy matching threshold
        
    async def find_duplicate_tender(self, tender_data: Dict[str, Any]) -> Optional[Tender]:
        """Find duplicate tender in database"""
        
        try:
            async with get_async_session() as session:
                # First, try exact match by external_id and source_system
                existing_tender = await session.scalar(
                    select(Tender).where(
                        and_(
                            Tender.external_id == tender_data.get('external_id'),
                            Tender.source_system == tender_data.get('source_system')
                        )
                    )
                )
                
                if existing_tender:
                    logger.debug(f"Found exact duplicate: {existing_tender.external_id}")
                    return existing_tender
                
                # If no exact match, try fuzzy matching
                potential_duplicates = await self._find_potential_tender_duplicates(
                    session, tender_data
                )
                
                if potential_duplicates:
                    # Use the highest scoring match
                    best_match = max(potential_duplicates, key=lambda x: x['score'])
                    
                    if best_match['score'] >= self.similarity_threshold:
                        logger.debug(f"Found fuzzy duplicate: {best_match['tender'].external_id} (score: {best_match['score']})")
                        return best_match['tender']
                
                return None
                
        except Exception as e:
            logger.error(f"Error finding duplicate tender: {str(e)}")
            return None
    
    async def _find_potential_tender_duplicates(
        self, 
        session: AsyncSession, 
        tender_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find potential tender duplicates using fuzzy matching"""
        
        potential_duplicates = []
        
        try:
            # Build query conditions
            conditions = []
            
            # Match by contracting authority
            if 'contracting_authority' in tender_data:
                conditions.append(
                    Tender.contracting_authority.has(
                        ContractingAuthority.name.ilike(f"%{tender_data['contracting_authority']}%")
                    )
                )
            
            # Match by publication date (within 30 days)
            if 'publication_date' in tender_data and tender_data['publication_date']:
                pub_date = tender_data['publication_date']
                conditions.append(
                    and_(
                        Tender.publication_date >= pub_date - timedelta(days=30),
                        Tender.publication_date <= pub_date + timedelta(days=30)
                    )
                )
            
            # Match by estimated value (within 20% range)
            if 'estimated_value' in tender_data and tender_data['estimated_value']:
                value = tender_data['estimated_value']
                value_min = value * 0.8
                value_max = value * 1.2
                conditions.append(
                    and_(
                        Tender.estimated_value >= value_min,
                        Tender.estimated_value <= value_max
                    )
                )
            
            if not conditions:
                return potential_duplicates
            
            # Execute query
            result = await session.execute(
                select(Tender).where(or_(*conditions)).limit(50)
            )
            
            candidates = result.scalars().all()
            
            # Calculate similarity scores
            for candidate in candidates:
                score = self._calculate_tender_similarity(tender_data, candidate)
                
                if score >= self.fuzzy_threshold:
                    potential_duplicates.append({
                        'tender': candidate,
                        'score': score
                    })
            
            return potential_duplicates
            
        except Exception as e:
            logger.error(f"Error finding potential duplicates: {str(e)}")
            return []
    
    def _calculate_tender_similarity(self, tender_data: Dict[str, Any], existing_tender: Tender) -> float:
        """Calculate similarity score between tender data and existing tender"""
        
        scores = []
        
        # Title similarity
        if 'title' in tender_data and existing_tender.title:
            title_score = fuzz.partial_ratio(
                tender_data['title'].lower(),
                existing_tender.title.lower()
            )
            scores.append(title_score * 0.4)  # 40% weight
        
        # Description similarity
        if 'description' in tender_data and existing_tender.description:
            desc_score = fuzz.partial_ratio(
                tender_data['description'].lower(),
                existing_tender.description.lower()
            )
            scores.append(desc_score * 0.2)  # 20% weight
        
        # Contracting authority similarity
        if 'contracting_authority' in tender_data and existing_tender.contracting_authority:
            auth_score = fuzz.ratio(
                tender_data['contracting_authority'].lower(),
                existing_tender.contracting_authority.name.lower()
            )
            scores.append(auth_score * 0.3)  # 30% weight
        
        # Value similarity
        if 'estimated_value' in tender_data and existing_tender.estimated_value:
            value_diff = abs(tender_data['estimated_value'] - float(existing_tender.estimated_value))
            max_value = max(tender_data['estimated_value'], float(existing_tender.estimated_value))
            
            if max_value > 0:
                value_score = max(0, 100 - (value_diff / max_value * 100))
                scores.append(value_score * 0.1)  # 10% weight
        
        # Calculate weighted average
        if scores:
            return sum(scores) / sum([0.4, 0.2, 0.3, 0.1][:len(scores)])
        
        return 0
    
    async def merge_tender_data(
        self, 
        existing_tender: Tender, 
        new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge new tender data with existing tender"""
        
        merged_data = new_data.copy()
        
        try:
            # Merge strategy: prefer newer data, but keep existing if new is empty
            merge_fields = [
                'title', 'description', 'tender_type', 'procedure_type',
                'estimated_value', 'currency', 'publication_date',
                'submission_deadline', 'opening_date', 'contract_start_date',
                'contract_end_date', 'status'
            ]
            
            for field in merge_fields:
                existing_value = getattr(existing_tender, field, None)
                new_value = new_data.get(field)
                
                # Use merge logic
                merged_value = self._merge_field_values(existing_value, new_value, field)
                
                if merged_value is not None:
                    merged_data[field] = merged_value
            
            # Merge processed data
            existing_processed = existing_tender.processed_data or {}
            new_processed = new_data.get('processed_data', {})
            
            merged_processed = existing_processed.copy()
            merged_processed.update(new_processed)
            merged_processed['last_merged_at'] = datetime.now().isoformat()
            
            merged_data['processed_data'] = merged_processed
            
            # Merge raw data
            existing_raw = existing_tender.raw_data or {}
            new_raw = new_data.get('raw_data', {})
            
            merged_raw = existing_raw.copy()
            merged_raw.update(new_raw)
            
            merged_data['raw_data'] = merged_raw
            
            logger.debug(f"Merged tender data for {existing_tender.external_id}")
            
            return merged_data
            
        except Exception as e:
            logger.error(f"Error merging tender data: {str(e)}")
            return new_data
    
    def _merge_field_values(self, existing_value: Any, new_value: Any, field_name: str) -> Any:
        """Merge two field values using field-specific logic"""
        
        # If new value is empty, keep existing
        if new_value is None or new_value == '':
            return existing_value
        
        # If existing value is empty, use new
        if existing_value is None or existing_value == '':
            return new_value
        
        # Field-specific merge logic
        if field_name == 'estimated_value':
            # Use the more recent or higher value
            if isinstance(existing_value, (int, float)) and isinstance(new_value, (int, float)):
                return max(existing_value, new_value)
            return new_value
        
        elif field_name == 'description':
            # Use the longer description
            if len(str(new_value)) > len(str(existing_value)):
                return new_value
            return existing_value
        
        elif field_name in ['publication_date', 'submission_deadline', 'opening_date']:
            # Use the more recent date
            if isinstance(existing_value, datetime) and isinstance(new_value, datetime):
                return max(existing_value, new_value)
            return new_value
        
        elif field_name == 'status':
            # Status priority: active > awarded > closed > cancelled > unknown
            status_priority = {
                'active': 5,
                'awarded': 4,
                'closed': 3,
                'cancelled': 2,
                'unknown': 1
            }
            
            existing_priority = status_priority.get(str(existing_value).lower(), 0)
            new_priority = status_priority.get(str(new_value).lower(), 0)
            
            return existing_value if existing_priority >= new_priority else new_value
        
        else:
            # Default: use new value
            return new_value
    
    async def find_duplicate_company(self, company_data: Dict[str, Any]) -> Optional[Company]:
        """Find duplicate company in database"""
        
        try:
            async with get_async_session() as session:
                # First, try exact match by CUI
                if 'cui' in company_data:
                    existing_company = await session.scalar(
                        select(Company).where(Company.cui == company_data['cui'])
                    )
                    
                    if existing_company:
                        logger.debug(f"Found exact company duplicate by CUI: {existing_company.cui}")
                        return existing_company
                
                # Try fuzzy matching by name
                if 'name' in company_data:
                    potential_duplicates = await self._find_potential_company_duplicates(
                        session, company_data
                    )
                    
                    if potential_duplicates:
                        best_match = max(potential_duplicates, key=lambda x: x['score'])
                        
                        if best_match['score'] >= self.similarity_threshold:
                            logger.debug(f"Found fuzzy company duplicate: {best_match['company'].name} (score: {best_match['score']})")
                            return best_match['company']
                
                return None
                
        except Exception as e:
            logger.error(f"Error finding duplicate company: {str(e)}")
            return None
    
    async def _find_potential_company_duplicates(
        self, 
        session: AsyncSession, 
        company_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find potential company duplicates using fuzzy matching"""
        
        potential_duplicates = []
        
        try:
            company_name = company_data.get('name', '')
            
            # Search for companies with similar names
            result = await session.execute(
                select(Company).where(
                    Company.name.ilike(f"%{company_name[:10]}%")
                ).limit(20)
            )
            
            candidates = result.scalars().all()
            
            # Calculate similarity scores
            for candidate in candidates:
                score = self._calculate_company_similarity(company_data, candidate)
                
                if score >= self.fuzzy_threshold:
                    potential_duplicates.append({
                        'company': candidate,
                        'score': score
                    })
            
            return potential_duplicates
            
        except Exception as e:
            logger.error(f"Error finding potential company duplicates: {str(e)}")
            return []
    
    def _calculate_company_similarity(self, company_data: Dict[str, Any], existing_company: Company) -> float:
        """Calculate similarity score between company data and existing company"""
        
        scores = []
        
        # Name similarity
        if 'name' in company_data and existing_company.name:
            name_score = fuzz.ratio(
                company_data['name'].lower(),
                existing_company.name.lower()
            )
            scores.append(name_score * 0.6)  # 60% weight
        
        # Address similarity
        if 'address' in company_data and existing_company.address:
            addr_score = fuzz.partial_ratio(
                company_data['address'].lower(),
                existing_company.address.lower()
            )
            scores.append(addr_score * 0.2)  # 20% weight
        
        # City similarity
        if 'city' in company_data and existing_company.city:
            city_score = fuzz.ratio(
                company_data['city'].lower(),
                existing_company.city.lower()
            )
            scores.append(city_score * 0.1)  # 10% weight
        
        # County similarity
        if 'county' in company_data and existing_company.county:
            county_score = fuzz.ratio(
                company_data['county'].lower(),
                existing_company.county.lower()
            )
            scores.append(county_score * 0.1)  # 10% weight
        
        # Calculate weighted average
        if scores:
            total_weight = sum([0.6, 0.2, 0.1, 0.1][:len(scores)])
            return sum(scores) / total_weight
        
        return 0
    
    async def find_duplicate_contracting_authority(
        self, 
        authority_data: Dict[str, Any]
    ) -> Optional[ContractingAuthority]:
        """Find duplicate contracting authority in database"""
        
        try:
            async with get_async_session() as session:
                authority_name = authority_data.get('name', '')
                
                # Try exact match
                existing_authority = await session.scalar(
                    select(ContractingAuthority).where(
                        ContractingAuthority.name == authority_name
                    )
                )
                
                if existing_authority:
                    return existing_authority
                
                # Try fuzzy matching
                result = await session.execute(
                    select(ContractingAuthority).where(
                        ContractingAuthority.name.ilike(f"%{authority_name[:10]}%")
                    ).limit(10)
                )
                
                candidates = result.scalars().all()
                
                best_match = None
                best_score = 0
                
                for candidate in candidates:
                    score = fuzz.ratio(
                        authority_name.lower(),
                        candidate.name.lower()
                    )
                    
                    if score > best_score and score >= self.similarity_threshold:
                        best_score = score
                        best_match = candidate
                
                if best_match:
                    logger.debug(f"Found fuzzy authority duplicate: {best_match.name} (score: {best_score})")
                
                return best_match
                
        except Exception as e:
            logger.error(f"Error finding duplicate authority: {str(e)}")
            return None
    
    def generate_data_fingerprint(self, data: Dict[str, Any]) -> str:
        """Generate fingerprint for data deduplication"""
        
        # Extract key fields for fingerprinting
        fingerprint_fields = []
        
        if 'title' in data:
            fingerprint_fields.append(TextCleaner.normalize_romanian_text(data['title']))
        
        if 'contracting_authority' in data:
            fingerprint_fields.append(TextCleaner.normalize_romanian_text(data['contracting_authority']))
        
        if 'estimated_value' in data:
            fingerprint_fields.append(str(data['estimated_value']))
        
        if 'publication_date' in data:
            fingerprint_fields.append(str(data['publication_date']))
        
        # Create fingerprint
        fingerprint_string = '|'.join(fingerprint_fields)
        
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    async def bulk_deduplicate_tenders(
        self, 
        tenders: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Bulk deduplicate a list of tenders"""
        
        logger.info(f"Bulk deduplicating {len(tenders)} tenders")
        
        # Group by fingerprint
        fingerprint_groups = {}
        
        for tender in tenders:
            fingerprint = self.generate_data_fingerprint(tender)
            
            if fingerprint not in fingerprint_groups:
                fingerprint_groups[fingerprint] = []
            
            fingerprint_groups[fingerprint].append(tender)
        
        # Process each group
        deduplicated_tenders = []
        
        for fingerprint, group in fingerprint_groups.items():
            if len(group) == 1:
                # No duplicates
                deduplicated_tenders.append(group[0])
            else:
                # Merge duplicates
                merged_tender = await self._merge_tender_group(group)
                deduplicated_tenders.append(merged_tender)
        
        logger.info(f"Deduplication complete: {len(tenders)} -> {len(deduplicated_tenders)}")
        
        return deduplicated_tenders
    
    async def _merge_tender_group(self, tender_group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge a group of duplicate tenders"""
        
        # Start with the first tender
        merged_tender = tender_group[0].copy()
        
        # Merge with each subsequent tender
        for tender in tender_group[1:]:
            merged_tender = await self._merge_tender_dicts(merged_tender, tender)
        
        return merged_tender
    
    async def _merge_tender_dicts(
        self, 
        tender1: Dict[str, Any], 
        tender2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two tender dictionaries"""
        
        merged = tender1.copy()
        
        # Merge each field
        for field in tender2:
            if field in merged:
                merged[field] = self._merge_field_values(merged[field], tender2[field], field)
            else:
                merged[field] = tender2[field]
        
        return merged