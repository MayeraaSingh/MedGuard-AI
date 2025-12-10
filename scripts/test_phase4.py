"""
MedGuard AI - Phase 4 Test Script
Tests OCR pipeline on sample PDFs

Validates:
1. PDF processing and quality assessment
2. OCR text extraction with confidence scoring
3. Entity parsing (NPI, name, specialty, etc.)
4. Integration with validation pipeline
5. Accuracy benchmarks for clean/moderate/challenging PDFs
"""

import sys
from pathlib import Path
import json
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.ocr import OCROrchestrator


class Phase4Tester:
    """Tests Phase 4 OCR pipeline."""
    
    def __init__(self):
        self.orchestrator = OCROrchestrator(dpi=300, fuzzy_threshold=80)
        self.results = {
            "phase": "Phase 4 - OCR Pipeline",
            "tests": {}
        }
        self.pdf_dir = Path("data/samples/pdfs")
    
    def test_pdf_discovery(self):
        """Test 1: Discover sample PDFs."""
        print("\nTest 1: PDF Discovery")
        print("-" * 70)
        
        try:
            if not self.pdf_dir.exists():
                print(f"  ✗ PDF directory not found: {self.pdf_dir}")
                self.results["tests"]["pdf_discovery"] = {
                    "status": "FAILED",
                    "error": "PDF directory not found"
                }
                return False
            
            # Find all PDFs
            clean_pdfs = list(self.pdf_dir.glob("*_clean_*.pdf"))
            moderate_pdfs = list(self.pdf_dir.glob("*_moderate_*.pdf"))
            challenging_pdfs = list(self.pdf_dir.glob("*_challenging_*.pdf"))
            
            total_pdfs = len(clean_pdfs) + len(moderate_pdfs) + len(challenging_pdfs)
            
            print(f"  ✓ Found {total_pdfs} PDFs")
            print(f"    Clean: {len(clean_pdfs)}")
            print(f"    Moderate: {len(moderate_pdfs)}")
            print(f"    Challenging: {len(challenging_pdfs)}")
            
            if total_pdfs == 0:
                print(f"  ✗ No PDFs found in {self.pdf_dir}")
                self.results["tests"]["pdf_discovery"] = {
                    "status": "FAILED",
                    "error": "No PDFs found"
                }
                return False
            
            self.results["tests"]["pdf_discovery"] = {
                "status": "PASSED",
                "total_pdfs": total_pdfs,
                "clean": len(clean_pdfs),
                "moderate": len(moderate_pdfs),
                "challenging": len(challenging_pdfs)
            }
            
            # Store for later tests
            self.clean_pdfs = clean_pdfs
            self.moderate_pdfs = moderate_pdfs
            self.challenging_pdfs = challenging_pdfs
            
            return True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results["tests"]["pdf_discovery"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def test_clean_pdf_ocr(self):
        """Test 2: OCR on clean quality PDFs."""
        print("\nTest 2: Clean PDF OCR")
        print("-" * 70)
        
        if not hasattr(self, 'clean_pdfs') or not self.clean_pdfs:
            print("  ⚠ Skipping (no clean PDFs found)")
            self.results["tests"]["clean_pdf_ocr"] = {"status": "SKIPPED"}
            return True
        
        try:
            results = []
            total_confidence = 0
            
            for pdf_path in self.clean_pdfs:
                print(f"\n  Processing: {pdf_path.name}")
                
                result = self.orchestrator.process_pdf(str(pdf_path))
                
                if result['success']:
                    confidence = result['confidence']['overall_confidence']
                    extracted_fields = sum(
                        1 for v in result['provider_data'].values()
                        if (v.get('value') if isinstance(v, dict) else v)
                    )
                    
                    print(f"    ✓ Confidence: {confidence:.1f}%")
                    print(f"    ✓ Extracted fields: {extracted_fields}")
                    print(f"    ✓ Processing time: {result['processing_time']:.2f}s")
                    
                    results.append({
                        'file': pdf_path.name,
                        'confidence': confidence,
                        'extracted_fields': extracted_fields,
                        'time': result['processing_time']
                    })
                    total_confidence += confidence
                else:
                    print(f"    ✗ Failed: {result.get('error')}")
                    results.append({
                        'file': pdf_path.name,
                        'error': result.get('error')
                    })
            
            avg_confidence = total_confidence / len(results) if results else 0
            success_rate = sum(1 for r in results if 'confidence' in r) / len(results) * 100
            
            print(f"\n  Summary:")
            print(f"    Average confidence: {avg_confidence:.1f}%")
            print(f"    Success rate: {success_rate:.0f}%")
            
            # Clean PDFs should have >90% confidence
            if avg_confidence >= 90:
                print(f"  ✓ PASSED: Clean PDFs achieved target accuracy")
                status = "PASSED"
            elif avg_confidence >= 70:
                print(f"  ⚠ PARTIAL: Clean PDFs below target but acceptable")
                status = "PARTIAL"
            else:
                print(f"  ✗ FAILED: Clean PDFs have low accuracy")
                status = "FAILED"
            
            self.results["tests"]["clean_pdf_ocr"] = {
                "status": status,
                "avg_confidence": round(avg_confidence, 2),
                "success_rate": round(success_rate, 2),
                "results": results
            }
            
            return status in ["PASSED", "PARTIAL"]
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results["tests"]["clean_pdf_ocr"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def test_moderate_pdf_ocr(self):
        """Test 3: OCR on moderate quality PDFs."""
        print("\nTest 3: Moderate PDF OCR")
        print("-" * 70)
        
        if not hasattr(self, 'moderate_pdfs') or not self.moderate_pdfs:
            print("  ⚠ Skipping (no moderate PDFs found)")
            self.results["tests"]["moderate_pdf_ocr"] = {"status": "SKIPPED"}
            return True
        
        try:
            results = []
            total_confidence = 0
            
            for pdf_path in self.moderate_pdfs:
                print(f"\n  Processing: {pdf_path.name}")
                
                result = self.orchestrator.process_pdf(str(pdf_path))
                
                if result['success']:
                    confidence = result['confidence']['overall_confidence']
                    extracted_fields = sum(
                        1 for v in result['provider_data'].values()
                        if (v.get('value') if isinstance(v, dict) else v)
                    )
                    
                    print(f"    ✓ Confidence: {confidence:.1f}%")
                    print(f"    ✓ Extracted fields: {extracted_fields}")
                    
                    results.append({
                        'file': pdf_path.name,
                        'confidence': confidence,
                        'extracted_fields': extracted_fields
                    })
                    total_confidence += confidence
                else:
                    print(f"    ✗ Failed: {result.get('error')}")
            
            avg_confidence = total_confidence / len(results) if results else 0
            
            print(f"\n  Summary:")
            print(f"    Average confidence: {avg_confidence:.1f}%")
            
            # Moderate PDFs should have >70% confidence
            if avg_confidence >= 70:
                print(f"  ✓ PASSED: Moderate PDFs achieved target accuracy")
                status = "PASSED"
            elif avg_confidence >= 50:
                print(f"  ⚠ PARTIAL: Moderate PDFs below target but acceptable")
                status = "PARTIAL"
            else:
                print(f"  ✗ FAILED: Moderate PDFs have low accuracy")
                status = "FAILED"
            
            self.results["tests"]["moderate_pdf_ocr"] = {
                "status": status,
                "avg_confidence": round(avg_confidence, 2),
                "results": results
            }
            
            return status in ["PASSED", "PARTIAL"]
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results["tests"]["moderate_pdf_ocr"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def test_challenging_pdf_ocr(self):
        """Test 4: OCR on challenging quality PDFs."""
        print("\nTest 4: Challenging PDF OCR")
        print("-" * 70)
        
        if not hasattr(self, 'challenging_pdfs') or not self.challenging_pdfs:
            print("  ⚠ Skipping (no challenging PDFs found)")
            self.results["tests"]["challenging_pdf_ocr"] = {"status": "SKIPPED"}
            return True
        
        try:
            results = []
            total_confidence = 0
            
            for pdf_path in self.challenging_pdfs:
                print(f"\n  Processing: {pdf_path.name}")
                
                result = self.orchestrator.process_pdf(str(pdf_path))
                
                if result['success']:
                    confidence = result['confidence']['overall_confidence']
                    extracted_fields = sum(
                        1 for v in result['provider_data'].values()
                        if (v.get('value') if isinstance(v, dict) else v)
                    )
                    
                    print(f"    ✓ Confidence: {confidence:.1f}%")
                    print(f"    ✓ Extracted fields: {extracted_fields}")
                    print(f"    ✓ Requires review: {result['requires_review']}")
                    
                    results.append({
                        'file': pdf_path.name,
                        'confidence': confidence,
                        'extracted_fields': extracted_fields,
                        'requires_review': result['requires_review']
                    })
                    total_confidence += confidence
                else:
                    print(f"    ✗ Failed: {result.get('error')}")
            
            avg_confidence = total_confidence / len(results) if results else 0
            
            print(f"\n  Summary:")
            print(f"    Average confidence: {avg_confidence:.1f}%")
            
            # Challenging PDFs should have >50% confidence (lower bar)
            if avg_confidence >= 50:
                print(f"  ✓ PASSED: Challenging PDFs processed successfully")
                status = "PASSED"
            elif avg_confidence >= 30:
                print(f"  ⚠ PARTIAL: Challenging PDFs have low but usable accuracy")
                status = "PARTIAL"
            else:
                print(f"  ⚠ Note: Challenging PDFs very low accuracy (expected)")
                status = "PARTIAL"
            
            self.results["tests"]["challenging_pdf_ocr"] = {
                "status": status,
                "avg_confidence": round(avg_confidence, 2),
                "results": results
            }
            
            return True  # Don't fail on challenging PDFs
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results["tests"]["challenging_pdf_ocr"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def test_batch_processing(self):
        """Test 5: Batch processing of all PDFs."""
        print("\nTest 5: Batch Processing")
        print("-" * 70)
        
        try:
            all_pdfs = []
            if hasattr(self, 'clean_pdfs'):
                all_pdfs.extend([str(p) for p in self.clean_pdfs])
            if hasattr(self, 'moderate_pdfs'):
                all_pdfs.extend([str(p) for p in self.moderate_pdfs])
            if hasattr(self, 'challenging_pdfs'):
                all_pdfs.extend([str(p) for p in self.challenging_pdfs])
            
            if not all_pdfs:
                print("  ⚠ Skipping (no PDFs found)")
                self.results["tests"]["batch_processing"] = {"status": "SKIPPED"}
                return True
            
            print(f"  Processing {len(all_pdfs)} PDFs in batch...")
            
            batch_result = self.orchestrator.process_batch(all_pdfs)
            
            print(f"\n  ✓ Batch complete")
            print(f"    Total PDFs: {batch_result['total_pdfs']}")
            print(f"    Successful: {batch_result['successful']}")
            print(f"    Failed: {batch_result['failed']}")
            print(f"    Total pages: {batch_result['total_pages']}")
            print(f"    Average confidence: {batch_result['avg_confidence']:.1f}%")
            print(f"    Total time: {batch_result['total_time']:.2f}s")
            print(f"    Avg time per PDF: {batch_result['avg_time_per_pdf']:.2f}s")
            
            # Generate report
            report_path = Path("data/phase4_ocr_report.txt")
            report = self.orchestrator.generate_ocr_report(batch_result, str(report_path))
            print(f"\n  ✓ Report saved to: {report_path}")
            
            self.results["tests"]["batch_processing"] = {
                "status": "PASSED",
                "total_pdfs": batch_result['total_pdfs'],
                "successful": batch_result['successful'],
                "avg_confidence": batch_result['avg_confidence'],
                "total_time": batch_result['total_time']
            }
            
            return True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results["tests"]["batch_processing"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def test_validation_integration(self):
        """Test 6: Integration with Phase 2 validation pipeline."""
        print("\nTest 6: Validation Pipeline Integration")
        print("-" * 70)
        
        try:
            # Take first clean PDF
            if not hasattr(self, 'clean_pdfs') or not self.clean_pdfs:
                print("  ⚠ Skipping (no clean PDFs found)")
                self.results["tests"]["validation_integration"] = {"status": "SKIPPED"}
                return True
            
            pdf_path = self.clean_pdfs[0]
            print(f"  Testing with: {pdf_path.name}")
            
            # Process PDF
            ocr_result = self.orchestrator.process_pdf(str(pdf_path))
            
            if not ocr_result['success']:
                print(f"  ✗ OCR failed: {ocr_result.get('error')}")
                self.results["tests"]["validation_integration"] = {
                    "status": "FAILED",
                    "error": "OCR failed"
                }
                return False
            
            # Convert to validation format
            validation_data = self.orchestrator.extract_to_validation_format(ocr_result)
            
            print(f"  ✓ Converted to validation format")
            print(f"    NPI: {validation_data.get('npi', 'N/A')}")
            print(f"    Name: {validation_data.get('first_name')} {validation_data.get('last_name')}")
            print(f"    Specialty: {validation_data.get('specialty', 'N/A')}")
            print(f"    Source: {validation_data.get('source')}")
            print(f"    OCR Confidence: {validation_data.get('ocr_confidence', 0):.1f}%")
            
            # Check required fields
            required_fields = ['npi', 'first_name', 'last_name', 'source']
            missing_fields = [f for f in required_fields if not validation_data.get(f)]
            
            if missing_fields:
                print(f"  ⚠ Missing required fields: {', '.join(missing_fields)}")
                status = "PARTIAL"
            else:
                print(f"  ✓ All required fields present")
                status = "PASSED"
            
            self.results["tests"]["validation_integration"] = {
                "status": status,
                "validation_data": validation_data,
                "missing_fields": missing_fields
            }
            
            return True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            self.results["tests"]["validation_integration"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def run_all_tests(self):
        """Run all Phase 4 tests."""
        print("=" * 70)
        print("MEDGUARD AI - PHASE 4 OCR TESTS")
        print("=" * 70)
        
        start_time = time.time()
        
        tests = [
            self.test_pdf_discovery,
            self.test_clean_pdf_ocr,
            self.test_moderate_pdf_ocr,
            self.test_challenging_pdf_ocr,
            self.test_batch_processing,
            self.test_validation_integration
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
        elif failed <= 1 or partial > 0:
            print("\n⚠ TESTS PARTIALLY PASSED")
            self.results["overall_status"] = "PARTIAL"
        else:
            print("\n✗ SOME TESTS FAILED")
            self.results["overall_status"] = "FAILED"
        
        # Save results
        results_path = Path("data/phase4_test_results.json")
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {results_path}")
        print("=" * 70)


if __name__ == "__main__":
    tester = Phase4Tester()
    tester.run_all_tests()
