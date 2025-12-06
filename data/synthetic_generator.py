"""
MedGuard AI - Synthetic Provider Data Generator
Phase 1: Data Layer & Input Pipeline

Generates 200 synthetic healthcare provider profiles with controlled noise injection
for testing multi-agent validation pipeline.

Noise Injection Strategy:
- 10% outdated/incorrect phone numbers
- 15% incorrect addresses (wrong ZIP, misspelled city, wrong street number)
- 5% mismatched specialties
- Target: 10-30% noise per record

Usage:
    python data/synthetic_generator.py
"""

import csv
import random
import json
from datetime import datetime, timedelta
from pathlib import Path
from faker import Faker
from typing import List, Dict, Any

# Initialize Faker
fake = Faker(['en_US'])
Faker.seed(42)
random.seed(42)

# Reference Data
SPECIALTIES = [
    "Family Medicine", "Internal Medicine", "Pediatrics", "Cardiology",
    "Dermatology", "Orthopedic Surgery", "Psychiatry", "Obstetrics & Gynecology",
    "Emergency Medicine", "Anesthesiology", "Radiology", "Pathology",
    "General Surgery", "Neurology", "Oncology", "Urology", "Ophthalmology",
    "Gastroenterology", "Pulmonology", "Nephrology", "Endocrinology",
    "Rheumatology", "Allergy & Immunology", "Physical Medicine & Rehabilitation"
]

LICENSE_STATES = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]

MEDICAL_SCHOOLS = [
    "Harvard Medical School", "Johns Hopkins School of Medicine",
    "Stanford University School of Medicine", "UCSF School of Medicine",
    "Yale School of Medicine", "Columbia University College of Physicians and Surgeons",
    "University of Pennsylvania Perelman School of Medicine",
    "Duke University School of Medicine", "Washington University School of Medicine",
    "Northwestern University Feinberg School of Medicine"
]

PRACTICE_TYPES = ["Solo Practice", "Group Practice", "Hospital-based", "Academic Medical Center"]

INSURANCES = ["Medicare", "Medicaid", "Blue Cross Blue Shield", "Aetna", "Cigna", 
              "UnitedHealthcare", "Humana", "Kaiser Permanente"]


def generate_npi() -> str:
    """Generate a synthetic 10-digit NPI number with Luhn checksum.
    Prefixed with 9999 to mark as synthetic."""
    base = "9999" + "".join([str(random.randint(0, 9)) for _ in range(5)])
    
    # Luhn algorithm for checksum
    digits = [int(d) for d in base]
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 0:
            doubled = digit * 2
            checksum += doubled if doubled < 10 else doubled - 9
        else:
            checksum += digit
    
    check_digit = (10 - (checksum % 10)) % 10
    return base + str(check_digit)


def generate_license_number(state: str) -> str:
    """Generate a synthetic state medical license number."""
    formats = {
        "CA": f"A{random.randint(10000, 99999)}",
        "NY": f"{random.randint(100000, 999999)}",
        "TX": f"{random.choice(['M', 'N', 'P'])}{random.randint(1000, 9999)}",
        "FL": f"ME{random.randint(10000, 99999)}",
        "IL": f"036.{random.randint(100000, 999999)}",
    }
    return formats.get(state, f"{state}{random.randint(10000, 99999)}")


def generate_dea_number(last_name: str) -> str:
    """Generate a synthetic DEA number."""
    first_letter = random.choice(['A', 'B', 'F'])  # A=pharmacy, B=hospital, F=practitioner
    second_letter = last_name[0].upper()
    numbers = "".join([str(random.randint(0, 9)) for _ in range(6)])
    
    # DEA checksum
    digits = [int(d) for d in numbers]
    checksum = (digits[0] + digits[2] + digits[4]) + 2 * (digits[1] + digits[3] + digits[5])
    check_digit = checksum % 10
    
    return f"{first_letter}{second_letter}{numbers}{check_digit}"


