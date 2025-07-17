"""
Data validation and transformation pipeline for Romanian procurement data
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal, InvalidOperation
import json
from dataclasses import dataclass

from app.core.logging import logger
from app.services.scrapers.utils import TextCleaner, DataValidator as BaseDataValidator


@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    cleaned_data: Dict[str, Any]


class TenderDataValidator:
    """Comprehensive validator for tender data"""
    
    def __init__(self):
        self.required_fields = {
            'title': str,
            'source_system': str,
            'external_id': str,
            'contracting_authority': str
        }
        
        self.optional_fields = {
            'description': str,
            'estimated_value': (float, Decimal),
            'currency': str,
            'tender_type': str,
            'procedure_type': str,
            'status': str,
            'cpv_code': str,
            'publication_date': datetime,
            'submission_deadline': datetime,
            'opening_date': datetime,
            'contract_start_date': datetime,
            'contract_end_date': datetime
        }
        
        self.valid_currencies = ['RON', 'EUR', 'USD']
        self.valid_statuses = ['active', 'closed', 'cancelled', 'awarded', 'suspended', 'unknown']
        self.valid_sources = ['SICAP', 'ANRMAP', 'EU_TED', 'MUNICIPALITY']
        
        # Romanian tender types
        self.valid_tender_types = [
            'bunuri', 'servicii', 'lucrari', 'contract-cadru',
            'acord-cadru', 'sistem-dinamic', 'concesiune'
        ]
        
        # Romanian procedure types
        self.valid_procedure_types = [
            'licitatie-deschisa', 'licitatie-restransa', 'dialog-competitiv',
            'negociere-cu-publicarea', 'negociere-fara-publicarea',
            'concurs-de-solutii', 'partenariat-inovatie'
        ]
    
    def validate_tender(self, raw_data: Dict[str, Any]) -> ValidationResult:
        """Validate and clean tender data"""
        
        errors = []
        warnings = []
        cleaned_data = {}
        
        try:
            # Validate required fields
            for field, field_type in self.required_fields.items():
                if field not in raw_data or not raw_data[field]:
                    errors.append(f"Missing required field: {field}")
                    continue
                
                cleaned_value = self._clean_and_validate_field(
                    raw_data[field], field_type, field
                )
                
                if cleaned_value is None:
                    errors.append(f"Invalid value for required field {field}: {raw_data[field]}")
                else:
                    cleaned_data[field] = cleaned_value
            
            # Validate optional fields
            for field, field_type in self.optional_fields.items():
                if field in raw_data and raw_data[field] is not None:
                    cleaned_value = self._clean_and_validate_field(
                        raw_data[field], field_type, field
                    )
                    
                    if cleaned_value is not None:
                        cleaned_data[field] = cleaned_value
                    else:
                        warnings.append(f"Invalid value for optional field {field}: {raw_data[field]}")
            
            # Perform business rule validation
            business_validation = self._validate_business_rules(cleaned_data)
            errors.extend(business_validation['errors'])
            warnings.extend(business_validation['warnings'])
            
            # Update cleaned data with business rule corrections
            cleaned_data.update(business_validation['corrections'])
            
            # Add metadata
            cleaned_data['validated_at'] = datetime.now()
            cleaned_data['validation_version'] = '1.0'
            
            is_valid = len(errors) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                cleaned_data=cleaned_data
            )
            
        except Exception as e:
            logger.error(f"Error validating tender data: {str(e)}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                cleaned_data={}
            )
    
    def _clean_and_validate_field(
        self, 
        value: Any, 
        field_type: Union[type, tuple], 
        field_name: str
    ) -> Any:
        """Clean and validate a single field"""
        
        if value is None:
            return None
        
        try:
            # Handle tuple types (multiple allowed types)
            if isinstance(field_type, tuple):
                for single_type in field_type:
                    try:
                        return self._convert_to_type(value, single_type, field_name)
                    except:
                        continue
                return None
            else:
                return self._convert_to_type(value, field_type, field_name)
                
        except Exception as e:
            logger.warning(f"Error cleaning field {field_name}: {str(e)}")
            return None
    
    def _convert_to_type(self, value: Any, target_type: type, field_name: str) -> Any:
        """Convert value to target type with field-specific logic"""
        
        if target_type == str:
            return self._clean_string_field(str(value), field_name)
        
        elif target_type == float:
            return self._clean_numeric_field(value, field_name)
        
        elif target_type == Decimal:
            return self._clean_decimal_field(value, field_name)
        
        elif target_type == datetime:
            return self._clean_date_field(value, field_name)
        
        else:
            return target_type(value)
    
    def _clean_string_field(self, value: str, field_name: str) -> str:
        """Clean string field with field-specific logic"""
        
        # Basic cleaning
        cleaned = TextCleaner.clean_text(value)
        
        if not cleaned:
            return cleaned
        
        # Field-specific cleaning
        if field_name == 'title':
            # Remove excessive capitalization
            if cleaned.isupper() and len(cleaned) > 10:
                cleaned = cleaned.title()
            
            # Limit length
            if len(cleaned) > 500:
                cleaned = cleaned[:497] + "..."
        
        elif field_name == 'description':
            # Limit length
            if len(cleaned) > 10000:
                cleaned = cleaned[:9997] + "..."
        
        elif field_name == 'currency':
            cleaned = cleaned.upper()
            if cleaned not in self.valid_currencies:
                # Try to map common variations
                currency_mapping = {
                    'LEI': 'RON',
                    'EURO': 'EUR',
                    'DOLLARS': 'USD',
                    'DOLARI': 'USD'
                }
                cleaned = currency_mapping.get(cleaned, 'RON')
        
        elif field_name == 'status':
            cleaned = cleaned.lower()
            if cleaned not in self.valid_statuses:
                # Try to map Romanian status terms
                status_mapping = {
                    'activ': 'active',
                    'deschis': 'active',
                    'inchis': 'closed',
                    'expirat': 'closed',
                    'anulat': 'cancelled',
                    'adjudecat': 'awarded',
                    'suspendat': 'suspended',
                    'necunoscut': 'unknown'
                }
                cleaned = status_mapping.get(cleaned, 'unknown')
        
        elif field_name == 'source_system':
            cleaned = cleaned.upper()
            if cleaned not in self.valid_sources:
                # Try to map variations
                source_mapping = {
                    'SICAP': 'SICAP',
                    'ANRMAP': 'ANRMAP',
                    'TED': 'EU_TED',
                    'PRIMARIE': 'MUNICIPALITY',
                    'MUNICIPALITY': 'MUNICIPALITY'
                }
                cleaned = source_mapping.get(cleaned, cleaned)
        
        elif field_name == 'cpv_code':
            # Validate CPV code format
            cleaned = re.sub(r'[^\d-]', '', cleaned)
            if not re.match(r'^\d{8}(-\d)?$', cleaned):
                return None
        
        return cleaned
    
    def _clean_numeric_field(self, value: Any, field_name: str) -> Optional[float]:
        """Clean numeric field"""
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # Extract numeric value from string
            numeric_value = TextCleaner.extract_currency_amount(value)
            if numeric_value is not None:
                return float(numeric_value)
        
        return None
    
    def _clean_decimal_field(self, value: Any, field_name: str) -> Optional[Decimal]:
        """Clean decimal field"""
        
        if isinstance(value, Decimal):
            return value
        
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        
        if isinstance(value, str):
            # Extract numeric value from string
            numeric_value = TextCleaner.extract_currency_amount(value)
            if numeric_value is not None:
                try:
                    return Decimal(str(numeric_value))
                except InvalidOperation:
                    return None
        
        return None
    
    def _clean_date_field(self, value: Any, field_name: str) -> Optional[datetime]:
        """Clean date field"""
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            return TextCleaner.extract_date(value)
        
        return None
    
    def _validate_business_rules(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate business rules and return corrections"""
        
        errors = []
        warnings = []
        corrections = {}
        
        try:
            # Date validation
            if 'publication_date' in data and 'submission_deadline' in data:
                if data['publication_date'] and data['submission_deadline']:
                    if data['submission_deadline'] <= data['publication_date']:
                        warnings.append("Submission deadline is before or same as publication date")
            
            # Value validation
            if 'estimated_value' in data and data['estimated_value']:
                if data['estimated_value'] < 0:
                    errors.append("Estimated value cannot be negative")
                elif data['estimated_value'] > 1000000000:  # 1 billion
                    warnings.append("Estimated value seems unusually high")
            
            # Currency validation
            if 'currency' in data and data['currency']:
                if data['currency'] not in self.valid_currencies:
                    warnings.append(f"Unusual currency: {data['currency']}")
            
            # Status validation for dates
            if 'status' in data and data['status'] == 'active':
                if 'submission_deadline' in data and data['submission_deadline']:
                    if data['submission_deadline'] < datetime.now():
                        corrections['status'] = 'closed'
                        warnings.append("Status changed from active to closed due to past deadline")
            
            # CPV code validation
            if 'cpv_code' in data and data['cpv_code']:
                if not self._is_valid_cpv_code(data['cpv_code']):
                    warnings.append(f"Invalid CPV code format: {data['cpv_code']}")
            
            # Authority validation
            if 'contracting_authority' in data and data['contracting_authority']:
                authority_name = data['contracting_authority']
                if len(authority_name) < 3:
                    warnings.append("Contracting authority name is very short")
                elif len(authority_name) > 255:
                    corrections['contracting_authority'] = authority_name[:255]
                    warnings.append("Contracting authority name truncated")
            
            # Title validation
            if 'title' in data and data['title']:
                title = data['title']
                if len(title) < 10:
                    warnings.append("Title is very short")
                
                # Check for suspicious patterns
                if title.count('X') > len(title) * 0.3:
                    warnings.append("Title contains many 'X' characters (might be placeholder)")
            
            return {
                'errors': errors,
                'warnings': warnings,
                'corrections': corrections
            }
            
        except Exception as e:
            logger.error(f"Error in business rules validation: {str(e)}")
            return {
                'errors': [f"Business validation error: {str(e)}"],
                'warnings': [],
                'corrections': {}
            }
    
    def _is_valid_cpv_code(self, cpv_code: str) -> bool:
        """Validate CPV code format"""
        
        # CPV codes are 8 digits optionally followed by a dash and more digits
        pattern = r'^\d{8}(-\d+)?$'
        return bool(re.match(pattern, cpv_code))


