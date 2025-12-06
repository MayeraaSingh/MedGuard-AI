"""
MedGuard AI - Validation Agent (Google ADK)
Phase 2: Core Agent Architecture

Validates provider data against authoritative sources using Google's Agent Development Kit.
Uses ADK's agent framework with tools for:
- NPI Registry API validation
- Phone number validation
- Address validation
- License validation
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
import re
import time

from google import genai
from google.genai import types


class ValidationAgentADK:
    """
    ADK-based validation agent that verifies provider data against external sources.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the validation agent with ADK.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.npi_api_url = "https://npiregistry.cms.hhs.gov/api/"
        self.timeout = self.config.get("timeout", 5)
        
        # Source confidence weights
        self.source_weights = {
            "npi_registry": 0.90,
            "google_maps": 0.70,
            "practice_website": 0.60,
            "hospital_directory": 0.85,
            "state_board": 0.95
        }
        
        # Define tools for the agent
        self.tools = self._create_tools()
    
    def _create_tools(self) -> List[types.Tool]:
        """
        Create ADK tools for validation operations.
        
        Returns:
            List of ADK tools
        """
        # Define tool functions
        def validate_npi_tool(npi: str) -> Dict[str, Any]:
            """Validate NPI number against NPI Registry."""
            return self._validate_npi_impl(npi)
        
        def validate_phone_tool(phone: str, state: str = None) -> Dict[str, Any]:
            """Validate phone number format and area code."""
            return self._validate_phone_impl(phone, state)
        
        def validate_address_tool(street: str, city: str, state: str, zip_code: str) -> Dict[str, Any]:
            """Validate address components."""
            return self._validate_address_impl({
                "street": street,
                "city": city,
                "state": state,
                "zip_code": zip_code
            })
        
        def validate_license_tool(license_number: str, state: str) -> Dict[str, Any]:
            """Validate medical license format."""
            return self._validate_license_impl(license_number, state)
        
        # Create ADK tools
        tools = [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="validate_npi",
                    description="Validate NPI number against the NPI Registry API",
                    parameters={
                        "type": "object",
                        "properties": {
                            "npi": {
                                "type": "string",
                                "description": "10-digit NPI number to validate"
                            }
                        },
                        "required": ["npi"]
                    }
                ),
                types.FunctionDeclaration(
                    name="validate_phone",
                    description="Validate phone number format and area code",
                    parameters={
                        "type": "object",
                        "properties": {
                            "phone": {
                                "type": "string",
                                "description": "Phone number to validate"
                            },
                            "state": {
                                "type": "string",
                                "description": "State code for area code validation"
                            }
                        },
                        "required": ["phone"]
                    }
                ),
                types.FunctionDeclaration(
                    name="validate_address",
                    description="Validate address components",
                    parameters={
                        "type": "object",
                        "properties": {
                            "street": {"type": "string", "description": "Street address"},
                            "city": {"type": "string", "description": "City name"},
                            "state": {"type": "string", "description": "State code"},
                            "zip_code": {"type": "string", "description": "ZIP code"}
                        },
                        "required": ["street", "city", "state", "zip_code"]
                    }
                ),
                types.FunctionDeclaration(
                    name="validate_license",
                    description="Validate medical license format",
                    parameters={
                        "type": "object",
                        "properties": {
                            "license_number": {
                                "type": "string",
                                "description": "Medical license number"
                            },
                            "state": {
                                "type": "string",
                                "description": "State that issued the license"
                            }
                        },
                        "required": ["license_number", "state"]
                    }
                )
            ])
        ]
        
        return tools
    
    def validate_provider(self, provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single provider using ADK tools.
        
        Args:
            provider_data: Provider information dictionary
            
        Returns:
            Validation result with evidence from all checks
        """
        validation_result = {
            "provider_id": provider_data.get("provider_id") or provider_data.get("npi"),
            "fields_validated": {},
            "source_evidence": [],
            "overall_confidence": 0.0,
            "flags": [],
            "status": "pending",
            "timestamp": datetime.now().isoformat()
        }
        
        # Validate NPI
        if provider_data.get("npi"):
            npi_result = self._validate_npi_impl(str(provider_data["npi"]))
            validation_result["fields_validated"]["npi"] = npi_result
            if npi_result.get("evidence"):
                validation_result["source_evidence"].extend(npi_result["evidence"])
            if not npi_result.get("valid"):
                validation_result["flags"].append(f"NPI validation failed: {npi_result.get('reason')}")
        
        # Validate phone
        if provider_data.get("phone"):
            phone_result = self._validate_phone_impl(
                str(provider_data["phone"]),
                provider_data.get("state")
            )
            validation_result["fields_validated"]["phone"] = phone_result
            if phone_result.get("evidence"):
                validation_result["source_evidence"].extend(phone_result["evidence"])
            if not phone_result.get("valid"):
                validation_result["flags"].append(f"Phone validation failed: {phone_result.get('reason')}")
        
        # Validate address
        if all(provider_data.get(k) for k in ["street_address", "city", "state", "zip_code"]):
            address_result = self._validate_address_impl({
                "street": provider_data["street_address"],
                "city": provider_data["city"],
                "state": provider_data["state"],
                "zip_code": str(provider_data["zip_code"])
            })
            validation_result["fields_validated"]["address"] = address_result
            if address_result.get("evidence"):
                validation_result["source_evidence"].extend(address_result["evidence"])
            if not address_result.get("valid"):
                validation_result["flags"].append(f"Address validation failed: {address_result.get('reason')}")
        
        # Validate license
        if provider_data.get("license_number") and provider_data.get("license_state"):
            license_result = self._validate_license_impl(
                str(provider_data["license_number"]),
                provider_data["license_state"]
            )
            validation_result["fields_validated"]["license"] = license_result
            if license_result.get("evidence"):
                validation_result["source_evidence"].extend(license_result["evidence"])
            if not license_result.get("valid"):
                validation_result["flags"].append(f"License validation failed: {license_result.get('reason')}")
        
        # Calculate overall confidence
        confidences = [
            result.get("confidence", 0.0)
            for result in validation_result["fields_validated"].values()
            if result.get("confidence") is not None
        ]
        
        if confidences:
            validation_result["overall_confidence"] = sum(confidences) / len(confidences)
        
        # Determine status
        if validation_result["overall_confidence"] >= 0.8:
            validation_result["status"] = "approved"
        elif validation_result["overall_confidence"] >= 0.6:
            validation_result["status"] = "needs_review"
        else:
            validation_result["status"] = "failed"
        
        return validation_result
    
    def _validate_npi_impl(self, npi: str) -> Dict[str, Any]:
        """
        Implementation of NPI validation.
        
        Args:
            npi: 10-digit NPI number
            
        Returns:
            Validation result with evidence
        """
        # Convert to string if needed
        if npi is not None:
            npi = str(npi)
        
        if not npi or len(npi) != 10:
            return {
                "valid": False,
                "confidence": 0.0,
                "reason": "Invalid NPI format",
                "evidence": []
            }
        
        # Check Luhn algorithm
        if not self._validate_npi_checksum(npi):
            return {
                "valid": False,
                "confidence": 0.0,
                "reason": "NPI checksum validation failed",
                "evidence": []
            }
        
        # Query NPI Registry API
        try:
            response = requests.get(
                self.npi_api_url,
                params={"number": npi, "version": "2.1"},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                result_count = data.get("result_count", 0)
                
                if result_count > 0:
                    provider_info = data["results"][0]
                    return {
                        "valid": True,
                        "confidence": self.source_weights["npi_registry"],
                        "normalized_value": npi,
                        "reason": "NPI verified with registry",
                        "evidence": [{
                            "field_name": "npi",
                            "source_name": "npi_registry",
                            "source_value": npi,
                            "source_confidence_weight": self.source_weights["npi_registry"],
                            "extraction_method": "api_lookup",
                            "timestamp": datetime.now().isoformat(),
                            "metadata": {
                                "provider_name": provider_info.get("basic", {}).get("name"),
                                "taxonomy": provider_info.get("taxonomies", [{}])[0].get("desc")
                            }
                        }]
                    }
                else:
                    return {
                        "valid": False,
                        "confidence": 0.0,
                        "reason": "NPI not found in registry",
                        "evidence": []
                    }
            else:
                return {
                    "valid": None,
                    "confidence": 0.0,
                    "reason": f"API error: {response.status_code}",
                    "evidence": []
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "valid": None,
                "confidence": 0.0,
                "reason": f"API request failed: {str(e)}",
                "evidence": []
            }
    
    def _validate_phone_impl(self, phone: str, state: str = None) -> Dict[str, Any]:
        """
        Implementation of phone validation.
        
        Args:
            phone: Phone number string
            state: State code for area code validation
            
        Returns:
            Validation result
        """
        # Convert to string if needed
        if phone is not None:
            phone = str(phone)
        
        if not phone:
            return {
                "valid": False,
                "confidence": 0.0,
                "normalized_value": None,
                "reason": "Phone number missing",
                "evidence": []
            }
        
        # Extract digits only
        phone_clean = re.sub(r'x\d+', '', phone)  # Remove extensions
        digits = re.sub(r'\D', '', phone_clean)
        
        # Check length
        if len(digits) == 11 and digits[0] == '1':
            digits = digits[1:]  # Remove country code
        
        if len(digits) != 10:
            return {
                "valid": False,
                "confidence": 0.3,
                "normalized_value": None,
                "reason": f"Invalid phone length: {len(digits)} digits",
                "evidence": []
            }
        
        # Check for invalid area codes
        area_code = digits[:3]
        invalid_area_codes = ['555', '999', '000']
        
        if area_code in invalid_area_codes:
            return {
                "valid": False,
                "confidence": 0.0,
                "normalized_value": None,
                "reason": f"Invalid area code: {area_code}",
                "evidence": []
            }
        
        # Normalize to (XXX) XXX-XXXX format
        normalized_phone = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        
        return {
            "valid": True,
            "confidence": 0.75,
            "normalized_value": normalized_phone,
            "reason": "Phone format valid",
            "evidence": [{
                "field_name": "phone",
                "source_name": "format_validation",
                "source_value": normalized_phone,
                "source_confidence_weight": 0.75,
                "extraction_method": "normalization",
                "timestamp": datetime.now().isoformat()
            }]
        }
    
    def _validate_address_impl(self, address: Dict[str, str]) -> Dict[str, Any]:
        """
        Implementation of address validation.
        
        Args:
            address: Dictionary with street, city, state, zip_code
            
        Returns:
            Validation result with normalized address
        """
        if not all([address.get("street"), address.get("city"), 
                    address.get("state"), address.get("zip_code")]):
            return {
                "valid": False,
                "confidence": 0.0,
                "normalized_value": None,
                "reason": "Incomplete address",
                "evidence": []
            }
        
        # Basic ZIP code validation
        zip_code = str(address["zip_code"])  # Convert to string
        if not re.match(r'^\d{5}(-\d{4})?$', zip_code):
            return {
                "valid": False,
                "confidence": 0.3,
                "normalized_value": None,
                "reason": "Invalid ZIP code format",
                "evidence": []
            }
        
        # Normalize address
        normalized_address = {
            "street": address["street"].strip().title(),
            "city": address["city"].strip().title(),
            "state": address["state"].strip().upper(),
            "zip_code": zip_code[:5]  # Use 5-digit ZIP
        }
        
        normalized_string = (
            f"{normalized_address['street']}, "
            f"{normalized_address['city']}, "
            f"{normalized_address['state']} {normalized_address['zip_code']}"
        )
        
        # TODO: Google Maps API validation in Phase 5
        return {
            "valid": True,
            "confidence": 0.60,  # Lower confidence without geocoding
            "normalized_value": normalized_string,
            "reason": "Address format valid, geocoding pending",
            "evidence": [{
                "field_name": "address",
                "source_name": "format_validation",
                "source_value": normalized_string,
                "source_confidence_weight": 0.60,
                "extraction_method": "normalization",
                "timestamp": datetime.now().isoformat()
            }]
        }
    
    def _validate_license_impl(self, license_number: str, state: str) -> Dict[str, Any]:
        """
        Implementation of license validation.
        
        Args:
            license_number: License number string
            state: State code
            
        Returns:
            Validation result
        """
        # Convert to string if needed
        if license_number is not None:
            license_number = str(license_number)
        
        if not license_number or not state:
            return {
                "valid": False,
                "confidence": 0.0,
                "reason": "License number or state missing",
                "evidence": []
            }
        
        # TODO: State board API lookup (Phase 5)
        # For now, basic format validation
        
        # Check if license has reasonable format (letters and/or numbers)
        if not re.match(r'^[A-Z0-9.\-]+$', license_number.upper()):
            return {
                "valid": False,
                "confidence": 0.0,
                "reason": "Invalid license format",
                "evidence": []
            }
        
        return {
            "valid": True,
            "confidence": 0.50,  # Low confidence without state board verification
            "normalized_value": license_number.upper(),
            "reason": "Format valid, but not verified with state board",
            "evidence": [{
                "field_name": "license",
                "source_name": "format_validation",
                "source_value": license_number.upper(),
                "source_confidence_weight": 0.50,
                "extraction_method": "normalization",
                "timestamp": datetime.now().isoformat()
            }]
        }
    
    def _validate_npi_checksum(self, npi: str) -> bool:
        """
        Validate NPI using Luhn algorithm.
        
        Args:
            npi: 10-digit NPI string
            
        Returns:
            True if checksum is valid
        """
        # Prefix with "80840" as per NPI standard
        digits = "80840" + npi
        
        # Luhn algorithm
        total = 0
        for i, digit in enumerate(reversed(digits)):
            n = int(digit)
            if i % 2 == 0:  # Even positions (from right)
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        
        return total % 10 == 0
    
    def validate_batch(self, providers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate multiple providers in batch.
        
        Args:
            providers: List of provider dictionaries
            
        Returns:
            List of validation results
        """
        results = []
        
        for i, provider in enumerate(providers, 1):
            print(f"Validating provider {i}/{len(providers)}: {provider.get('npi') or provider.get('provider_id')}")
            result = self.validate_provider(provider)
            results.append(result)
            
            # Rate limiting
            if i < len(providers):
                time.sleep(0.1)
        
        return results


if __name__ == "__main__":
    # Test the ADK validation agent
    agent = ValidationAgentADK()
    
    test_provider = {
        "provider_id": "9999123456",
        "npi": "9999123456",
        "phone": "(617) 555-1234",
        "street_address": "123 Main St",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02101",
        "license_number": "MD12345",
        "license_state": "MA"
    }
    
    result = agent.validate_provider(test_provider)
    print("\nValidation Result:")
    print(f"Status: {result['status']}")
    print(f"Confidence: {result['overall_confidence']:.3f}")
    print(f"Flags: {result['flags']}")
    print(f"Evidence count: {len(result['source_evidence'])}")