def inject_phone_noise(phone: str) -> str:
    """Inject noise into phone number (10% chance)."""
    if random.random() < 0.10:
        digits = phone.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
        noise_type = random.choice(['swap_digits', 'wrong_area_code', 'missing_digit'])
        
        if noise_type == 'swap_digits' and len(digits) >= 10:
            # Swap two random digits
            pos1, pos2 = random.sample(range(len(digits)), 2)
            digits_list = list(digits)
            digits_list[pos1], digits_list[pos2] = digits_list[pos2], digits_list[pos1]
            digits = ''.join(digits_list)
        elif noise_type == 'wrong_area_code':
            # Replace area code with outdated one
            wrong_codes = ['555', '999', '000']
            digits = random.choice(wrong_codes) + digits[3:]
        elif noise_type == 'missing_digit':
            # Remove one digit
            digits = digits[:-1]
        
        return digits
    return phone


def inject_address_noise(address: Dict[str, str]) -> Dict[str, str]:
    """Inject noise into address (15% chance)."""
    if random.random() < 0.15:
        noise_type = random.choice(['wrong_zip', 'misspelled_city', 'wrong_street_number'])
        
        if noise_type == 'wrong_zip':
            # Change last digit of ZIP
            address['zip_code'] = address['zip_code'][:-1] + str(random.randint(0, 9))
        elif noise_type == 'misspelled_city':
            # Add typo to city name
            city = address['city']
            if len(city) > 3:
                pos = random.randint(1, len(city) - 2)
                city = city[:pos] + random.choice('aeiou') + city[pos + 1:]
                address['city'] = city
        elif noise_type == 'wrong_street_number':
            # Change street number
            parts = address['street'].split()
            if parts and parts[0].isdigit():
                parts[0] = str(int(parts[0]) + random.randint(1, 100))
                address['street'] = ' '.join(parts)
    
    return address


def inject_specialty_mismatch(specialty: str, degree: str) -> str:
    """Inject mismatched specialty (5% chance)."""
    if random.random() < 0.05:
        # Pick a completely different specialty
        different = [s for s in SPECIALTIES if s != specialty]
        return random.choice(different)
    return specialty


def generate_provider() -> Dict[str, Any]:
    """Generate a single synthetic provider profile."""
    
    # Basic Information
    first_name = fake.first_name()
    last_name = fake.last_name()
    degree = random.choice(["MD", "DO", "NP", "PA", "DDS", "PharmD"])
    
    # Professional Information
    npi = generate_npi()
    specialty = random.choice(SPECIALTIES)
    license_state = random.choice(LICENSE_STATES)
    license_number = generate_license_number(license_state)
    dea_number = generate_dea_number(last_name) if degree in ["MD", "DO", "NP", "PA"] else ""
    
    # Practice Information
    practice_name = f"{last_name} {random.choice(['Medical Group', 'Health Center', 'Clinic', 'Associates'])}"
    practice_type = random.choice(PRACTICE_TYPES)
    years_in_practice = random.randint(1, 35)
    
    # Education
    medical_school = random.choice(MEDICAL_SCHOOLS)
    graduation_year = datetime.now().year - years_in_practice - random.randint(3, 7)
    
    # Contact Information
    phone = fake.phone_number()
    fax = fake.phone_number()
    email = f"{first_name.lower()}.{last_name.lower()}@{fake.domain_name()}"
    website = f"https://www.{last_name.lower()}health.com" if random.random() > 0.3 else ""
    
    # Address
    address = {
        'street': fake.street_address(),
        'city': fake.city(),
        'state': license_state,
        'zip_code': fake.zipcode()
    }
    
    # Insurance & Additional Info
    accepts_new_patients = random.choice([True, False])
    insurances_accepted = random.sample(INSURANCES, k=random.randint(3, 6))
    languages = ["English"] + random.sample(["Spanish", "Mandarin", "French", "German", "Hindi"], 
                                            k=random.randint(0, 2))
    
    # License Information
    license_issue_date = datetime.now() - timedelta(days=random.randint(365, 3650))
    license_expiration_date = license_issue_date + timedelta(days=random.randint(730, 1825))
    
    # Inject Noise
    phone = inject_phone_noise(phone)
    address = inject_address_noise(address)
    specialty = inject_specialty_mismatch(specialty, degree)
    
    return {
        "provider_id": npi,
        "npi": npi,
        "first_name": first_name,
        "last_name": last_name,
        "degree": degree,
        "specialty": specialty,
        "license_number": license_number,
        "license_state": license_state,
        "license_issue_date": license_issue_date.strftime("%Y-%m-%d"),
        "license_expiration_date": license_expiration_date.strftime("%Y-%m-%d"),
        "dea_number": dea_number,
        "practice_name": practice_name,
        "practice_type": practice_type,
        "street_address": address['street'],
        "city": address['city'],
        "state": address['state'],
        "zip_code": address['zip_code'],
        "phone": phone,
        "fax": fax,
        "email": email,
        "website": website,
        "medical_school": medical_school,
        "graduation_year": graduation_year,
        "years_in_practice": years_in_practice,
        "accepts_new_patients": accepts_new_patients,
        "insurances_accepted": "; ".join(insurances_accepted),
        "languages_spoken": "; ".join(languages),
        "date_added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "record_status": "Active"
    }


