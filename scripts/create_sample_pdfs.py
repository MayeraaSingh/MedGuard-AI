"""
MedGuard AI - Sample PDF Generator
Phase 1: Data Layer & Input Pipeline

Generates 5-10 sample scanned provider profile PDFs for OCR testing.
Includes varied layouts, fonts, and quality levels to simulate real-world scenarios.

Quality Levels:
- Clean: 3 PDFs (high resolution, clear text, standard layout)
- Moderate: 3 PDFs (medium quality, slight rotation, varied fonts)
- Challenging: 2 PDFs (low quality, handwritten notes, complex layout)

Usage:
    python scripts/create_sample_pdfs.py
"""

import csv
import random
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

random.seed(42)


def load_sample_providers(csv_path: str, num_samples: int = 10):
    """Load sample provider data from CSV."""
    providers = []
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            if i >= num_samples:
                break
            providers.append(row)
    return providers


def create_clean_pdf(provider: dict, output_path: str, pdf_num: int):
    """Create a clean, professional provider profile PDF."""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(1 * inch, height - 1 * inch, "Provider Information Form")
    
    # Subheader
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, height - 1.3 * inch, f"Document ID: PDF-{pdf_num:03d}")
    c.drawString(1 * inch, height - 1.5 * inch, f"Date: {datetime.now().strftime('%B %d, %Y')}")
    
    # Provider Details
    y_position = height - 2.2 * inch
    c.setFont("Helvetica-Bold", 12)
    
    fields = [
        ("Provider Name:", f"{provider['first_name']} {provider['last_name']}, {provider['degree']}"),
        ("NPI Number:", provider['npi']),
        ("Specialty:", provider['specialty']),
        ("License Number:", f"{provider['license_number']} ({provider['license_state']})"),
        ("License Expiration:", provider['license_expiration_date']),
        ("DEA Number:", provider['dea_number'] if provider['dea_number'] else "N/A"),
        ("Practice Name:", provider['practice_name']),
        ("Address:", provider['street_address']),
        ("City, State ZIP:", f"{provider['city']}, {provider['state']} {provider['zip_code']}"),
        ("Phone:", provider['phone']),
        ("Fax:", provider['fax']),
        ("Email:", provider['email']),
        ("Medical School:", provider['medical_school']),
        ("Graduation Year:", str(provider['graduation_year'])),
        ("Years in Practice:", str(provider['years_in_practice'])),
        ("Accepting New Patients:", "Yes" if provider['accepts_new_patients'] == 'True' else "No"),
        ("Languages:", provider['languages_spoken'])
    ]
    
    for label, value in fields:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1 * inch, y_position, label)
        c.setFont("Helvetica", 10)
        c.drawString(2.5 * inch, y_position, str(value))
        y_position -= 0.35 * inch
    
    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(1 * inch, 0.5 * inch, "This is a synthetic document for testing purposes only.")
    
    c.save()
    print(f"  ✓ Generated clean PDF: {Path(output_path).name}")


