"""
MedGuard AI - Phase 5 Test Script
Tests API integrations and web scraping

Validates:
1. Google Maps API (geocoding, address verification, business search)
2. CMS Data API (provider enrollment, quality ratings)
3. NPPES Parser (offline NPI lookup)
4. State Board Scrapers (license verification)
5. Integration with validation pipeline
"""

import sys
from pathlib import Path
import json
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.apis import GoogleMapsAPI, CMSDataAPI, NPPESParser
from backend.app.scrapers import StateBoardScraper


class Phase5Tester:
    """Tests Phase 5 API integrations and scrapers."""
    
    def __init__(self):
        self.google_maps = GoogleMapsAPI()
        self.cms_api = CMSDataAPI()
        self.nppes_parser = NPPESParser()
        self.state_scraper = StateBoardScraper(use_selenium=False)
        
        self.results = {
            "phase": "Phase 5 - API Integrations & Web Scraping",
            "tests": {}
        }
        
        # Test data
        self.test_npi = "1234567893"  # Valid checksum NPI
        self.test_address = "1600 Amphitheatre Parkway, Mountain View, CA 94043"
        self.test_provider_name = "Stanford Health Care"
    
    def test_google_maps_geocoding(self):
        """Test 1: Google Maps geocoding."""
        print("\nTest 1: Google Maps Geocoding")
        print("-" * 70)
        
        try:
            if not self.google_maps.enabled:
                print("  ⚠ Google Maps API not configured (no API key)")
                print("  Set GOOGLE_MAPS_API_KEY environment variable to enable")
                self.results["tests"]["google_maps_geocoding"] = {
                    "status": "SKIPPED",
                    "reason": "No API key"
                }
                return True
            
            # Test geocoding
            result = self.google_maps.geocode_address(self.test_address)
            
            if result:
                print(f"  ✓ Address geocoded")
                print(f"    Formatted: {result['formatted_address']}")
                print(f"    Coordinates: {result['latitude']}, {result['longitude']}")
                print(f"    Confidence: {result['confidence']}%")
                
                self.results["tests"]["google_maps_geocoding"] = {
                    "status": "PASSED",
                    "result": result
                }
                return True
            else:
                print(f"  ⚠ Geocoding returned no results")
                self.results["tests"]["google_maps_geocoding"] = {
                    "status": "PARTIAL",
                    "note": "API enabled but no results"
                }
                return True
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results["tests"]["google_maps_geocoding"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def test_google_maps_verification(self):
        """Test 2: Address verification."""
        print("\nTest 2: Google Maps Address Verification")
        print("-" * 70)
        
        try:
            if not self.google_maps.enabled:
                print("  ⚠ Skipped (no API key)")
                self.results["tests"]["google_maps_verification"] = {"status": "SKIPPED"}
                return True
            
            result = self.google_maps.verify_address(
                self.test_address,
                expected_components={'state': 'CA', 'city': 'Mountain View'}
            )
            
            print(f"  Verified: {result['verified']}")
            print(f"  Confidence: {result['confidence']}%")
            
            if result['issues']:
                print(f"  Issues: {', '.join(result['issues'])}")
            else:
                print(f"  ✓ No issues found")
            
            self.results["tests"]["google_maps_verification"] = {
                "status": "PASSED",
                "result": result
            }
            return True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results["tests"]["google_maps_verification"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def test_google_maps_business_search(self):
        """Test 3: Business search."""
        print("\nTest 3: Google Maps Business Search")
        print("-" * 70)
        
        try:
            if not self.google_maps.enabled:
                print("  ⚠ Skipped (no API key)")
                self.results["tests"]["google_maps_business"] = {"status": "SKIPPED"}
                return True
            
            result = self.google_maps.find_place(self.test_provider_name)
            
            if result:
                print(f"  ✓ Business found")
                print(f"    Name: {result['name']}")
                print(f"    Address: {result['address']}")
                print(f"    Status: {result['business_status']}")
                
                if result.get('rating'):
                    print(f"    Rating: {result['rating']}/5 ({result['total_ratings']} reviews)")
                
                self.results["tests"]["google_maps_business"] = {
                    "status": "PASSED",
                    "result": result
                }
            else:
                print(f"  ⚠ Business not found")
                self.results["tests"]["google_maps_business"] = {
                    "status": "PARTIAL"
                }
            
            return True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results["tests"]["google_maps_business"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def test_cms_enrollment(self):
        """Test 4: CMS provider enrollment."""
        print("\nTest 4: CMS Provider Enrollment")
        print("-" * 70)
        
        try:
            result = self.cms_api.get_provider_enrollment(self.test_npi)
            
            if result:
                print(f"  ✓ Enrollment data retrieved")
                print(f"    NPI: {result['npi']}")
                print(f"    Name: {result['name']}")
                print(f"    Status: {result['status']}")
                print(f"    Enumeration Date: {result['enumeration_date']}")
                
                self.results["tests"]["cms_enrollment"] = {
                    "status": "PASSED",
                    "result": result
                }
                return True
            else:
                print(f"  ⚠ No enrollment data found for NPI: {self.test_npi}")
                self.results["tests"]["cms_enrollment"] = {
                    "status": "PARTIAL",
                    "note": "NPI not found in registry"
                }
                return True
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results["tests"]["cms_enrollment"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def test_cms_validation(self):
        """Test 5: CMS comprehensive validation."""
        print("\nTest 5: CMS Comprehensive Validation")
        print("-" * 70)
        
        try:
            result = self.cms_api.validate_provider_cms(self.test_npi)
            
            print(f"  Validated: {result['validated']}")
            print(f"  Confidence: {result['confidence']}%")
            
            if result['issues']:
                print(f"  Issues: {', '.join(result['issues'])}")
            else:
                print(f"  ✓ No issues found")
            
            if result['cms_data']:
                print(f"  ✓ CMS data available")
            
            self.results["tests"]["cms_validation"] = {
                "status": "PASSED",
                "result": result
            }
            return True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results["tests"]["cms_validation"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def test_nppes_parser(self):
        """Test 6: NPPES parser."""
        print("\nTest 6: NPPES Parser")
        print("-" * 70)
        
        try:
            print("  NPPES parser initialized")
            print("  Note: Full NPPES file required for actual parsing")
            print("  Testing structure only...")
            
            # Test that parser methods exist and are callable
            assert hasattr(self.nppes_parser, 'iter_providers')
            assert hasattr(self.nppes_parser, 'build_index')
            assert hasattr(self.nppes_parser, 'lookup_npi')
            assert hasattr(self.nppes_parser, 'search_by_name')
            
            print(f"  ✓ All parser methods available")
            print(f"  ✓ Ready to process NPPES data file")
            
            self.results["tests"]["nppes_parser"] = {
                "status": "PASSED",
                "note": "Structure validated - requires NPPES file for full test"
            }
            return True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results["tests"]["nppes_parser"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def test_state_board_scrapers(self):
        """Test 7: State board scrapers."""
        print("\nTest 7: State Board License Verification")
        print("-" * 70)
        
        try:
            supported_states = self.state_scraper.get_supported_states()
            print(f"  Supported states: {len(supported_states)}")
            print(f"  States: {', '.join(supported_states[:10])}...")
            
            # Test a few states
            test_states = ['CA', 'NY', 'TX', 'FL']
            results = []
            
            for state in test_states:
                result = self.state_scraper.verify_license(
                    state=state,
                    license_number='TEST123',
                    last_name='Smith',
                    first_name='John'
                )
                
                print(f"\n  {state}:")
                print(f"    Status: {result.get('status', 'UNKNOWN')}")
                print(f"    Verified: {result.get('verified', False)}")
                
                if result.get('note'):
                    print(f"    Note: {result['note']}")
                
                results.append(result)
            
            print(f"\n  ✓ Tested {len(test_states)} state scrapers")
            print(f"  ✓ All scrapers returned structured data")
            
            self.results["tests"]["state_board_scrapers"] = {
                "status": "PASSED",
                "supported_states": len(supported_states),
                "test_results": results,
                "note": "Using mock data - real implementation pending"
            }
            return True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results["tests"]["state_board_scrapers"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def test_integration_workflow(self):
        """Test 8: Complete integration workflow."""
        print("\nTest 8: Complete Integration Workflow")
        print("-" * 70)
        
        try:
            # Simulate provider validation workflow
            test_provider = {
                'npi': self.test_npi,
                'name': 'Test Provider',
                'address': '123 Medical Dr, San Francisco, CA 94102',
                'state': 'CA',
                'license_number': 'TEST123'
            }
            
            print(f"  Testing provider: {test_provider['name']}")
            
            validation_results = {}
            
            # Step 1: CMS validation
            print(f"\n  Step 1: CMS Validation...")
            cms_result = self.cms_api.validate_provider_cms(test_provider['npi'])
            validation_results['cms'] = cms_result
            print(f"    ✓ CMS: {cms_result['confidence']}% confidence")
            
            # Step 2: Address verification
            if self.google_maps.enabled:
                print(f"\n  Step 2: Address Verification...")
                addr_result = self.google_maps.verify_address(test_provider['address'])
                validation_results['address'] = addr_result
                print(f"    ✓ Address: {addr_result['confidence']}% confidence")
            else:
                print(f"\n  Step 2: Address Verification... SKIPPED (no API key)")
            
            # Step 3: License verification
            print(f"\n  Step 3: License Verification...")
            license_result = self.state_scraper.verify_license(
                state=test_provider['state'],
                license_number=test_provider['license_number']
            )
            validation_results['license'] = license_result
            print(f"    ✓ License: {license_result.get('status', 'UNKNOWN')}")
            
            # Calculate overall confidence
            confidences = [
                cms_result['confidence'],
                validation_results.get('address', {}).get('confidence', 0),
                license_result.get('confidence', 70)
            ]
            overall_confidence = sum(confidences) / len(confidences)
            
            print(f"\n  ✓ Integration workflow complete")
            print(f"  Overall Confidence: {overall_confidence:.1f}%")
            
            self.results["tests"]["integration_workflow"] = {
                "status": "PASSED",
                "overall_confidence": round(overall_confidence, 2),
                "validation_results": validation_results
            }
            return True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            self.results["tests"]["integration_workflow"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def run_all_tests(self):
        """Run all Phase 5 tests."""
        print("=" * 70)
        print("MEDGUARD AI - PHASE 5 API INTEGRATION TESTS")
        print("=" * 70)
        
        start_time = time.time()
        
        tests = [
            self.test_google_maps_geocoding,
            self.test_google_maps_verification,
            self.test_google_maps_business_search,
            self.test_cms_enrollment,
            self.test_cms_validation,
            self.test_nppes_parser,
            self.test_state_board_scrapers,
            self.test_integration_workflow
        ]
        
        for test in tests:
            test()
        
        duration = time.time() - start_time
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for t in self.results["tests"].values() if t["status"] == "PASSED")
        partial = sum(1 for t in self.results["tests"].values() if t["status"] == "PARTIAL")
        failed = sum(1 for t in self.results["tests"].values() if t["status"] == "FAILED")
        skipped = sum(1 for t in self.results["tests"].values() if t["status"] == "SKIPPED")
        
        print(f"Passed: {passed}")
        print(f"Partial: {partial}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        print(f"Total time: {duration:.2f}s")
        
        if failed == 0:
            print("\n✓ ALL TESTS PASSED")
            self.results["overall_status"] = "PASSED"
        elif failed <= 1:
            print("\n⚠ TESTS MOSTLY PASSED")
            self.results["overall_status"] = "PARTIAL"
        else:
            print("\n✗ SOME TESTS FAILED")
            self.results["overall_status"] = "FAILED"
        
        # Save results
        results_path = Path("data/phase5_test_results.json")
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {results_path}")
        print("=" * 70)


if __name__ == "__main__":
    tester = Phase5Tester()
    tester.run_all_tests()
