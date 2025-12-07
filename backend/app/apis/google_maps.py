"""
MedGuard AI - Google Maps API Integration
Geocoding, address verification, and business validation
"""

import logging
import os
from typing import Dict, Any, Optional, Tuple
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GoogleMapsAPI:
    """Google Maps API integration for address and business validation."""
    
    BASE_URL = "https://maps.googleapis.com/maps/api"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Google Maps API client.
        
        Args:
            api_key: Google Maps API key (reads from env if not provided)
        """
        self.api_key = api_key or os.getenv('GOOGLE_MAPS_API_KEY')
        
        if not self.api_key:
            logger.warning("No Google Maps API key found. API calls will fail.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Initialized Google Maps API")
        
        # Simple in-memory cache to avoid redundant API calls
        self._cache = {}
        self._cache_duration = timedelta(hours=24)
    
    def geocode_address(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Geocode an address to get coordinates and formatted address.
        
        Args:
            address: Address string to geocode
            
        Returns:
            Dictionary with geocoding results or None if failed
        """
        if not self.enabled:
            logger.debug("Google Maps API disabled")
            return None
        
        # Check cache
        cache_key = f"geocode:{address}"
        if cache_key in self._cache:
            cached_result, cached_time = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_duration:
                logger.debug(f"Using cached geocode for: {address}")
                return cached_result
        
        try:
            url = f"{self.BASE_URL}/geocode/json"
            params = {
                'address': address,
                'key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                result = data['results'][0]
                
                geocoded = {
                    'formatted_address': result['formatted_address'],
                    'latitude': result['geometry']['location']['lat'],
                    'longitude': result['geometry']['location']['lng'],
                    'place_id': result['place_id'],
                    'location_type': result['geometry']['location_type'],
                    'address_components': self._parse_address_components(result['address_components']),
                    'confidence': self._calculate_geocode_confidence(result),
                    'api': 'google_maps'
                }
                
                # Cache result
                self._cache[cache_key] = (geocoded, datetime.now())
                
                logger.info(f"Geocoded address: {address[:50]}...")
                return geocoded
            else:
                logger.warning(f"Geocoding failed: {data['status']}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Geocoding API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None
    
    def _parse_address_components(self, components: list) -> Dict[str, str]:
        """Parse address components into structured format."""
        parsed = {
            'street_number': '',
            'route': '',
            'city': '',
            'state': '',
            'zip_code': '',
            'country': ''
        }
        
        type_mapping = {
            'street_number': 'street_number',
            'route': 'route',
            'locality': 'city',
            'administrative_area_level_1': 'state',
            'postal_code': 'zip_code',
            'country': 'country'
        }
        
        for component in components:
            for comp_type in component['types']:
                if comp_type in type_mapping:
                    field = type_mapping[comp_type]
                    parsed[field] = component.get('short_name', '')
        
        return parsed
    
    def _calculate_geocode_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score for geocoding result."""
        location_type = result['geometry']['location_type']
        
        # Confidence based on location type
        type_confidence = {
            'ROOFTOP': 100,
            'RANGE_INTERPOLATED': 85,
            'GEOMETRIC_CENTER': 70,
            'APPROXIMATE': 50
        }
        
        return type_confidence.get(location_type, 50)
    
    def verify_address(self, address: str, expected_components: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Verify address exists and matches expected components.
        
        Args:
            address: Address to verify
            expected_components: Optional dict with expected city, state, zip
            
        Returns:
            Verification result with confidence and issues
        """
        geocoded = self.geocode_address(address)
        
        if not geocoded:
            return {
                'verified': False,
                'confidence': 0,
                'issues': ['Could not geocode address'],
                'geocoded_address': None
            }
        
        issues = []
        
        # Check if address components match expectations
        if expected_components:
            components = geocoded['address_components']
            
            for key, expected_value in expected_components.items():
                actual_value = components.get(key, '')
                
                if expected_value and actual_value:
                    if expected_value.lower() != actual_value.lower():
                        issues.append(f"{key} mismatch: expected '{expected_value}', got '{actual_value}'")
        
        # Lower confidence if issues found
        confidence = geocoded['confidence']
        if issues:
            confidence *= 0.7
        
        return {
            'verified': len(issues) == 0,
            'confidence': round(confidence, 2),
            'issues': issues,
            'geocoded_address': geocoded['formatted_address'],
            'coordinates': {
                'lat': geocoded['latitude'],
                'lng': geocoded['longitude']
            },
            'components': geocoded['address_components']
        }
    
    def find_place(self, query: str, location: Optional[Tuple[float, float]] = None) -> Optional[Dict[str, Any]]:
        """
        Find a place (business) by name and optional location.
        
        Args:
            query: Business name or search query
            location: Optional (latitude, longitude) to bias search
            
        Returns:
            Place information or None if not found
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.BASE_URL}/place/findplacefromtext/json"
            params = {
                'input': query,
                'inputtype': 'textquery',
                'fields': 'place_id,name,formatted_address,geometry,rating,user_ratings_total,types,business_status',
                'key': self.api_key
            }
            
            if location:
                params['locationbias'] = f"circle:5000@{location[0]},{location[1]}"
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['candidates']:
                place = data['candidates'][0]
                
                result = {
                    'place_id': place.get('place_id'),
                    'name': place.get('name'),
                    'address': place.get('formatted_address'),
                    'latitude': place['geometry']['location']['lat'],
                    'longitude': place['geometry']['location']['lng'],
                    'rating': place.get('rating'),
                    'total_ratings': place.get('user_ratings_total', 0),
                    'types': place.get('types', []),
                    'business_status': place.get('business_status', 'UNKNOWN'),
                    'api': 'google_places'
                }
                
                logger.info(f"Found place: {place.get('name')}")
                return result
            else:
                logger.warning(f"Place not found: {query}")
                return None
                
        except Exception as e:
            logger.error(f"Place search error: {e}")
            return None
    
    def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a place.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            Detailed place information
        """
        if not self.enabled:
            return None
        
        try:
            url = f"{self.BASE_URL}/place/details/json"
            params = {
                'place_id': place_id,
                'fields': 'name,formatted_address,formatted_phone_number,website,opening_hours,rating,user_ratings_total,reviews,types,business_status',
                'key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK':
                result = data['result']
                
                details = {
                    'name': result.get('name'),
                    'address': result.get('formatted_address'),
                    'phone': result.get('formatted_phone_number'),
                    'website': result.get('website'),
                    'rating': result.get('rating'),
                    'total_ratings': result.get('user_ratings_total', 0),
                    'types': result.get('types', []),
                    'business_status': result.get('business_status', 'UNKNOWN'),
                    'opening_hours': result.get('opening_hours', {}),
                    'reviews': result.get('reviews', [])[:3],  # Top 3 reviews
                    'api': 'google_places_details'
                }
                
                logger.info(f"Got place details: {result.get('name')}")
                return details
            else:
                logger.warning(f"Place details not found: {place_id}")
                return None
                
        except Exception as e:
            logger.error(f"Place details error: {e}")
            return None
    
    def validate_practice_location(
        self,
        provider_name: str,
        address: str,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate provider practice location exists.
        
        Args:
            provider_name: Provider or practice name
            address: Practice address
            phone: Optional phone number
            
        Returns:
            Validation result with confidence
        """
        # First geocode the address
        geocoded = self.geocode_address(address)
        
        if not geocoded:
            return {
                'validated': False,
                'confidence': 0,
                'issues': ['Could not geocode address'],
                'business_found': False
            }
        
        # Search for business at this location
        location = (geocoded['latitude'], geocoded['longitude'])
        place = self.find_place(provider_name, location)
        
        issues = []
        business_found = place is not None
        
        if place:
            # Check if business is operational
            if place['business_status'] != 'OPERATIONAL':
                issues.append(f"Business status: {place['business_status']}")
            
            # Check if phone matches (if provided)
            if phone:
                place_details = self.get_place_details(place['place_id'])
                if place_details and place_details.get('phone'):
                    # Normalize and compare phones
                    normalized_phone = ''.join(filter(str.isdigit, phone))
                    normalized_place_phone = ''.join(filter(str.isdigit, place_details['phone']))
                    
                    if normalized_phone and normalized_place_phone:
                        if normalized_phone != normalized_place_phone:
                            issues.append('Phone number mismatch')
        else:
            issues.append('Business not found at this location')
        
        # Calculate confidence
        confidence = geocoded['confidence']
        if business_found:
            confidence = (confidence + 100) / 2  # Boost if business found
        else:
            confidence *= 0.5  # Reduce if not found
        
        if issues:
            confidence *= 0.8
        
        return {
            'validated': business_found and len(issues) == 0,
            'confidence': round(confidence, 2),
            'issues': issues,
            'business_found': business_found,
            'geocoded_address': geocoded['formatted_address'],
            'place_info': place,
            'coordinates': {
                'lat': geocoded['latitude'],
                'lng': geocoded['longitude']
            }
        }


# Singleton instance
_google_maps_api = None


def get_google_maps_api() -> GoogleMapsAPI:
    """Get or create Google Maps API instance."""
    global _google_maps_api
    
    if _google_maps_api is None:
        _google_maps_api = GoogleMapsAPI()
    
    return _google_maps_api
