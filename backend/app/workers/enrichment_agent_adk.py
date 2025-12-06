"""
MedGuard AI - Enrichment Agent (Google ADK)
Phase 2: Core Agent Architecture

Enriches provider data with additional information using Google's Agent Development Kit.
Uses ADK's agent framework with tools for:
- Medical school fuzzy matching
- Specialty mapping and sub-specialties
- Certification inference
- Services offered inference
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from fuzzywuzzy import fuzz

from google import genai
from google.genai import types


class EnrichmentAgentADK:
    """
    ADK-based enrichment agent that augments provider data with additional information.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the enrichment agent with ADK.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Medical schools for fuzzy matching
        self.medical_schools = [
            "Harvard Medical School", "Johns Hopkins University School of Medicine",
            "Stanford University School of Medicine", "University of California San Francisco",
            "Yale School of Medicine", "Columbia University Vagelos College of Physicians and Surgeons",
            "University of Pennsylvania Perelman School of Medicine",
            "Duke University School of Medicine", "University of Washington School of Medicine",
            "University of Michigan Medical School", "Mayo Clinic Alix School of Medicine",
            "New York University Grossman School of Medicine", "Northwestern University Feinberg School of Medicine",
            "Vanderbilt University School of Medicine", "Cornell University Weill Cornell Medicine"
        ]
        
        # Specialty mappings
        self.specialty_mappings = {
            "Cardiology": ["Interventional Cardiology", "Electrophysiology", "Heart Failure"],
            "Orthopedic Surgery": ["Sports Medicine", "Joint Replacement", "Spine Surgery"],
            "Internal Medicine": ["Geriatrics", "Hospital Medicine", "Primary Care"],
            "Pediatrics": ["Neonatology", "Pediatric Emergency Medicine", "Adolescent Medicine"],
            "Dermatology": ["Cosmetic Dermatology", "Dermatopathology", "Mohs Surgery"],
            "Family Medicine": ["Sports Medicine", "Geriatrics", "Obstetrics"],
            "Emergency Medicine": ["Pediatric Emergency", "Toxicology", "EMS"],
            "Psychiatry": ["Child Psychiatry", "Addiction Psychiatry", "Geriatric Psychiatry"],
            "Radiology": ["Interventional Radiology", "Neuroradiology", "Body Imaging"],
            "Anesthesiology": ["Pain Management", "Cardiac Anesthesia", "Pediatric Anesthesia"]
        }
        
        # Services by specialty
        self.specialty_services = {
            "Cardiology": ["Cardiac Consultations", "EKG", "Echocardiography", "Stress Tests", "Holter Monitoring"],
            "Dermatology": ["Skin Exams", "Acne Treatment", "Skin Cancer Screening", "Cosmetic Procedures", "Laser Therapy"],
            "Family Medicine": ["Annual Physicals", "Vaccinations", "Chronic Disease Management", "Minor Procedures", "Preventive Care"],
            "Pediatrics": ["Well-Child Visits", "Vaccinations", "Developmental Screenings", "Sick Visits", "Sports Physicals"],
            "Internal Medicine": ["Annual Physicals", "Chronic Disease Management", "Preventive Care", "Health Screenings"],
            "Orthopedic Surgery": ["Fracture Care", "Joint Replacement", "Arthroscopy", "Sports Medicine", "Physical Therapy"]
        }
        
        # Define tools for the agent
        self.tools = self._create_tools()
    
    def _create_tools(self) -> List[types.Tool]:
        """
        Create ADK tools for enrichment operations.
        
        Returns:
            List of ADK tools
        """
        tools = [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="enrich_education",
                    description="Match and validate medical school using fuzzy matching",
                    parameters={
                        "type": "object",
                        "properties": {
                            "medical_school": {
                                "type": "string",
                                "description": "Medical school name to match"
                            }
                        },
                        "required": ["medical_school"]
                    }
                ),
                types.FunctionDeclaration(
                    name="enrich_specialty",
                    description="Map specialty to sub-specialties and validate degree alignment",
                    parameters={
                        "type": "object",
                        "properties": {
                            "specialty": {
                                "type": "string",
                                "description": "Medical specialty"
                            },
                            "degree": {
                                "type": "string",
                                "description": "Medical degree (MD, DO, DDS, etc.)"
                            }
                        },
                        "required": ["specialty"]
                    }
                ),
                types.FunctionDeclaration(
                    name="enrich_services",
                    description="Infer services offered based on specialty",
                    parameters={
                        "type": "object",
                        "properties": {
                            "specialty": {
                                "type": "string",
                                "description": "Medical specialty"
                            }
                        },
                        "required": ["specialty"]
                    }
                )
            ])
        ]
        
        return tools
    
    def enrich_provider(self, provider_data: Dict[str, Any], 
                       validation_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Enrich a single provider using ADK tools.
        
        Args:
            provider_data: Provider information dictionary
            validation_result: Optional validation result from ValidationAgent
            
        Returns:
            Enrichment result with additional fields
        """
        enrichment_result = {
            "provider_id": provider_data.get("provider_id") or provider_data.get("npi"),
            "enriched_fields": {},
            "source_evidence": [],
            "enrichment_confidence": 0.0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Enrich education
        if provider_data.get("medical_school"):
            education_result = self._enrich_education_impl(provider_data["medical_school"])
            enrichment_result["enriched_fields"]["education"] = education_result
            if education_result.get("evidence"):
                enrichment_result["source_evidence"].extend(education_result["evidence"])
        
        # Enrich specialty
        if provider_data.get("specialty"):
            specialty_result = self._enrich_specialty_impl(
                provider_data["specialty"],
                provider_data.get("degree")
            )
            enrichment_result["enriched_fields"]["specialty"] = specialty_result
            if specialty_result.get("evidence"):
                enrichment_result["source_evidence"].extend(specialty_result["evidence"])
        
        # Enrich services
        if provider_data.get("specialty"):
            services_result = self._enrich_services_impl(provider_data["specialty"])
            enrichment_result["enriched_fields"]["services"] = services_result
            if services_result.get("evidence"):
                enrichment_result["source_evidence"].extend(services_result["evidence"])
        
        # Calculate overall enrichment confidence
        confidences = [
            result.get("confidence", 0.0)
            for result in enrichment_result["enriched_fields"].values()
            if result.get("confidence") is not None
        ]
        
        if confidences:
            enrichment_result["enrichment_confidence"] = sum(confidences) / len(confidences)
        
        return enrichment_result
    
    def _enrich_education_impl(self, medical_school: str) -> Dict[str, Any]:
        """
        Implementation of education enrichment using fuzzy matching.
        
        Args:
            medical_school: Medical school name
            
        Returns:
            Enrichment result with matched school
        """
        if not medical_school:
            return {
                "enriched_value": None,
                "confidence": 0.0,
                "reason": "Medical school not provided",
                "evidence": []
            }
        
        # Fuzzy match against known schools
        best_match = None
        best_score = 0
        
        for school in self.medical_schools:
            score = fuzz.ratio(medical_school.lower(), school.lower())
            if score > best_score:
                best_score = score
                best_match = school
        
        # Threshold for matching
        match_threshold = 80
        
        if best_score >= match_threshold:
            return {
                "enriched_value": best_match,
                "confidence": best_score / 100.0,
                "match_score": best_score,
                "original_value": medical_school,
                "reason": f"Matched with {best_score}% confidence",
                "evidence": [{
                    "field_name": "medical_school",
                    "source_name": "fuzzy_matching",
                    "source_value": best_match,
                    "source_confidence_weight": best_score / 100.0,
                    "extraction_method": "fuzzy_match",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "match_score": best_score,
                        "original_value": medical_school
                    }
                }]
            }
        else:
            return {
                "enriched_value": medical_school,  # Keep original
                "confidence": 0.4,  # Low confidence for unmatched
                "match_score": best_score,
                "reason": f"No good match found (best: {best_score}%)",
                "evidence": [{
                    "field_name": "medical_school",
                    "source_name": "original_data",
                    "source_value": medical_school,
                    "source_confidence_weight": 0.4,
                    "extraction_method": "passthrough",
                    "timestamp": datetime.now().isoformat()
                }]
            }
    
    def _enrich_specialty_impl(self, specialty: str, degree: str = None) -> Dict[str, Any]:
        """
        Implementation of specialty enrichment with sub-specialties.
        
        Args:
            specialty: Medical specialty
            degree: Medical degree
            
        Returns:
            Enrichment result with sub-specialties
        """
        if not specialty:
            return {
                "enriched_value": None,
                "confidence": 0.0,
                "reason": "Specialty not provided",
                "evidence": []
            }
        
        # Map to sub-specialties
        sub_specialties = self.specialty_mappings.get(specialty, [])
        
        # Check degree-specialty alignment
        alignment_check = self._check_degree_specialty_alignment(degree, specialty)
        
        confidence = 0.7
        if not alignment_check["aligned"]:
            confidence = 0.3
        
        return {
            "enriched_value": {
                "specialty": specialty,
                "sub_specialties": sub_specialties,
                "degree_aligned": alignment_check["aligned"]
            },
            "confidence": confidence,
            "reason": alignment_check["reason"],
            "evidence": [{
                "field_name": "specialty",
                "source_name": "specialty_mapping",
                "source_value": specialty,
                "source_confidence_weight": confidence,
                "extraction_method": "mapping",
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "sub_specialties": sub_specialties,
                    "degree_aligned": alignment_check["aligned"]
                }
            }]
        }
    
    def _enrich_services_impl(self, specialty: str) -> Dict[str, Any]:
        """
        Implementation of services inference based on specialty.
        
        Args:
            specialty: Medical specialty
            
        Returns:
            Enrichment result with inferred services
        """
        if not specialty:
            return {
                "enriched_value": [],
                "confidence": 0.0,
                "reason": "Specialty not provided",
                "evidence": []
            }
        
        # Get services for specialty
        services = self.specialty_services.get(specialty, [])
        
        confidence = 0.6 if services else 0.3
        
        return {
            "enriched_value": services,
            "confidence": confidence,
            "reason": f"Inferred {len(services)} services from specialty",
            "evidence": [{
                "field_name": "services",
                "source_name": "specialty_inference",
                "source_value": services,
                "source_confidence_weight": confidence,
                "extraction_method": "inference",
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "specialty": specialty,
                    "service_count": len(services)
                }
            }]
        }
    
    def _check_degree_specialty_alignment(self, degree: str, specialty: str) -> Dict[str, Any]:
        """
        Check if degree aligns with specialty.
        
        Args:
            degree: Medical degree (MD, DO, DDS, etc.)
            specialty: Medical specialty
            
        Returns:
            Alignment check result
        """
        if not degree:
            return {
                "aligned": True,
                "reason": "Degree not provided for alignment check"
            }
        
        degree = degree.upper()
        
        # Define misalignment patterns
        misalignments = {
            "PharmD": ["Surgery", "Cardiology", "Orthopedics", "Dermatology"],
            "DDS": ["Internal Medicine", "Cardiology", "Psychiatry"],
            "DPM": ["Cardiology", "Internal Medicine", "Psychiatry"],
            "OD": ["Surgery", "Internal Medicine", "Cardiology"]
        }
        
        for deg, incompatible_specialties in misalignments.items():
            if degree == deg and any(spec.lower() in specialty.lower() for spec in incompatible_specialties):
                return {
                    "aligned": False,
                    "reason": f"{degree} degree does not typically align with {specialty}"
                }
        
        return {
            "aligned": True,
            "reason": "Degree-specialty alignment acceptable"
        }
    
    def enrich_batch(self, providers: List[Dict[str, Any]], 
                    validation_results: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Enrich multiple providers in batch.
        
        Args:
            providers: List of provider dictionaries
            validation_results: Optional list of validation results
            
        Returns:
            List of enrichment results
        """
        results = []
        
        for i, provider in enumerate(providers, 1):
            print(f"Enriching provider {i}/{len(providers)}: {provider.get('npi') or provider.get('provider_id')}")
            
            validation_result = None
            if validation_results and i <= len(validation_results):
                validation_result = validation_results[i-1]
            
            result = self.enrich_provider(provider, validation_result)
            results.append(result)
        
        return results


if __name__ == "__main__":
    # Test the ADK enrichment agent
    agent = EnrichmentAgentADK()
    
    test_provider = {
        "provider_id": "9999123456",
        "npi": "9999123456",
        "medical_school": "Harvard Med School",  # Slight mismatch for fuzzy matching
        "specialty": "Cardiology",
        "degree": "MD"
    }
    
    result = agent.enrich_provider(test_provider)
    print("\nEnrichment Result:")
    print(f"Enriched fields: {list(result['enriched_fields'].keys())}")
    print(f"Confidence: {result['enrichment_confidence']:.3f}")
    print(f"Evidence count: {len(result['source_evidence'])}")
    
    if result['enriched_fields'].get('education'):
        edu = result['enriched_fields']['education']
        print(f"\nEducation match: {edu['enriched_value']} ({edu.get('match_score', 0)}% match)")
    
    if result['enriched_fields'].get('specialty'):
        spec = result['enriched_fields']['specialty']
        print(f"\nSub-specialties: {spec['enriched_value'].get('sub_specialties', [])}")
    
    if result['enriched_fields'].get('services'):
        serv = result['enriched_fields']['services']
        print(f"\nServices: {serv['enriched_value']}")
