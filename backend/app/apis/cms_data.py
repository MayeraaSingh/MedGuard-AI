"""
MedGuard AI - CMS Data API Integration
Medicare provider enrollment, quality ratings, and hospital affiliations
"""

import logging
import os
from typing import Dict, Any, Optional, List
import requests
import csv
from io import StringIO
from datetime import datetime

logger = logging.getLogger(__name__)


class CMSDataAPI:
    """CMS (Centers for Medicare & Medicaid Services) data integration."""
    
    # CMS APIs
    NPPES_API_URL = "https://npiregistry.cms.hhs.gov/api/"
    CARE_COMPARE_URL = "https://data.cms.gov/provider-data/api/1/datastore/query/"
    
    def __init__(self):
        """Initialize CMS data API client."""
        logger.info("Initialized CMS Data API")
    
    def get_provider_enrollment(self, npi: str) -> Optional[Dict[str, Any]]:
        """
        Get Medicare provider enrollment data.
        
        Args:
            npi: National Provider Identifier
            
        Returns:
            Provider enrollment information
        """
        try:
            params = {
                'version': '2.1',
                'number': npi
            }
            
            response = requests.get(self.NPPES_API_URL, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('result_count', 0) > 0:
                result = data['results'][0]
                
                # Extract key enrollment data
                basic = result.get('basic', {})
                addresses = result.get('addresses', [])
                taxonomies = result.get('taxonomies', [])
                
                # Get primary address
                primary_address = None
                for addr in addresses:
                    if addr.get('address_purpose') == 'LOCATION':
                        primary_address = addr
                        break
                
                if not primary_address and addresses:
                    primary_address = addresses[0]
                
                # Get primary taxonomy
                primary_taxonomy = None
                for tax in taxonomies:
                    if tax.get('primary', False):
                        primary_taxonomy = tax
                        break
                
                if not primary_taxonomy and taxonomies:
                    primary_taxonomy = taxonomies[0]
                
                enrollment = {
                    'npi': result.get('number'),
                    'enumeration_date': result.get('enumeration_date'),
                    'last_updated': result.get('last_updated'),
                    'status': result.get('status', 'UNKNOWN'),
                    'name': f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip(),
                    'credential': basic.get('credential'),
                    'gender': basic.get('gender'),
                    'sole_proprietor': basic.get('sole_proprietor'),
                    'address': primary_address,
                    'taxonomy': primary_taxonomy,
                    'other_taxonomies': [t for t in taxonomies if t != primary_taxonomy],
                    'api': 'cms_nppes'
                }
                
                logger.info(f"Retrieved enrollment data for NPI: {npi}")
                return enrollment
            else:
                logger.warning(f"No enrollment data found for NPI: {npi}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"CMS API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Enrollment lookup error: {e}")
            return None
    
    def get_physician_compare_data(self, npi: str) -> Optional[Dict[str, Any]]:
        """
        Get Physician Compare quality data.
        
        Args:
            npi: National Provider Identifier
            
        Returns:
            Quality ratings and performance data
        """
        try:
            # CMS Physician Compare API
            # Note: This is a simplified version - actual API may require different endpoints
            
            # For demonstration, using mock data structure
            # In production, this would call actual CMS Physician Compare API
            
            logger.info(f"Physician Compare data lookup for NPI: {npi}")
            
            # Placeholder - actual implementation would fetch real data
            compare_data = {
                'npi': npi,
                'quality_measures': [],
                'patient_experience': None,
                'hospital_affiliations': [],
                'available': False,
                'api': 'cms_physician_compare'
            }
            
            return compare_data
            
        except Exception as e:
            logger.error(f"Physician Compare error: {e}")
            return None
    
    def get_hospital_affiliations(self, provider_name: str, city: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get hospital affiliations for a provider.
        
        Args:
            provider_name: Provider name
            city: Optional city to narrow search
            
        Returns:
            List of affiliated hospitals
        """
        try:
            # This would integrate with CMS Hospital Compare or other databases
            # For now, returning empty list
            
            logger.info(f"Hospital affiliation lookup for: {provider_name}")
            
            affiliations = []
            
            return affiliations
            
        except Exception as e:
            logger.error(f"Hospital affiliation error: {e}")
            return []
    
    def check_medicare_opt_out(self, npi: str) -> Dict[str, Any]:
        """
        Check if provider has opted out of Medicare.
        
        Args:
            npi: National Provider Identifier
            
        Returns:
            Opt-out status information
        """
        try:
            # CMS maintains an opt-out list
            # This would check against that list
            
            logger.info(f"Medicare opt-out check for NPI: {npi}")
            
            # Placeholder result
            opt_out = {
                'npi': npi,
                'opted_out': False,
                'opt_out_date': None,
                'opt_out_end_date': None,
                'api': 'cms_opt_out'
            }
            
            return opt_out
            
        except Exception as e:
            logger.error(f"Opt-out check error: {e}")
            return {
                'npi': npi,
                'opted_out': None,
                'error': str(e)
            }
    
    def get_quality_ratings(self, npi: str) -> Optional[Dict[str, Any]]:
        """
        Get provider quality ratings and metrics.
        
        Args:
            npi: National Provider Identifier
            
        Returns:
            Quality ratings and performance metrics
        """
        try:
            # Aggregate quality data from multiple sources
            enrollment = self.get_provider_enrollment(npi)
            compare = self.get_physician_compare_data(npi)
            
            if not enrollment:
                return None
            
            ratings = {
                'npi': npi,
                'enrollment_status': enrollment.get('status'),
                'years_enrolled': self._calculate_years_enrolled(enrollment.get('enumeration_date')),
                'quality_measures': compare.get('quality_measures', []) if compare else [],
                'patient_experience': compare.get('patient_experience') if compare else None,
                'hospital_affiliations': compare.get('hospital_affiliations', []) if compare else [],
                'has_quality_data': bool(compare and compare.get('quality_measures')),
                'api': 'cms_quality_composite'
            }
            
            logger.info(f"Retrieved quality ratings for NPI: {npi}")
            return ratings
            
        except Exception as e:
            logger.error(f"Quality ratings error: {e}")
            return None
    
    def _calculate_years_enrolled(self, enumeration_date: Optional[str]) -> Optional[float]:
        """Calculate years since enrollment."""
        if not enumeration_date:
            return None
        
        try:
            # Parse date (format: MM-DD-YYYY)
            enum_dt = datetime.strptime(enumeration_date, '%m-%d-%Y')
            years = (datetime.now() - enum_dt).days / 365.25
            return round(years, 1)
        except Exception:
            return None
    
    def validate_provider_cms(self, npi: str) -> Dict[str, Any]:
        """
        Comprehensive CMS validation for provider.
        
        Args:
            npi: National Provider Identifier
            
        Returns:
            Validation result with all CMS data
        """
        enrollment = self.get_provider_enrollment(npi)
        opt_out = self.check_medicare_opt_out(npi)
        quality = self.get_quality_ratings(npi)
        
        if not enrollment:
            return {
                'validated': False,
                'confidence': 0,
                'issues': ['No CMS enrollment data found'],
                'cms_data': None
            }
        
        issues = []
        
        # Check enrollment status
        if enrollment['status'] != 'A':  # Active
            issues.append(f"Enrollment status: {enrollment['status']}")
        
        # Check opt-out
        if opt_out.get('opted_out'):
            issues.append('Provider has opted out of Medicare')
        
        # Calculate confidence
        confidence = 100
        
        if issues:
            confidence = 70
        
        if not quality or not quality.get('has_quality_data'):
            confidence *= 0.9  # Slight reduction if no quality data
        
        return {
            'validated': len(issues) == 0,
            'confidence': round(confidence, 2),
            'issues': issues,
            'cms_data': {
                'enrollment': enrollment,
                'opt_out': opt_out,
                'quality': quality
            }
        }


# Singleton instance
_cms_api = None


def get_cms_api() -> CMSDataAPI:
    """Get or create CMS API instance."""
    global _cms_api
    
    if _cms_api is None:
        _cms_api = CMSDataAPI()
    
    return _cms_api
