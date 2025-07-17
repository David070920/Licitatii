"""
Data enrichment services for Romanian procurement data
"""

import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import json

from app.core.logging import logger
from app.services.scrapers.utils import TextCleaner


class DataEnricher:
    """Data enrichment service for procurement data"""
    
    def __init__(self):
        self.geocoder = Nominatim(user_agent="romanian_procurement_platform")
        self.cpv_mapper = CPVMapper()
        self.company_matcher = CompanyMatcher()
        self.geographic_enricher = GeographicEnricher()
        
    async def enrich_tender_batch(self, tenders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich a batch of tender data"""
        
        logger.info(f"Enriching batch of {len(tenders)} tenders")
        
        enriched_tenders = []
        
        for tender in tenders:
            try:
                enriched_tender = await self.enrich_tender(tender)
                enriched_tenders.append(enriched_tender)
                
            except Exception as e:
                logger.error(f"Error enriching tender {tender.get('external_id', 'unknown')}: {str(e)}")
                # Add original tender without enrichment
                enriched_tenders.append(tender)
        
        logger.info(f"Enriched {len(enriched_tenders)} tenders")
        return enriched_tenders
    
    async def enrich_tender(self, tender: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single tender with additional data"""
        
        enriched = tender.copy()
        
        # Initialize processed_data if not exists
        if 'processed_data' not in enriched:
            enriched['processed_data'] = {}
        
        # Enrich CPV codes
        if 'title' in tender or 'description' in tender:
            await self._enrich_cpv_codes(enriched)
        
        # Enrich geographic data
        if 'contracting_authority_details' in tender:
            await self._enrich_geographic_data(enriched)
        
        # Enrich company information
        if 'contracting_authority' in tender:
            await self._enrich_authority_data(enriched)
        
        # Enrich classification
        await self._enrich_classification(enriched)
        
        # Add enrichment metadata
        enriched['processed_data']['enriched_at'] = datetime.now().isoformat()
        enriched['processed_data']['enrichment_version'] = '1.0'
        
        return enriched
    
    async def _enrich_cpv_codes(self, tender: Dict[str, Any]):
        """Enrich CPV codes based on tender content"""
        
        try:
            # Get text content for CPV mapping
            text_content = []
            
            if 'title' in tender:
                text_content.append(tender['title'])
            
            if 'description' in tender:
                text_content.append(tender['description'])
            
            combined_text = ' '.join(text_content)
            
            # Map CPV codes
            cpv_suggestions = await self.cpv_mapper.suggest_cpv_codes(combined_text)
            
            if cpv_suggestions:
                if 'cpv_code' not in tender or not tender['cpv_code']:
                    # Use the most confident suggestion
                    best_suggestion = max(cpv_suggestions, key=lambda x: x['confidence'])
                    tender['cpv_code'] = best_suggestion['code']
                    tender['cpv_description'] = best_suggestion['description']
                
                # Store all suggestions
                tender['processed_data']['cpv_suggestions'] = cpv_suggestions
                
                logger.debug(f"CPV codes suggested for tender {tender.get('external_id', 'unknown')}: {len(cpv_suggestions)}")
            
        except Exception as e:
            logger.warning(f"Error enriching CPV codes: {str(e)}")
    
    async def _enrich_geographic_data(self, tender: Dict[str, Any]):
        """Enrich geographic data"""
        
        try:
            authority_details = tender.get('contracting_authority_details', {})
            
            if 'address' in authority_details:
                address = authority_details['address']
                
                # Geocode address
                location = await self.geographic_enricher.geocode_address(address)
                
                if location:
                    tender['processed_data']['geographic'] = {
                        'latitude': location['latitude'],
                        'longitude': location['longitude'],
                        'formatted_address': location['formatted_address'],
                        'county': location.get('county'),
                        'city': location.get('city'),
                        'region': location.get('region')
                    }
                    
                    logger.debug(f"Geocoded address for tender {tender.get('external_id', 'unknown')}")
            
        except Exception as e:
            logger.warning(f"Error enriching geographic data: {str(e)}")
    
    async def _enrich_authority_data(self, tender: Dict[str, Any]):
        """Enrich contracting authority data"""
        
        try:
            authority_name = tender.get('contracting_authority')
            
            if authority_name:
                # Try to match with existing authority data
                authority_info = await self.company_matcher.match_authority(authority_name)
                
                if authority_info:
                    if 'contracting_authority_details' not in tender:
                        tender['contracting_authority_details'] = {}
                    
                    tender['contracting_authority_details'].update(authority_info)
                    
                    logger.debug(f"Enriched authority data for {authority_name}")
            
        except Exception as e:
            logger.warning(f"Error enriching authority data: {str(e)}")
    
    async def _enrich_classification(self, tender: Dict[str, Any]):
        """Enrich tender classification"""
        
        try:
            # Determine tender category
            category = self._classify_tender_category(tender)
            tender['processed_data']['category'] = category
            
            # Determine complexity level
            complexity = self._assess_complexity(tender)
            tender['processed_data']['complexity'] = complexity
            
            # Determine risk level (basic assessment)
            risk_level = self._assess_basic_risk(tender)
            tender['processed_data']['risk_level'] = risk_level
            
        except Exception as e:
            logger.warning(f"Error enriching classification: {str(e)}")
    
    def _classify_tender_category(self, tender: Dict[str, Any]) -> str:
        """Classify tender into category"""
        
        # Use CPV code if available
        if 'cpv_code' in tender and tender['cpv_code']:
            cpv_code = tender['cpv_code']
            
            # Basic CPV classification
            if cpv_code.startswith('45'):
                return 'construction'
            elif cpv_code.startswith(('30', '31', '32', '33', '34', '35', '37', '38', '39')):
                return 'goods'
            elif cpv_code.startswith(('50', '51', '55', '60', '63', '64', '65', '66', '67', '68', '70', '71', '72', '73', '74', '75', '76', '77', '79', '80', '85', '90', '92', '98')):
                return 'services'
        
        # Use title/description analysis
        title = tender.get('title', '').lower()
        description = tender.get('description', '').lower()
        
        combined_text = f"{title} {description}"
        
        # Construction keywords
        construction_keywords = [
            'constructie', 'construire', 'edificare', 'lucrari', 'reparatie',
            'renovare', 'modernizare', 'infrastructura', 'cladire', 'drum',
            'pod', 'instalatie', 'amenajare'
        ]
        
        # Goods keywords
        goods_keywords = [
            'achizitie', 'cumparare', 'furnizare', 'livrare', 'echipament',
            'aparatura', 'mobilier', 'material', 'produs', 'bunuri'
        ]
        
        # Services keywords
        services_keywords = [
            'servicii', 'consultanta', 'asistenta', 'expertiza', 'proiectare',
            'mentenanta', 'intretinere', 'transport', 'comunicare', 'instruire'
        ]
        
        # Count keyword matches
        construction_score = sum(1 for keyword in construction_keywords if keyword in combined_text)
        goods_score = sum(1 for keyword in goods_keywords if keyword in combined_text)
        services_score = sum(1 for keyword in services_keywords if keyword in combined_text)
        
        # Determine category
        if construction_score > goods_score and construction_score > services_score:
            return 'construction'
        elif goods_score > services_score:
            return 'goods'
        else:
            return 'services'
    
    def _assess_complexity(self, tender: Dict[str, Any]) -> str:
        """Assess tender complexity"""
        
        complexity_score = 0
        
        # Value-based complexity
        if 'estimated_value' in tender and tender['estimated_value']:
            value = tender['estimated_value']
            if value > 10000000:  # > 10M RON
                complexity_score += 3
            elif value > 1000000:  # > 1M RON
                complexity_score += 2
            elif value > 100000:  # > 100K RON
                complexity_score += 1
        
        # Duration-based complexity
        if 'contract_start_date' in tender and 'contract_end_date' in tender:
            start_date = tender['contract_start_date']
            end_date = tender['contract_end_date']
            
            if start_date and end_date:
                duration = (end_date - start_date).days
                if duration > 365:  # > 1 year
                    complexity_score += 2
                elif duration > 180:  # > 6 months
                    complexity_score += 1
        
        # Procedure-based complexity
        if 'procedure_type' in tender:
            procedure = tender['procedure_type']
            if procedure in ['dialog-competitiv', 'partenariat-inovatie']:
                complexity_score += 2
            elif procedure in ['negociere-cu-publicarea', 'licitatie-restransa']:
                complexity_score += 1
        
        # Content-based complexity
        title = tender.get('title', '')
        description = tender.get('description', '')
        
        complex_keywords = [
            'complex', 'sistem', 'integrat', 'sofisticat', 'avansat',
            'tehnologie', 'inovativ', 'specializat', 'expertiza'
        ]
        
        combined_text = f"{title} {description}".lower()
        for keyword in complex_keywords:
            if keyword in combined_text:
                complexity_score += 1
        
        # Determine complexity level
        if complexity_score >= 6:
            return 'high'
        elif complexity_score >= 3:
            return 'medium'
        else:
            return 'low'
    
    def _assess_basic_risk(self, tender: Dict[str, Any]) -> str:
        """Basic risk assessment"""
        
        risk_score = 0
        
        # Single bidder risk
        if 'bids' in tender and len(tender['bids']) == 1:
            risk_score += 2
        
        # Unusual value patterns
        if 'estimated_value' in tender and tender['estimated_value']:
            value = tender['estimated_value']
            # Very round numbers might indicate estimate manipulation
            if value % 1000000 == 0 or value % 100000 == 0:
                risk_score += 1
        
        # Short submission periods
        if 'publication_date' in tender and 'submission_deadline' in tender:
            pub_date = tender['publication_date']
            sub_deadline = tender['submission_deadline']
            
            if pub_date and sub_deadline:
                days_diff = (sub_deadline - pub_date).days
                if days_diff < 10:
                    risk_score += 2
                elif days_diff < 20:
                    risk_score += 1
        
        # Determine risk level
        if risk_score >= 4:
            return 'high'
        elif risk_score >= 2:
            return 'medium'
        else:
            return 'low'
    
    async def enrich_company_batch(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich a batch of company data"""
        
        logger.info(f"Enriching batch of {len(companies)} companies")
        
        enriched_companies = []
        
        for company in companies:
            try:
                enriched_company = await self.enrich_company(company)
                enriched_companies.append(enriched_company)
                
            except Exception as e:
                logger.error(f"Error enriching company {company.get('name', 'unknown')}: {str(e)}")
                enriched_companies.append(company)
        
        return enriched_companies
    
    async def enrich_company(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single company with additional data"""
        
        enriched = company.copy()
        
        # Initialize processed_data if not exists
        if 'processed_data' not in enriched:
            enriched['processed_data'] = {}
        
        # Enrich geographic data
        if 'address' in company:
            await self._enrich_company_geographic_data(enriched)
        
        # Enrich company classification
        await self._enrich_company_classification(enriched)
        
        # Add enrichment metadata
        enriched['processed_data']['enriched_at'] = datetime.now().isoformat()
        
        return enriched
    
    async def _enrich_company_geographic_data(self, company: Dict[str, Any]):
        """Enrich company geographic data"""
        
        try:
            address = company.get('address')
            
            if address:
                location = await self.geographic_enricher.geocode_address(address)
                
                if location:
                    company['processed_data']['geographic'] = {
                        'latitude': location['latitude'],
                        'longitude': location['longitude'],
                        'formatted_address': location['formatted_address'],
                        'county': location.get('county'),
                        'city': location.get('city'),
                        'region': location.get('region')
                    }
            
        except Exception as e:
            logger.warning(f"Error enriching company geographic data: {str(e)}")
    
    async def _enrich_company_classification(self, company: Dict[str, Any]):
        """Enrich company classification"""
        
        try:
            # Determine company size based on available data
            if 'company_size' not in company:
                company['company_size'] = 'unknown'
            
            # Set default company type if not available
            if 'company_type' not in company:
                company['company_type'] = 'private'
            
        except Exception as e:
            logger.warning(f"Error enriching company classification: {str(e)}")


class CPVMapper:
    """CPV code mapping service"""
    
    def __init__(self):
        self.cpv_keywords = self._load_cpv_keywords()
    
    def _load_cpv_keywords(self) -> Dict[str, List[str]]:
        """Load CPV code keywords mapping"""
        
        # Simplified mapping - in production, this would be loaded from database
        return {
            '45000000': ['constructie', 'construire', 'edificare', 'lucrari'],
            '30000000': ['echipament', 'aparatura', 'masini', 'utilaje'],
            '50000000': ['reparatie', 'mentenanta', 'intretinere'],
            '60000000': ['transport', 'expeditie', 'logistica'],
            '70000000': ['servicii', 'consultanta', 'asistenta'],
            '80000000': ['educatie', 'formare', 'instruire'],
            '90000000': ['curatenie', 'salubritate', 'mediu']
        }
    
    async def suggest_cpv_codes(self, text: str) -> List[Dict[str, Any]]:
        """Suggest CPV codes based on text content"""
        
        suggestions = []
        text_lower = text.lower()
        
        for cpv_code, keywords in self.cpv_keywords.items():
            confidence = 0
            
            for keyword in keywords:
                if keyword in text_lower:
                    confidence += 1
            
            if confidence > 0:
                suggestions.append({
                    'code': cpv_code,
                    'description': f"CPV {cpv_code}",
                    'confidence': confidence / len(keywords)
                })
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        
        return suggestions[:5]  # Return top 5 suggestions


class CompanyMatcher:
    """Company matching and enrichment service"""
    
    async def match_authority(self, authority_name: str) -> Optional[Dict[str, Any]]:
        """Match authority name with additional data"""
        
        try:
            # In production, this would query external databases
            # For now, return basic information
            
            authority_info = {
                'authority_type': self._determine_authority_type(authority_name),
                'sector': self._determine_sector(authority_name)
            }
            
            return authority_info
            
        except Exception as e:
            logger.warning(f"Error matching authority {authority_name}: {str(e)}")
            return None
    
    def _determine_authority_type(self, name: str) -> str:
        """Determine authority type from name"""
        
        name_lower = name.lower()
        
        if any(keyword in name_lower for keyword in ['primaria', 'municipiul', 'orasul']):
            return 'municipality'
        elif any(keyword in name_lower for keyword in ['consiliul', 'judet']):
            return 'county'
        elif any(keyword in name_lower for keyword in ['ministerul', 'guvernul']):
            return 'government'
        elif any(keyword in name_lower for keyword in ['spital', 'sanitar']):
            return 'healthcare'
        elif any(keyword in name_lower for keyword in ['scoala', 'universitate', 'educational']):
            return 'education'
        else:
            return 'other'
    
    def _determine_sector(self, name: str) -> str:
        """Determine sector from name"""
        
        name_lower = name.lower()
        
        if any(keyword in name_lower for keyword in ['sanatate', 'spital', 'medical']):
            return 'healthcare'
        elif any(keyword in name_lower for keyword in ['educatie', 'scoala', 'universitate']):
            return 'education'
        elif any(keyword in name_lower for keyword in ['transport', 'cai_ferate', 'drum']):
            return 'transport'
        elif any(keyword in name_lower for keyword in ['energie', 'electric', 'gaz']):
            return 'energy'
        elif any(keyword in name_lower for keyword in ['apa', 'canal', 'mediu']):
            return 'environment'
        else:
            return 'general'


class GeographicEnricher:
    """Geographic data enrichment service"""
    
    def __init__(self):
        self.geocoder = Nominatim(user_agent="romanian_procurement_platform")
    
    async def geocode_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Geocode address to coordinates"""
        
        try:
            # Add Romania to improve geocoding accuracy
            full_address = f"{address}, Romania"
            
            # Use asyncio to make geocoding non-blocking
            location = await asyncio.get_event_loop().run_in_executor(
                None, self._geocode_sync, full_address
            )
            
            if location:
                return {
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'formatted_address': location.address,
                    'county': self._extract_county(location.address),
                    'city': self._extract_city(location.address),
                    'region': self._extract_region(location.address)
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error geocoding address {address}: {str(e)}")
            return None
    
    def _geocode_sync(self, address: str):
        """Synchronous geocoding"""
        try:
            return self.geocoder.geocode(address, timeout=10)
        except GeocoderTimedOut:
            return None
    
    def _extract_county(self, address: str) -> Optional[str]:
        """Extract county from geocoded address"""
        
        # Romanian counties pattern
        county_pattern = r'Judetul\s+([A-Z][a-z]+)'
        match = re.search(county_pattern, address)
        
        if match:
            return match.group(1)
        
        return None
    
    def _extract_city(self, address: str) -> Optional[str]:
        """Extract city from geocoded address"""
        
        # Split address and find city
        parts = address.split(',')
        
        for part in parts:
            part = part.strip()
            if any(keyword in part.lower() for keyword in ['bucuresti', 'municipiul', 'orasul']):
                return part
        
        return None
    
    def _extract_region(self, address: str) -> Optional[str]:
        """Extract region from geocoded address"""
        
        # Romanian regions
        regions = {
            'Bucuresti': 'Bucuresti-Ilfov',
            'Ilfov': 'Bucuresti-Ilfov',
            'Cluj': 'Nord-Vest',
            'Timis': 'Vest',
            'Constanta': 'Sud-Est',
            'Brasov': 'Centru',
            'Iasi': 'Nord-Est',
            'Dolj': 'Sud-Vest Oltenia',
            'Galati': 'Sud-Est'
        }
        
        for county, region in regions.items():
            if county in address:
                return region
        
        return None