class CompanyDataValidator:
    """Validator for company data"""
    
    def __init__(self):
        self.required_fields = {
            'name': str,
            'cui': str
        }
        
        self.optional_fields = {
            'registration_number': str,
            'address': str,
            'county': str,
            'city': str,
            'contact_email': str,
            'contact_phone': str,
            'company_type': str,
            'company_size': str
        }
    
    def validate_company(self, raw_data: Dict[str, Any]) -> ValidationResult:
        """Validate company data"""
        
        errors = []
        warnings = []
        cleaned_data = {}
        
        try:
            # Validate required fields
            for field, field_type in self.required_fields.items():
                if field not in raw_data or not raw_data[field]:
                    errors.append(f"Missing required field: {field}")
                    continue
                
                if field == 'cui':
                    cui_valid, cui_cleaned = self._validate_cui(raw_data[field])
                    if not cui_valid:
                        errors.append(f"Invalid CUI: {raw_data[field]}")
                    else:
                        cleaned_data[field] = cui_cleaned
                else:
                    cleaned_data[field] = TextCleaner.clean_text(str(raw_data[field]))
            
            # Validate optional fields
            for field, field_type in self.optional_fields.items():
                if field in raw_data and raw_data[field]:
                    if field == 'contact_email':
                        if BaseDataValidator.validate_email(raw_data[field]):
                            cleaned_data[field] = raw_data[field].lower()
                        else:
                            warnings.append(f"Invalid email format: {raw_data[field]}")
                    else:
                        cleaned_data[field] = TextCleaner.clean_text(str(raw_data[field]))
            
            is_valid = len(errors) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                cleaned_data=cleaned_data
            )
            
        except Exception as e:
            logger.error(f"Error validating company data: {str(e)}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                cleaned_data={}
            )
    
    def _validate_cui(self, cui: str) -> tuple[bool, str]:
        """Validate Romanian CUI"""
        
        try:
            # Clean CUI
            cui_cleaned = re.sub(r'[^\d]', '', cui)
            
            if not cui_cleaned:
                return False, cui
            
            # Check length
            if len(cui_cleaned) < 2 or len(cui_cleaned) > 10:
                return False, cui
            
            # Basic validation (simplified)
            if not cui_cleaned.isdigit():
                return False, cui
            
            return True, cui_cleaned
            
        except Exception as e:
            logger.warning(f"Error validating CUI {cui}: {str(e)}")
            return False, cui


