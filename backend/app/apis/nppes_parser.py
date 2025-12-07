"""
MedGuard AI - NPPES Parser
Parse NPPES downloadable file for offline bulk validation
"""

import logging
import csv
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Iterator
import json

logger = logging.getLogger(__name__)


class NPPESParser:
    """
    Parser for NPPES National Provider Data file.
    
    The NPPES file is a large CSV containing all registered NPIs.
    Download from: https://download.cms.gov/nppes/NPI_Files.html
    """
    
    def __init__(self, nppes_file_path: Optional[str] = None):
        """
        Initialize NPPES parser.
        
        Args:
            nppes_file_path: Path to NPPES CSV or ZIP file
        """
        self.nppes_file_path = nppes_file_path
        
        if nppes_file_path:
            self.nppes_file_path = Path(nppes_file_path)
        
        # In-memory index for fast lookups (for smaller datasets)
        self._npi_index: Dict[str, Dict[str, Any]] = {}
        self._indexed = False
        
        logger.info("Initialized NPPES Parser")
    
    def extract_zip(self, zip_path: str, extract_to: Optional[str] = None) -> str:
        """
        Extract NPPES ZIP file.
        
        Args:
            zip_path: Path to ZIP file
            extract_to: Directory to extract to (default: same directory as ZIP)
            
        Returns:
            Path to extracted CSV file
        """
        zip_path = Path(zip_path)
        
        if not extract_to:
            extract_to = zip_path.parent
        else:
            extract_to = Path(extract_to)
            extract_to.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Find CSV file in ZIP
                csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
                
                if not csv_files:
                    raise ValueError("No CSV file found in ZIP")
                
                csv_file = csv_files[0]
                zip_ref.extract(csv_file, extract_to)
                
                extracted_path = extract_to / csv_file
                logger.info(f"Extracted NPPES file to: {extracted_path}")
                
                return str(extracted_path)
                
        except Exception as e:
            logger.error(f"ZIP extraction error: {e}")
            raise
    
    def parse_line(self, row: Dict[str, str]) -> Dict[str, Any]:
        """
        Parse a single NPPES CSV row.
        
        Args:
            row: CSV row as dictionary
            
        Returns:
            Parsed provider data
        """
        # NPPES CSV has many columns - extract key fields
        provider = {
            'npi': row.get('NPI'),
            'entity_type': row.get('Entity Type Code'),  # 1=Individual, 2=Organization
            'replacement_npi': row.get('Replacement NPI'),
            'ein': row.get('Employer Identification Number (EIN)'),
            'org_name': row.get('Provider Organization Name (Legal Business Name)'),
            'last_name': row.get('Provider Last Name (Legal Name)'),
            'first_name': row.get('Provider First Name'),
            'middle_name': row.get('Provider Middle Name'),
            'prefix': row.get('Provider Name Prefix Text'),
            'suffix': row.get('Provider Name Suffix Text'),
            'credential': row.get('Provider Credential Text'),
            'address_line1': row.get('Provider First Line Business Mailing Address'),
            'address_line2': row.get('Provider Second Line Business Mailing Address'),
            'city': row.get('Provider Business Mailing Address City Name'),
            'state': row.get('Provider Business Mailing Address State Name'),
            'zip_code': row.get('Provider Business Mailing Address Postal Code'),
            'country': row.get('Provider Business Mailing Address Country Code (If outside U.S.)'),
            'phone': row.get('Provider Business Mailing Address Telephone Number'),
            'fax': row.get('Provider Business Mailing Address Fax Number'),
            'practice_address_line1': row.get('Provider First Line Business Practice Location Address'),
            'practice_address_line2': row.get('Provider Second Line Business Practice Location Address'),
            'practice_city': row.get('Provider Business Practice Location Address City Name'),
            'practice_state': row.get('Provider Business Practice Location Address State Name'),
            'practice_zip_code': row.get('Provider Business Practice Location Address Postal Code'),
            'practice_phone': row.get('Provider Business Practice Location Address Telephone Number'),
            'enumeration_date': row.get('Provider Enumeration Date'),
            'last_update_date': row.get('Last Update Date'),
            'npi_deactivation_date': row.get('NPI Deactivation Date'),
            'npi_reactivation_date': row.get('NPI Reactivation Date'),
            'gender': row.get('Provider Gender Code'),
            'taxonomy_code_1': row.get('Healthcare Provider Taxonomy Code_1'),
            'taxonomy_license_1': row.get('Provider License Number_1'),
            'taxonomy_state_1': row.get('Provider License Number State Code_1'),
            'is_sole_proprietor': row.get('Is Sole Proprietor'),
            'is_organization_subpart': row.get('Is Organization Subpart'),
            'parent_org_ein': row.get('Parent Organization LBN'),
            'authorized_official_last_name': row.get('Authorized Official Last Name'),
            'authorized_official_first_name': row.get('Authorized Official First Name'),
            'authorized_official_title': row.get('Authorized Official Title or Position'),
            'authorized_official_phone': row.get('Authorized Official Telephone Number')
        }
        
        # Clean empty strings
        provider = {k: v if v else None for k, v in provider.items()}
        
        return provider
    
    def iter_providers(self, csv_path: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        """
        Iterate through providers in NPPES file.
        
        Args:
            csv_path: Path to NPPES CSV (uses init path if not provided)
            
        Yields:
            Provider dictionaries
        """
        if csv_path:
            file_path = Path(csv_path)
        elif self.nppes_file_path:
            file_path = self.nppes_file_path
        else:
            raise ValueError("No NPPES file path provided")
        
        if not file_path.exists():
            raise FileNotFoundError(f"NPPES file not found: {file_path}")
        
        logger.info(f"Reading NPPES file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                
                for i, row in enumerate(reader):
                    if i % 100000 == 0 and i > 0:
                        logger.info(f"Processed {i:,} providers")
                    
                    provider = self.parse_line(row)
                    yield provider
                    
        except Exception as e:
            logger.error(f"NPPES parsing error: {e}")
            raise
    
    def build_index(self, csv_path: Optional[str] = None, max_records: Optional[int] = None):
        """
        Build in-memory index of NPIs.
        
        Warning: Full NPPES file has millions of records - use max_records for testing.
        
        Args:
            csv_path: Path to NPPES CSV
            max_records: Maximum records to index (None = all)
        """
        logger.info("Building NPI index...")
        
        count = 0
        for provider in self.iter_providers(csv_path):
            npi = provider.get('npi')
            if npi:
                self._npi_index[npi] = provider
                count += 1
                
                if max_records and count >= max_records:
                    break
        
        self._indexed = True
        logger.info(f"Indexed {count:,} NPIs")
    
    def lookup_npi(self, npi: str) -> Optional[Dict[str, Any]]:
        """
        Lookup provider by NPI from index.
        
        Args:
            npi: National Provider Identifier
            
        Returns:
            Provider data or None if not found
        """
        if not self._indexed:
            logger.warning("NPI index not built. Call build_index() first.")
            return None
        
        return self._npi_index.get(npi)
    
    def search_by_name(
        self,
        last_name: str,
        first_name: Optional[str] = None,
        state: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search providers by name (requires index).
        
        Args:
            last_name: Provider last name
            first_name: Optional first name
            state: Optional state filter
            
        Returns:
            List of matching providers
        """
        if not self._indexed:
            logger.warning("NPI index not built. Call build_index() first.")
            return []
        
        results = []
        
        for provider in self._npi_index.values():
            # Match last name
            if provider.get('last_name', '').lower() != last_name.lower():
                continue
            
            # Match first name if provided
            if first_name:
                if provider.get('first_name', '').lower() != first_name.lower():
                    continue
            
            # Match state if provided
            if state:
                if provider.get('state', '').upper() != state.upper():
                    continue
            
            results.append(provider)
        
        logger.info(f"Found {len(results)} providers matching: {last_name}, {first_name}, {state}")
        return results
    
    def export_subset(self, output_path: str, filter_func: callable, max_records: Optional[int] = None):
        """
        Export subset of NPPES data to JSON.
        
        Args:
            output_path: Output JSON file path
            filter_func: Function that takes provider dict and returns True to include
            max_records: Maximum records to process
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        providers = []
        count = 0
        
        for provider in self.iter_providers():
            if filter_func(provider):
                providers.append(provider)
            
            count += 1
            if max_records and count >= max_records:
                break
        
        with open(output_path, 'w') as f:
            json.dump(providers, f, indent=2, default=str)
        
        logger.info(f"Exported {len(providers)} providers to: {output_path}")
    
    def get_statistics(self, csv_path: Optional[str] = None, sample_size: int = 10000) -> Dict[str, Any]:
        """
        Get statistics from NPPES file.
        
        Args:
            csv_path: Path to NPPES CSV
            sample_size: Number of records to sample
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'total_records': 0,
            'entity_types': {'1': 0, '2': 0},  # Individual vs Organization
            'states': {},
            'taxonomies': {},
            'with_deactivation': 0,
            'sole_proprietors': 0
        }
        
        for i, provider in enumerate(self.iter_providers(csv_path)):
            if i >= sample_size:
                break
            
            stats['total_records'] += 1
            
            # Entity type
            entity_type = provider.get('entity_type')
            if entity_type in stats['entity_types']:
                stats['entity_types'][entity_type] += 1
            
            # State
            state = provider.get('state')
            if state:
                stats['states'][state] = stats['states'].get(state, 0) + 1
            
            # Taxonomy
            taxonomy = provider.get('taxonomy_code_1')
            if taxonomy:
                stats['taxonomies'][taxonomy] = stats['taxonomies'][taxonomy].get(taxonomy, 0) + 1
            
            # Deactivation
            if provider.get('npi_deactivation_date'):
                stats['with_deactivation'] += 1
            
            # Sole proprietor
            if provider.get('is_sole_proprietor') == 'Y':
                stats['sole_proprietors'] += 1
        
        logger.info(f"Computed statistics from {stats['total_records']} records")
        return stats


# Singleton instance
_nppes_parser = None


def get_nppes_parser(nppes_file_path: Optional[str] = None) -> NPPESParser:
    """Get or create NPPES parser instance."""
    global _nppes_parser
    
    if _nppes_parser is None:
        _nppes_parser = NPPESParser(nppes_file_path)
    
    return _nppes_parser
