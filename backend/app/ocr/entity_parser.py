"""
MedGuard AI - Entity Parser
Extract provider entities from OCR text using regex and fuzzy matching
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from fuzzywuzzy import fuzz, process

logger = logging.getLogger(__name__)


class EntityParser:
    """Parse provider entities from extracted text."""
    
    # Regex patterns for entity extraction
    PATTERNS = {
        'npi': [
            r'\b(?:NPI|National Provider Identifier)[:\s]+(\d{10})\b',
            r'\bNPI[:\s]*#?\s*(\d{10})\b',
            r'\b(\d{10})\b(?=.*(?:NPI|provider))',
        ],
        'phone': [
            r'\b(?:Phone|Tel|Telephone|Office)[:\s]*(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b',
            r'\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b',
            r'\((\d{3})\)\s*(\d{3})[-.\s]?(\d{4})',
        ],
        'email': [
            r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
        ],
        'zip_code': [
            r'\b(\d{5}(?:-\d{4})?)\b',
        ],
        'license': [
            r'\b(?:License|Lic)[:\s]*#?\s*([A-Z0-9]{5,15})\b',
            r'\b(?:Medical License|State License)[:\s]*([A-Z0-9]{5,15})\b',
        ],
        'ssn': [
            r'\b(\d{3}[-\s]?\d{2}[-\s]?\d{4})\b',
        ],
    }
    
    # Common medical specialties for fuzzy matching
    SPECIALTIES = [
        'Family Medicine', 'Internal Medicine', 'Pediatrics',
        'Obstetrics & Gynecology', 'Cardiology', 'Dermatology',
        'Orthopedic Surgery', 'Psychiatry', 'Radiology',
        'Emergency Medicine', 'Anesthesiology', 'Neurology',
        'Ophthalmology', 'Urology', 'Gastroenterology',
        'Endocrinology', 'Nephrology', 'Pulmonology',
        'Rheumatology', 'Oncology', 'Hematology',
        'Infectious Disease', 'Allergy & Immunology',
        'Physical Medicine & Rehabilitation', 'General Surgery'
    ]
    
    # Common degree suffixes
    DEGREES = ['MD', 'DO', 'NP', 'PA', 'DDS', 'DMD', 'PharmD', 'DPM', 'DC', 'OD']
    
    # US state abbreviations
    US_STATES = [
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
    ]
    
    def __init__(self, fuzzy_threshold: int = 80):
        """
        Initialize entity parser.
        
        Args:
            fuzzy_threshold: Minimum fuzzy match score (0-100)
        """
        self.fuzzy_threshold = fuzzy_threshold
        logger.info(f"Initialized EntityParser with fuzzy_threshold={fuzzy_threshold}")
    
    def parse_provider(self, text: str, confidence_map: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Parse provider information from text.
        
        Args:
            text: Extracted text from OCR
            confidence_map: Optional confidence scores for text regions
            
        Returns:
            Dictionary of extracted provider fields
        """
        provider = {
            'npi': self.extract_npi(text),
            'name': self.extract_name(text),
            'degree': self.extract_degree(text),
            'specialty': self.extract_specialty(text),
            'phone': self.extract_phone(text),
            'email': self.extract_email(text),
            'address': self.extract_address(text),
            'license': self.extract_license(text),
        }
        
        # Add confidence scores if available
        if confidence_map:
            for field, value in provider.items():
                if value and field in confidence_map:
                    value['ocr_confidence'] = confidence_map.get(field, 0)
        
        # Calculate overall extraction confidence
        extracted_fields = sum(1 for v in provider.values() if v and v.get('value'))
        provider['extraction_confidence'] = (extracted_fields / len(provider)) * 100
        
        logger.info(f"Parsed provider: {extracted_fields}/{len(provider)} fields extracted")
        return provider
    
    def extract_npi(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract NPI number."""
        for pattern in self.PATTERNS['npi']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                npi = matches[0]
                # Validate NPI length
                if len(npi) == 10 and npi.isdigit():
                    return {
                        'value': npi,
                        'confidence': 95,
                        'method': 'regex'
                    }
        
        return None
    
    def extract_name(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract provider name.
        Looks for patterns like "Dr. FirstName LastName" or "FirstName LastName, MD"
        """
        # Pattern 1: Dr. FirstName LastName
        pattern1 = r'(?:Dr\.|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)'
        matches = re.findall(pattern1, text)
        
        if matches:
            return {
                'value': matches[0].strip(),
                'confidence': 90,
                'method': 'regex_title'
            }
        
        # Pattern 2: FirstName LastName, MD/DO/etc
        pattern2 = r'([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+),?\s+(?:' + '|'.join(self.DEGREES) + r')\b'
        matches = re.findall(pattern2, text)
        
        if matches:
            return {
                'value': matches[0].strip(),
                'confidence': 85,
                'method': 'regex_degree'
            }
        
        # Pattern 3: Any capitalized name near "Name:" label
        pattern3 = r'(?:Name|Provider)[:\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)'
        matches = re.findall(pattern3, text, re.IGNORECASE)
        
        if matches:
            return {
                'value': matches[0].strip(),
                'confidence': 80,
                'method': 'regex_label'
            }
        
        return None
    
    def extract_degree(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract medical degree."""
        for degree in self.DEGREES:
            # Look for degree with word boundaries
            pattern = r'\b' + degree + r'\b'
            if re.search(pattern, text):
                return {
                    'value': degree,
                    'confidence': 95,
                    'method': 'exact_match'
                }
        
        return None
    
    def extract_specialty(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract specialty using fuzzy matching."""
        # First try exact match
        for specialty in self.SPECIALTIES:
            if specialty.lower() in text.lower():
                return {
                    'value': specialty,
                    'confidence': 100,
                    'method': 'exact_match'
                }
        
        # Try fuzzy matching on each line
        lines = text.split('\n')
        best_match = None
        best_score = 0
        
        for line in lines:
            line = line.strip()
            if len(line) < 5:  # Skip very short lines
                continue
            
            # Get best match from SPECIALTIES list
            match = process.extractOne(line, self.SPECIALTIES, scorer=fuzz.token_set_ratio)
            
            if match and match[1] > best_score and match[1] >= self.fuzzy_threshold:
                best_match = match[0]
                best_score = match[1]
        
        if best_match:
            return {
                'value': best_match,
                'confidence': best_score,
                'method': 'fuzzy_match'
            }
        
        return None
    
    def extract_phone(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract phone number."""
        for pattern in self.PATTERNS['phone']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Handle tuple matches from grouped patterns
                if isinstance(matches[0], tuple):
                    phone = ''.join(matches[0])
                else:
                    phone = matches[0]
                
                # Normalize phone number
                phone = re.sub(r'[^\d]', '', phone)
                
                if len(phone) == 10:
                    formatted = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
                    return {
                        'value': formatted,
                        'confidence': 90,
                        'method': 'regex'
                    }
        
        return None
    
    def extract_email(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract email address."""
        matches = re.findall(self.PATTERNS['email'][0], text, re.IGNORECASE)
        
        if matches:
            email = matches[0].lower()
            return {
                'value': email,
                'confidence': 95,
                'method': 'regex'
            }
        
        return None
    
    def extract_address(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract address components.
        Returns dict with street, city, state, zip.
        """
        address_parts = {
            'street': None,
            'city': None,
            'state': None,
            'zip': None
        }
        
        # Extract ZIP code first
        zip_matches = re.findall(self.PATTERNS['zip_code'][0], text)
        if zip_matches:
            address_parts['zip'] = zip_matches[0]
        
        # Extract state (2-letter abbreviation)
        for state in self.US_STATES:
            pattern = r'\b' + state + r'\b'
            if re.search(pattern, text):
                address_parts['state'] = state
                break
        
        # Extract street address (line with number + street name)
        street_pattern = r'(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way)\.?)'
        street_matches = re.findall(street_pattern, text, re.IGNORECASE)
        if street_matches:
            address_parts['street'] = street_matches[0].strip()
        
        # Extract city (word before state abbreviation)
        if address_parts['state']:
            city_pattern = r'([A-Za-z\s]+),?\s+' + address_parts['state']
            city_matches = re.findall(city_pattern, text)
            if city_matches:
                address_parts['city'] = city_matches[0].strip()
        
        # Calculate confidence based on completeness
        filled = sum(1 for v in address_parts.values() if v)
        confidence = (filled / 4) * 100
        
        if filled >= 2:  # At least 2 components found
            return {
                'value': address_parts,
                'confidence': confidence,
                'method': 'regex_composite'
            }
        
        return None
    
    def extract_license(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract medical license number."""
        for pattern in self.PATTERNS['license']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                license_num = matches[0].strip()
                return {
                    'value': license_num,
                    'confidence': 85,
                    'method': 'regex'
                }
        
        return None
    
    def validate_extracted_data(self, provider: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted data quality.
        
        Args:
            provider: Extracted provider dictionary
            
        Returns:
            Validation results with flags
        """
        issues = []
        warnings = []
        
        # Check NPI
        if not provider.get('npi'):
            issues.append('Missing NPI')
        elif provider['npi'].get('value'):
            npi = provider['npi']['value']
            if not self._validate_npi_checksum(npi):
                warnings.append('NPI checksum validation failed')
        
        # Check name
        if not provider.get('name'):
            issues.append('Missing provider name')
        
        # Check phone
        if provider.get('phone'):
            phone = provider['phone'].get('value', '')
            if '555' in phone:
                warnings.append('Phone contains 555 (likely fake)')
        
        # Check email
        if provider.get('email'):
            email = provider['email'].get('value', '')
            if 'test' in email or 'example' in email:
                warnings.append('Email appears to be test/example')
        
        # Overall quality assessment
        if len(issues) == 0 and len(warnings) <= 1:
            quality = 'high'
        elif len(issues) <= 1:
            quality = 'medium'
        else:
            quality = 'low'
        
        validation = {
            'quality': quality,
            'issues': issues,
            'warnings': warnings,
            'requires_review': len(issues) > 0 or len(warnings) > 1
        }
        
        logger.info(f"Validation: {quality} quality, {len(issues)} issues, {len(warnings)} warnings")
        return validation
    
    def _validate_npi_checksum(self, npi: str) -> bool:
        """Validate NPI using Luhn algorithm."""
        if len(npi) != 10 or not npi.isdigit():
            return False
        
        # Add prefix 80840 for Luhn algorithm
        full_number = '80840' + npi
        
        # Luhn algorithm
        total = 0
        for i, digit in enumerate(reversed(full_number)):
            n = int(digit)
            if i % 2 == 0:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        
        return total % 10 == 0