class BidDataValidator:
    """Validator for bid data"""
    
    def __init__(self):
        self.required_fields = {
            'tender_id': str,
            'company_id': str,
            'bid_amount': (float, Decimal),
            'currency': str,
            'status': str
        }
        
        self.valid_statuses = ['submitted', 'accepted', 'rejected', 'winner']
        self.valid_currencies = ['RON', 'EUR', 'USD']
    
    def validate_bid(self, raw_data: Dict[str, Any]) -> ValidationResult:
        """Validate bid data"""
        
        errors = []
        warnings = []
        cleaned_data = {}
        
        try:
            # Validate bid amount
            if 'bid_amount' in raw_data:
                if isinstance(raw_data['bid_amount'], str):
                    amount = TextCleaner.extract_currency_amount(raw_data['bid_amount'])
                    if amount is not None:
                        cleaned_data['bid_amount'] = amount
                    else:
                        errors.append("Invalid bid amount format")
                else:
                    cleaned_data['bid_amount'] = float(raw_data['bid_amount'])
            
            # Validate currency
            if 'currency' in raw_data:
                currency = raw_data['currency'].upper()
                if currency in self.valid_currencies:
                    cleaned_data['currency'] = currency
                else:
                    warnings.append(f"Unknown currency: {currency}")
                    cleaned_data['currency'] = 'RON'  # Default to RON
            
            # Validate status
            if 'status' in raw_data:
                status = raw_data['status'].lower()
                if status in self.valid_statuses:
                    cleaned_data['status'] = status
                else:
                    warnings.append(f"Unknown bid status: {status}")
                    cleaned_data['status'] = 'submitted'  # Default status
            
            # Copy other fields
            for field in ['tender_id', 'company_id', 'bid_date', 'execution_period_days']:
                if field in raw_data:
                    cleaned_data[field] = raw_data[field]
            
            is_valid = len(errors) == 0
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                cleaned_data=cleaned_data
            )
            
        except Exception as e:
            logger.error(f"Error validating bid data: {str(e)}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                cleaned_data={}
            )


