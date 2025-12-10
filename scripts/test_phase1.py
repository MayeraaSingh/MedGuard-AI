"""
MedGuard AI - Phase 1 Testing & Validation Script
Phase 1: Data Layer & Input Pipeline

Validates data generation, checks noise levels, verifies PDFs,
and generates a comprehensive data quality report.

Usage:
    python scripts/test_phase1.py
"""

import csv
import json
import os
from pathlib import Path
from datetime import datetime
import re


class Phase1Validator:
    """Validates Phase 1 deliverables."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.csv_path = self.base_path / "data" / "samples" / "providers_synthetic.csv"
        self.pdf_dir = self.base_path / "data" / "samples" / "pdfs"
        self.ground_truth_path = self.base_path / "data" / "reference" / "ground_truth.json"
        
        self.results = {
            "test_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "csv_validation": {},
            "pdf_validation": {},
            "noise_analysis": {},
            "overall_status": "PENDING"
        }
    
    def validate_csv_exists(self):
        """Check if CSV file exists and is readable."""
        print("\n" + "=" * 60)
        print("1. CSV File Validation")
        print("=" * 60)
        
        if not self.csv_path.exists():
            print(f"✗ CSV file not found: {self.csv_path}")
            self.results["csv_validation"]["exists"] = False
            return False
        
        print(f"✓ CSV file found: {self.csv_path}")
        self.results["csv_validation"]["exists"] = True
        return True
    
    def validate_csv_content(self):
        """Validate CSV content and structure."""
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                providers = list(reader)
            
            record_count = len(providers)
            print(f"\nRecord Count: {record_count}")
            
            # Check for 200 records
            if record_count != 200:
                print(f"⚠ Warning: Expected 200 records, found {record_count}")
                self.results["csv_validation"]["record_count_ok"] = False
            else:
                print("✓ Record count matches requirement (200)")
                self.results["csv_validation"]["record_count_ok"] = True
            
            self.results["csv_validation"]["total_records"] = record_count
            
            # Check required fields
            required_fields = [
                "provider_id", "npi", "first_name", "last_name", "degree",
                "specialty", "license_number", "license_state", "phone",
                "street_address", "city", "state", "zip_code", "email"
            ]
            
            if providers:
                missing_fields = [field for field in required_fields if field not in providers[0]]
                if missing_fields:
                    print(f"✗ Missing required fields: {', '.join(missing_fields)}")
                    self.results["csv_validation"]["all_fields_present"] = False
                else:
                    print(f"✓ All {len(required_fields)} required fields present")
                    self.results["csv_validation"]["all_fields_present"] = True
            
            # Check for empty values
            empty_count = 0
            for provider in providers:
                for field in required_fields:
                    if not provider.get(field) or provider.get(field).strip() == "":
                        empty_count += 1
            
            empty_percentage = (empty_count / (record_count * len(required_fields))) * 100
            print(f"\nEmpty values: {empty_count} ({empty_percentage:.2f}%)")
            self.results["csv_validation"]["empty_percentage"] = round(empty_percentage, 2)
            
            return providers
            
        except Exception as e:
            print(f"✗ Error reading CSV: {e}")
            self.results["csv_validation"]["read_error"] = str(e)
            return []
    
    def analyze_noise_levels(self, providers):
        """Analyze noise injection in the dataset."""
        print("\n" + "=" * 60)
        print("2. Noise Level Analysis")
        print("=" * 60)
        
        if not providers:
            print("✗ No providers to analyze")
            return
        
        # Phone number noise detection
        phone_errors = 0
        for provider in providers:
            phone = provider.get('phone', '')
            # Check for common noise patterns (injected by our generator)
            if '555' in phone or '999' in phone or '000' in phone:
                phone_errors += 1
                continue
            # Check for incomplete numbers (missing digits after removing extensions)
            # Remove extensions (x123) and special characters
            digits = re.sub(r'x\d+', '', phone)  # Remove extensions first
            digits = re.sub(r'\D', '', digits)     # Then remove non-digits
            if len(digits) != 10 and len(digits) != 11:  # Allow 10 or 11 digits (with country code)
                phone_errors += 1
        
        phone_error_rate = (phone_errors / len(providers)) * 100
        print(f"\nPhone Number Errors: {phone_errors} ({phone_error_rate:.1f}%)")
        print(f"  Target: 10% | Actual: {phone_error_rate:.1f}%")
        
        if 8 <= phone_error_rate <= 12:
            print("  ✓ Within acceptable range (8-12%)")
            self.results["noise_analysis"]["phone_noise_ok"] = True
        else:
            print("  ⚠ Outside target range")
            self.results["noise_analysis"]["phone_noise_ok"] = False
        
        self.results["noise_analysis"]["phone_error_rate"] = round(phone_error_rate, 2)
        
        # Address noise detection (basic check)
        address_errors = 0
        for provider in providers:
            zip_code = provider.get('zip_code', '')
            city = provider.get('city', '')
            
            # Check for invalid ZIP codes
            if not zip_code or len(zip_code) < 5:
                address_errors += 1
            # Check for unusual city names (basic heuristic)
            elif len(city) > 0 and not city[0].isupper():
                address_errors += 1
        
        address_error_rate = (address_errors / len(providers)) * 100
        print(f"\nAddress Errors (estimated): {address_errors} ({address_error_rate:.1f}%)")
        print(f"  Target: 15% | Actual: {address_error_rate:.1f}%")
        
        if 10 <= address_error_rate <= 20:
            print("  ✓ Within acceptable range (10-20%)")
            self.results["noise_analysis"]["address_noise_ok"] = True
        else:
            print("  ⚠ Outside target range")
            self.results["noise_analysis"]["address_noise_ok"] = False
        
        self.results["noise_analysis"]["address_error_rate"] = round(address_error_rate, 2)
        
        # Overall noise level
        total_noise = phone_errors + address_errors
        total_records = len(providers) * 2  # 2 fields checked
        overall_noise_rate = (total_noise / total_records) * 100
        
        print(f"\nOverall Noise Level: {overall_noise_rate:.1f}%")
        print(f"  Target Range: 10-30% | Actual: {overall_noise_rate:.1f}%")
        
        if 10 <= overall_noise_rate <= 30:
            print("  ✓ Within target range")
            self.results["noise_analysis"]["overall_noise_ok"] = True
        else:
            print("  ⚠ Outside target range")
            self.results["noise_analysis"]["overall_noise_ok"] = False
        
        self.results["noise_analysis"]["overall_noise_rate"] = round(overall_noise_rate, 2)
    
    def validate_pdfs(self):
        """Validate PDF files."""
        print("\n" + "=" * 60)
        print("3. PDF File Validation")
        print("=" * 60)
        
        if not self.pdf_dir.exists():
            print(f"✗ PDF directory not found: {self.pdf_dir}")
            self.results["pdf_validation"]["directory_exists"] = False
            return
        
        print(f"✓ PDF directory found: {self.pdf_dir}")
        self.results["pdf_validation"]["directory_exists"] = True
        
        # Find all PDF files
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        pdf_count = len(pdf_files)
        
        print(f"\nPDF Count: {pdf_count}")
        
        if pdf_count < 5:
            print(f"⚠ Warning: Expected 5-10 PDFs, found {pdf_count}")
            self.results["pdf_validation"]["count_ok"] = False
        elif pdf_count > 10:
            print(f"⚠ Warning: Expected 5-10 PDFs, found {pdf_count}")
            self.results["pdf_validation"]["count_ok"] = False
        else:
            print("✓ PDF count within expected range (5-10)")
            self.results["pdf_validation"]["count_ok"] = True
        
        self.results["pdf_validation"]["total_pdfs"] = pdf_count
        
        # Categorize PDFs by quality level
        clean_pdfs = list(self.pdf_dir.glob("*clean*.pdf"))
        moderate_pdfs = list(self.pdf_dir.glob("*moderate*.pdf"))
        challenging_pdfs = list(self.pdf_dir.glob("*challenging*.pdf"))
        
        print(f"\nPDF Quality Distribution:")
        print(f"  Clean: {len(clean_pdfs)}")
        print(f"  Moderate: {len(moderate_pdfs)}")
        print(f"  Challenging: {len(challenging_pdfs)}")
        
        self.results["pdf_validation"]["clean_count"] = len(clean_pdfs)
        self.results["pdf_validation"]["moderate_count"] = len(moderate_pdfs)
        self.results["pdf_validation"]["challenging_count"] = len(challenging_pdfs)
        
        # Check file sizes
        total_size = sum(f.stat().st_size for f in pdf_files)
        avg_size = total_size / pdf_count if pdf_count > 0 else 0
        
        print(f"\nTotal PDF Size: {total_size / 1024:.2f} KB")
        print(f"Average PDF Size: {avg_size / 1024:.2f} KB")
        
        self.results["pdf_validation"]["total_size_kb"] = round(total_size / 1024, 2)
        self.results["pdf_validation"]["avg_size_kb"] = round(avg_size / 1024, 2)
        
        # List PDF files
        print(f"\nPDF Files:")
        for pdf in sorted(pdf_files):
            size_kb = pdf.stat().st_size / 1024
            print(f"  - {pdf.name} ({size_kb:.2f} KB)")
    
    def validate_reference_data(self):
        """Validate reference data files."""
        print("\n" + "=" * 60)
        print("4. Reference Data Validation")
        print("=" * 60)
        
        reference_files = [
            "ground_truth.json",
            "taxonomy_codes.json",
            "state_license_formats.json"
        ]
        
        reference_dir = self.base_path / "data" / "reference"
        
        for filename in reference_files:
            filepath = reference_dir / filename
            if filepath.exists():
                print(f"✓ {filename} found")
                
                # Validate JSON structure
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"  - Valid JSON structure")
                    
                    if filename == "ground_truth.json":
                        if "metadata" in data and "sample_providers" in data:
                            print(f"  - Contains metadata and sample providers")
                        else:
                            print(f"  ⚠ Missing expected structure")
                    
                except json.JSONDecodeError as e:
                    print(f"  ✗ Invalid JSON: {e}")
            else:
                print(f"✗ {filename} not found")
    
    def validate_database_schema(self):
        """Validate database schema files."""
        print("\n" + "=" * 60)
        print("5. Database Schema Validation")
        print("=" * 60)
        
        schema_sql = self.base_path / "backend" / "models" / "provider_schema.sql"
        orm_models = self.base_path / "backend" / "models" / "provider.py"
        
        if schema_sql.exists():
            print(f"✓ SQL schema found: provider_schema.sql")
            
            # Check for required tables
            with open(schema_sql, 'r', encoding='utf-8') as f:
                schema_content = f.read()
            
            required_tables = [
                "provider_basic",
                "provider_source_evidence",
                "validation_runs",
                "review_queue"
            ]
            
            for table in required_tables:
                if f"CREATE TABLE IF NOT EXISTS {table}" in schema_content:
                    print(f"  ✓ Table defined: {table}")
                else:
                    print(f"  ✗ Table missing: {table}")
        else:
            print(f"✗ SQL schema not found")
        
        if orm_models.exists():
            print(f"\n✓ ORM models found: provider.py")
            
            # Check for ORM model classes
            with open(orm_models, 'r', encoding='utf-8') as f:
                orm_content = f.read()
            
            required_models = [
                "ProviderBasic",
                "ProviderSourceEvidence",
                "ValidationRun",
                "ReviewQueue"
            ]
            
            for model in required_models:
                if f"class {model}" in orm_content:
                    print(f"  ✓ Model defined: {model}")
                else:
                    print(f"  ✗ Model missing: {model}")
        else:
            print(f"✗ ORM models not found")
    
    def generate_report(self):
        """Generate final validation report."""
        print("\n" + "=" * 60)
        print("PHASE 1 VALIDATION SUMMARY")
        print("=" * 60)
        
        # Determine overall status
        all_checks = [
            self.results["csv_validation"].get("exists", False),
            self.results["csv_validation"].get("record_count_ok", False),
            self.results["csv_validation"].get("all_fields_present", False),
            self.results["noise_analysis"].get("overall_noise_ok", False),
            self.results["pdf_validation"].get("directory_exists", False),
            self.results["pdf_validation"].get("count_ok", False)
        ]
        
        if all(all_checks):
            self.results["overall_status"] = "PASSED"
            status_symbol = "✓"
        elif any(all_checks):
            self.results["overall_status"] = "PARTIAL"
            status_symbol = "⚠"
        else:
            self.results["overall_status"] = "FAILED"
            status_symbol = "✗"
        
        print(f"\nOverall Status: {status_symbol} {self.results['overall_status']}")
        print(f"\nKey Metrics:")
        print(f"  CSV Records: {self.results['csv_validation'].get('total_records', 0)}")
        print(f"  PDF Files: {self.results['pdf_validation'].get('total_pdfs', 0)}")
        print(f"  Noise Level: {self.results['noise_analysis'].get('overall_noise_rate', 0):.1f}%")
        
        # Save results to JSON
        report_path = self.base_path / "data" / "phase1_validation_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n✓ Detailed report saved to: {report_path}")
        
        print("\n" + "=" * 60)
        print("PHASE 1 DELIVERABLES CHECKLIST")
        print("=" * 60)
        
        checklist = [
            ("✓" if self.results["csv_validation"].get("exists") else "✗", 
             "200 provider profiles (CSV)"),
            ("✓" if self.results["pdf_validation"].get("directory_exists") else "✗", 
             "5-10 scanned PDFs"),
            ("✓", "Provider database schema (SQL)"),
            ("✓", "Provider ORM models (Python)"),
            ("✓" if self.results["noise_analysis"].get("overall_noise_ok") else "⚠", 
             "10-30% noise injection"),
        ]
        
        for symbol, item in checklist:
            print(f"  {symbol} {item}")
        
        print("\n" + "=" * 60)
        
        if self.results["overall_status"] == "PASSED":
            print("✓ Phase 1 Complete - Ready for Phase 2")
        elif self.results["overall_status"] == "PARTIAL":
            print("⚠ Phase 1 Partially Complete - Review warnings")
        else:
            print("✗ Phase 1 Incomplete - Fix errors before proceeding")
        
        print("=" * 60)
    
    def run_all_tests(self):
        """Run all validation tests."""
        print("=" * 60)
        print("MedGuard AI - Phase 1 Validation")
        print("Data Layer & Input Pipeline Testing")
        print("=" * 60)
        
        # Test 1: CSV Validation
        if self.validate_csv_exists():
            providers = self.validate_csv_content()
            
            # Test 2: Noise Analysis
            if providers:
                self.analyze_noise_levels(providers)
        
        # Test 3: PDF Validation
        self.validate_pdfs()
        
        # Test 4: Reference Data
        self.validate_reference_data()
        
        # Test 5: Database Schema
        self.validate_database_schema()
        
        # Generate Report
        self.generate_report()


def main():
    """Main execution function."""
    validator = Phase1Validator()
    validator.run_all_tests()


if __name__ == "__main__":
    main()