def generate_dataset(num_providers: int = 200) -> List[Dict[str, Any]]:
    """Generate complete synthetic dataset."""
    print(f"Generating {num_providers} synthetic provider profiles...")
    providers = []
    
    for i in range(num_providers):
        provider = generate_provider()
        providers.append(provider)
        
        if (i + 1) % 50 == 0:
            print(f"  Generated {i + 1}/{num_providers} providers...")
    
    print(f"✓ Successfully generated {num_providers} provider profiles")
    return providers


def save_to_csv(providers: List[Dict[str, Any]], output_path: str):
    """Save providers to CSV file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = list(providers[0].keys())
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(providers)
    
    print(f"✓ Saved dataset to: {output_path}")


def save_ground_truth(providers: List[Dict[str, Any]], output_path: str):
    """Save ground truth data for validation testing."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save first 10 providers as ground truth with clean data (pre-noise)
    ground_truth = {
        "metadata": {
            "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_records": len(providers),
            "noise_injection": {
                "phone_errors": "10%",
                "address_errors": "15%",
                "specialty_mismatches": "5%"
            }
        },
        "sample_providers": providers[:10]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, indent=2)
    
    print(f"✓ Saved ground truth to: {output_path}")


def generate_statistics(providers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate statistics about the dataset."""
    stats = {
        "total_providers": len(providers),
        "specialties": {},
        "states": {},
        "degrees": {},
        "practice_types": {}
    }
    
    for provider in providers:
        # Count specialties
        specialty = provider['specialty']
        stats['specialties'][specialty] = stats['specialties'].get(specialty, 0) + 1
        
        # Count states
        state = provider['state']
        stats['states'][state] = stats['states'].get(state, 0) + 1
        
        # Count degrees
        degree = provider['degree']
        stats['degrees'][degree] = stats['degrees'].get(degree, 0) + 1
        
        # Count practice types
        practice_type = provider['practice_type']
        stats['practice_types'][practice_type] = stats['practice_types'].get(practice_type, 0) + 1
    
    return stats


def main():
    """Main execution function."""
    print("=" * 60)
    print("MedGuard AI - Synthetic Provider Data Generator")
    print("Phase 1: Data Layer & Input Pipeline")
    print("=" * 60)
    print()
    
    # Generate dataset
    providers = generate_dataset(num_providers=200)
    
    # Define output paths
    base_path = Path(__file__).parent
    csv_output = base_path / "samples" / "providers_synthetic.csv"
    ground_truth_output = base_path / "reference" / "ground_truth.json"
    
    # Save outputs
    save_to_csv(providers, str(csv_output))
    save_ground_truth(providers, str(ground_truth_output))
    
    # Generate and display statistics
    stats = generate_statistics(providers)
    print()
    print("=" * 60)
    print("Dataset Statistics")
    print("=" * 60)
    print(f"Total Providers: {stats['total_providers']}")
    print(f"\nTop Specialties:")
    for specialty, count in sorted(stats['specialties'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {specialty}: {count}")
    print(f"\nStates: {len(stats['states'])}")
    print(f"Degrees: {list(stats['degrees'].keys())}")
    print(f"Practice Types: {list(stats['practice_types'].keys())}")
    print()
    print("=" * 60)
    print("✓ Phase 1 Data Generation Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