class DataTransformationPipeline:
    """Complete data transformation pipeline"""
    
    def __init__(self):
        self.tender_validator = TenderDataValidator()
        self.company_validator = CompanyDataValidator()
        self.bid_validator = BidDataValidator()
    
    def transform_tender_data(self, raw_data: Dict[str, Any]) -> ValidationResult:
        """Transform raw tender data into validated format"""
        
        logger.info(f"Transforming tender data: {raw_data.get('external_id', 'unknown')}")
        
        # Validate tender data
        result = self.tender_validator.validate_tender(raw_data)
        
        if result.is_valid:
            logger.info(f"Tender data validated successfully: {result.cleaned_data.get('external_id')}")
        else:
            logger.warning(f"Tender data validation failed: {result.errors}")
        
        return result
    
    def transform_company_data(self, raw_data: Dict[str, Any]) -> ValidationResult:
        """Transform raw company data into validated format"""
        
        logger.info(f"Transforming company data: {raw_data.get('name', 'unknown')}")
        
        result = self.company_validator.validate_company(raw_data)
        
        if result.is_valid:
            logger.info(f"Company data validated successfully: {result.cleaned_data.get('name')}")
        else:
            logger.warning(f"Company data validation failed: {result.errors}")
        
        return result
    
    def transform_bid_data(self, raw_data: Dict[str, Any]) -> ValidationResult:
        """Transform raw bid data into validated format"""
        
        logger.info(f"Transforming bid data for tender: {raw_data.get('tender_id', 'unknown')}")
        
        result = self.bid_validator.validate_bid(raw_data)
        
        if result.is_valid:
            logger.info(f"Bid data validated successfully")
        else:
            logger.warning(f"Bid data validation failed: {result.errors}")
        
        return result
    
    def transform_batch(self, raw_data_list: List[Dict[str, Any]], data_type: str) -> List[ValidationResult]:
        """Transform batch of data"""
        
        logger.info(f"Transforming batch of {len(raw_data_list)} {data_type} items")
        
        results = []
        
        for raw_data in raw_data_list:
            try:
                if data_type == 'tender':
                    result = self.transform_tender_data(raw_data)
                elif data_type == 'company':
                    result = self.transform_company_data(raw_data)
                elif data_type == 'bid':
                    result = self.transform_bid_data(raw_data)
                else:
                    logger.error(f"Unknown data type: {data_type}")
                    continue
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error transforming {data_type} data: {str(e)}")
                results.append(ValidationResult(
                    is_valid=False,
                    errors=[f"Transformation error: {str(e)}"],
                    warnings=[],
                    cleaned_data={}
                ))
        
        valid_count = sum(1 for r in results if r.is_valid)
        logger.info(f"Batch transformation completed: {valid_count}/{len(results)} valid")
        
        return results