def create_moderate_pdf(provider: dict, output_path: str, pdf_num: int):
    """Create a moderate quality PDF with varied fonts and slight formatting issues."""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    # Slightly rotated (simulating scan)
    c.rotate(1)  # 1 degree rotation
    
    # Header with different font
    c.setFont("Times-Bold", 18)
    c.drawString(1.2 * inch, height - 1.1 * inch, "HEALTHCARE PROVIDER PROFILE")
    
    # Decorative line
    c.setStrokeColor(colors.grey)
    c.setLineWidth(2)
    c.line(1 * inch, height - 1.4 * inch, 7.5 * inch, height - 1.4 * inch)
    
    # Provider Details with mixed fonts
    y_position = height - 2 * inch
    
    c.setFont("Times-Bold", 11)
    c.drawString(1.2 * inch, y_position, "PERSONAL INFORMATION")
    y_position -= 0.3 * inch
    
    # Use Courier for data (simulating typewriter)
    c.setFont("Courier", 9)
    personal_info = [
        f"Name: {provider['first_name']} {provider['last_name']}, {provider['degree']}",
        f"NPI: {provider['npi']}",
        f"Specialty: {provider['specialty']}",
        f"Email: {provider['email']}"
    ]
    
    for info in personal_info:
        c.drawString(1.4 * inch, y_position, info)
        y_position -= 0.25 * inch
    
    y_position -= 0.2 * inch
    
    # License section
    c.setFont("Times-Bold", 11)
    c.drawString(1.2 * inch, y_position, "LICENSING & CREDENTIALS")
    y_position -= 0.3 * inch
    
    c.setFont("Courier", 9)
    license_info = [
        f"License: {provider['license_number']} (State: {provider['license_state']})",
        f"Issued: {provider['license_issue_date']}",
        f"Expires: {provider['license_expiration_date']}",
        f"DEA: {provider['dea_number'] if provider['dea_number'] else 'Not Applicable'}"
    ]
    
    for info in license_info:
        c.drawString(1.4 * inch, y_position, info)
        y_position -= 0.25 * inch
    
    y_position -= 0.2 * inch
    
    # Practice Information
    c.setFont("Times-Bold", 11)
    c.drawString(1.2 * inch, y_position, "PRACTICE INFORMATION")
    y_position -= 0.3 * inch
    
    c.setFont("Courier", 9)
    practice_info = [
        f"Practice: {provider['practice_name']}",
        f"Address: {provider['street_address']}",
        f"         {provider['city']}, {provider['state']} {provider['zip_code']}",
        f"Phone: {provider['phone']}",
        f"Fax: {provider['fax']}"
    ]
    
    for info in practice_info:
        c.drawString(1.4 * inch, y_position, info)
        y_position -= 0.25 * inch
    
    # Footer with timestamp
    c.setFont("Helvetica", 7)
    c.drawString(1 * inch, 0.6 * inch, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(1 * inch, 0.4 * inch, "CONFIDENTIAL - For verification purposes only")
    
    c.save()
    print(f"  ✓ Generated moderate PDF: {Path(output_path).name}")


def create_challenging_pdf(provider: dict, output_path: str, pdf_num: int):
    """Create a challenging PDF with complex layout and lower quality."""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    # More significant rotation (poor scan)
    c.rotate(-2)  # -2 degree rotation
    
    # Faded header (simulating old document)
    c.setFillColor(colors.Color(0.3, 0.3, 0.3))  # Dark grey
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.8 * inch, height - 0.9 * inch, "Medical License Verification Form")
    
    # Box around main content (simulating form)
    c.setStrokeColor(colors.grey)
    c.setLineWidth(1)
    c.rect(0.7 * inch, height - 8 * inch, 7 * inch, 6.5 * inch)
    
    # Content in small, varied fonts
    y_position = height - 1.5 * inch
    c.setFillColor(colors.black)
    
    # Handwritten-style notes (using different fonts)
    c.setFont("Times-Italic", 9)
    c.drawString(0.9 * inch, y_position, "Provider Details (as reported):")
    y_position -= 0.4 * inch
    
    # Mixed formatting
    c.setFont("Courier-Bold", 8)
    c.drawString(1.1 * inch, y_position, f"NAME: {provider['last_name'].upper()}, {provider['first_name'].upper()}")
    y_position -= 0.3 * inch
    
    c.setFont("Courier", 8)
    details = [
        f"NPI #: {provider['npi']}",
        f"Lic: {provider['license_number']} / {provider['license_state']}",
        f"Spec: {provider['specialty']}",
        f"DEA: {provider['dea_number'] if provider['dea_number'] else '---'}",
        "",
        f"Practice: {provider['practice_name']}",
        f"Addr: {provider['street_address']}",
        f"      {provider['city']}, {provider['state']}",
        f"      ZIP: {provider['zip_code']}",
        "",
        f"Tel: {provider['phone']}",
        f"Fax: {provider['fax']}",
        "",
        f"Education: {provider['medical_school']}",
        f"Grad Year: {provider['graduation_year']}",
        f"Yrs Practice: {provider['years_in_practice']}"
    ]
    
    for detail in details:
        c.drawString(1.1 * inch, y_position, detail)
        y_position -= 0.22 * inch
    
    # Simulated handwritten note
    c.setFont("Times-Italic", 9)
    c.setFillColor(colors.Color(0, 0, 0.5))  # Blue ink
    c.drawString(1.1 * inch, y_position - 0.2 * inch, "Verified by: [Signature]")
    c.drawString(1.1 * inch, y_position - 0.4 * inch, f"Date: {datetime.now().strftime('%m/%d/%Y')}")
    
    # Stamp-like marking
    c.setStrokeColor(colors.red)
    c.setLineWidth(2)
    c.setFillColor(colors.Color(1, 0, 0, alpha=0.3))
    c.circle(6 * inch, height - 2 * inch, 0.5 * inch, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.red)
    c.drawString(5.6 * inch, height - 2.05 * inch, "COPY")
    
    # Footer
    c.setFillColor(colors.grey)
    c.setFont("Helvetica", 6)
    c.drawString(0.8 * inch, 0.5 * inch, "This document may contain artifacts from scanning process.")
    
    c.save()
    print(f"  ✓ Generated challenging PDF: {Path(output_path).name}")


def main():
    """Main execution function."""
    print("=" * 60)
    print("MedGuard AI - Sample PDF Generator")
    print("Phase 1: Data Layer & Input Pipeline")
    print("=" * 60)
    print()
    
    # Setup paths
    base_path = Path(__file__).parent.parent
    csv_path = base_path / "data" / "samples" / "providers_synthetic.csv"
    output_dir = base_path / "data" / "samples" / "pdfs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if CSV exists
    if not csv_path.exists():
        print(f"✗ Error: CSV file not found at {csv_path}")
        print("  Please run data/synthetic_generator.py first.")
        return
    
    # Load providers
    print("Loading provider data from CSV...")
    providers = load_sample_providers(str(csv_path), num_samples=10)
    print(f"✓ Loaded {len(providers)} provider profiles")
    print()
    
    # Generate PDFs
    print("Generating sample PDFs...")
    print()
    
    pdf_num = 1
    
    # Clean PDFs (3)
    print("Creating clean quality PDFs (3)...")
    for i in range(3):
        output_path = output_dir / f"provider_profile_clean_{i+1:02d}.pdf"
        create_clean_pdf(providers[i], str(output_path), pdf_num)
        pdf_num += 1
    print()
    
    # Moderate PDFs (3)
    print("Creating moderate quality PDFs (3)...")
    for i in range(3, 6):
        output_path = output_dir / f"provider_profile_moderate_{i-2:02d}.pdf"
        create_moderate_pdf(providers[i], str(output_path), pdf_num)
        pdf_num += 1
    print()
    
    # Challenging PDFs (2)
    print("Creating challenging quality PDFs (2)...")
    for i in range(6, 8):
        output_path = output_dir / f"provider_profile_challenging_{i-5:02d}.pdf"
        create_challenging_pdf(providers[i], str(output_path), pdf_num)
        pdf_num += 1
    print()
    
    # Summary
    print("=" * 60)
    print("PDF Generation Summary")
    print("=" * 60)
    print(f"Total PDFs Generated: {pdf_num - 1}")
    print(f"  Clean Quality: 3")
    print(f"  Moderate Quality: 3")
    print(f"  Challenging Quality: 2")
    print(f"\nOutput Directory: {output_dir}")
    print()
    print("=" * 60)
    print("✓ PDF Generation Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
