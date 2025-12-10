"""
MedGuard AI - Phase 3 Test Script
Tests FastAPI backend endpoints

Validates:
1. API health check
2. File upload
3. Validation pipeline trigger
4. Job status tracking
5. Provider queries
6. Review queue
"""

import requests
import time
from pathlib import Path
import json


class Phase3Tester:
    """Tests Phase 3 FastAPI backend."""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"
        self.results = {
            "phase": "Phase 3 - Backend Skeleton",
            "tests": {}
        }
    
    def test_health_check(self):
        """Test health check endpoint."""
        print("\nTest 1: Health Check")
        print("-" * 70)
        
        try:
            response = requests.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ API is healthy")
                print(f"  Version: {data.get('version')}")
                self.results["tests"]["health_check"] = {"status": "PASSED"}
                return True
            else:
                print(f"  ✗ Health check failed: {response.status_code}")
                self.results["tests"]["health_check"] = {"status": "FAILED"}
                return False
                
        except Exception as e:
            print(f"  ✗ Health check error: {e}")
            self.results["tests"]["health_check"] = {"status": "FAILED", "error": str(e)}
            return False
    
    def test_file_upload(self):
        """Test file upload endpoint."""
        print("\nTest 2: File Upload")
        print("-" * 70)
        
        try:
            # Use existing test data
            csv_path = Path("data/samples/providers_synthetic.csv")
            
            if not csv_path.exists():
                print(f"  ✗ Test file not found: {csv_path}")
                self.results["tests"]["file_upload"] = {"status": "FAILED", "error": "Test file not found"}
                return False
            
            # Upload file
            with open(csv_path, 'rb') as f:
                files = {'file': ('test_providers.csv', f, 'text/csv')}
                response = requests.post(f"{self.api_url}/upload", files=files)
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ File uploaded: {data['filename']}")
                print(f"  File size: {data['file_size']} bytes")
                print(f"  Rows detected: {data.get('rows_detected', 'N/A')}")
                
                self.results["tests"]["file_upload"] = {
                    "status": "PASSED",
                    "filename": data['filename']
                }
                self.uploaded_filename = data['filename']
                return True
            else:
                print(f"  ✗ Upload failed: {response.status_code}")
                self.results["tests"]["file_upload"] = {"status": "FAILED"}
                return False
                
        except Exception as e:
            print(f"  ✗ Upload error: {e}")
            self.results["tests"]["file_upload"] = {"status": "FAILED", "error": str(e)}
            return False
    
    def test_validation_trigger(self):
        """Test validation pipeline trigger."""
        print("\nTest 3: Validation Pipeline Trigger")
        print("-" * 70)
        
        try:
            if not hasattr(self, 'uploaded_filename'):
                print("  ⚠ Skipping (no uploaded file)")
                self.results["tests"]["validation_trigger"] = {"status": "SKIPPED"}
                return True
            
            # Start validation
            payload = {
                "file_path": self.uploaded_filename,
                "batch_size": 5
            }
            
            response = requests.post(f"{self.api_url}/start-validation", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ Validation started")
                print(f"  Job ID: {data['job_id']}")
                print(f"  Status: {data['status']}")
                
                self.results["tests"]["validation_trigger"] = {
                    "status": "PASSED",
                    "job_id": data['job_id']
                }
                self.job_id = data['job_id']
                return True
            else:
                print(f"  ✗ Validation trigger failed: {response.status_code}")
                print(f"  Response: {response.text}")
                self.results["tests"]["validation_trigger"] = {"status": "FAILED"}
                return False
                
        except Exception as e:
            print(f"  ✗ Validation trigger error: {e}")
            self.results["tests"]["validation_trigger"] = {"status": "FAILED", "error": str(e)}
            return False
    
    def test_job_status(self):
        """Test job status tracking."""
        print("\nTest 4: Job Status Tracking")
        print("-" * 70)
        
        try:
            if not hasattr(self, 'job_id'):
                print("  ⚠ Skipping (no job started)")
                self.results["tests"]["job_status"] = {"status": "SKIPPED"}
                return True
            
            # Check status multiple times
            max_attempts = 30
            for i in range(max_attempts):
                response = requests.get(f"{self.api_url}/status/{self.job_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  Status: {data['status']} | Progress: {data['progress']:.1f}% | Processed: {data['providers_processed']}/{data['providers_total']}")
                    
                    if data['status'] == 'completed':
                        print(f"  ✓ Validation completed")
                        print(f"  Duration: {data.get('duration_seconds', 0):.2f}s")
                        
                        self.results["tests"]["job_status"] = {
                            "status": "PASSED",
                            "duration": data.get('duration_seconds', 0)
                        }
                        return True
                    elif data['status'] == 'failed':
                        print(f"  ✗ Validation failed: {data.get('error')}")
                        self.results["tests"]["job_status"] = {"status": "FAILED"}
                        return False
                    
                    time.sleep(1)
                else:
                    print(f"  ✗ Status check failed: {response.status_code}")
                    self.results["tests"]["job_status"] = {"status": "FAILED"}
                    return False
            
            print(f"  ⚠ Validation did not complete within {max_attempts} seconds")
            self.results["tests"]["job_status"] = {"status": "TIMEOUT"}
            return False
            
        except Exception as e:
            print(f"  ✗ Status check error: {e}")
            self.results["tests"]["job_status"] = {"status": "FAILED", "error": str(e)}
            return False
    
    def test_provider_endpoints(self):
        """Test provider query endpoints."""
        print("\nTest 5: Provider Endpoints")
        print("-" * 70)
        
        try:
            # List providers
            response = requests.get(f"{self.api_url}/providers?page=1&page_size=10")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ Provider list endpoint working")
                print(f"  Total providers: {data.get('total', 0)}")
                
                # Get system stats
                stats_response = requests.get(f"{self.api_url}/stats")
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    print(f"  ✓ Stats endpoint working")
                    print(f"  Average confidence: {stats.get('average_confidence', 0):.3f}")
                
                self.results["tests"]["provider_endpoints"] = {"status": "PASSED"}
                return True
            else:
                print(f"  ✗ Provider list failed: {response.status_code}")
                self.results["tests"]["provider_endpoints"] = {"status": "FAILED"}
                return False
                
        except Exception as e:
            print(f"  ✗ Provider endpoint error: {e}")
            self.results["tests"]["provider_endpoints"] = {"status": "FAILED", "error": str(e)}
            return False
    
    def test_review_queue(self):
        """Test review queue endpoint."""
        print("\nTest 6: Review Queue")
        print("-" * 70)
        
        try:
            response = requests.get(f"{self.api_url}/review-queue?limit=10")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ Review queue endpoint working")
                print(f"  Items in queue: {data.get('total_items', 0)}")
                
                self.results["tests"]["review_queue"] = {"status": "PASSED"}
                return True
            else:
                print(f"  ✗ Review queue failed: {response.status_code}")
                self.results["tests"]["review_queue"] = {"status": "FAILED"}
                return False
                
        except Exception as e:
            print(f"  ✗ Review queue error: {e}")
            self.results["tests"]["review_queue"] = {"status": "FAILED", "error": str(e)}
            return False
    
    def run_all_tests(self):
        """Run all tests."""
        print("=" * 70)
        print("MEDGUARD AI - PHASE 3 API TESTS")
        print("=" * 70)
        
        tests = [
            self.test_health_check,
            self.test_file_upload,
            self.test_validation_trigger,
            self.test_job_status,
            self.test_provider_endpoints,
            self.test_review_queue
        ]
        
        for test in tests:
            test()
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for t in self.results["tests"].values() if t["status"] == "PASSED")
        failed = sum(1 for t in self.results["tests"].values() if t["status"] == "FAILED")
        skipped = sum(1 for t in self.results["tests"].values() if t["status"] == "SKIPPED")
        
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        
        if failed == 0:
            print("\n✓ ALL TESTS PASSED")
            self.results["overall_status"] = "PASSED"
        else:
            print("\n✗ SOME TESTS FAILED")
            self.results["overall_status"] = "FAILED"
        
        # Save results
        results_path = Path("data/phase3_test_results.json")
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {results_path}")
        print("=" * 70)


if __name__ == "__main__":
    tester = Phase3Tester()
    tester.run_all_tests()
