"""
MedGuard AI - QA Agent (Google ADK)
Phase 2: Core Agent Architecture

Quality assurance agent using Google's Agent Development Kit.
Consolidates multi-source evidence, resolves conflicts, detects fraud, scores confidence.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dateutil import parser as date_parser
from fuzzywuzzy import fuzz
import re

from google import genai
from google.genai import types


class QAAgentADK:
    """
    ADK-based QA agent that performs quality assurance and conflict resolution.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the QA agent with ADK.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Source weights for conflict resolution
        self.source_weights = {
            "npi_registry": 0.90,
            "state_board": 0.95,
            "hospital_directory": 0.85,
            "google_maps": 0.70,
            "practice_website": 0.60,
            "format_validation": 0.50
        }
        
        # Confidence thresholds
        self.thresholds = {
            "high": 0.80,
            "medium": 0.60,
            "low": 0.40
        }
        
        # Fraud patterns
        self.fraud_patterns = {
            "phone": [r'555-?\d{4}', r'999-?\d{4}', r'000-?\d{4}'],
            "address": [r'PO\s+BOX', r'P\.O\.\s+BOX'],
            "email": [r'test@', r'example\.com$', r'sample\.', r'temp\.']
        }
    
    def assess_provider(self, provider_data: Dict[str, Any],
                       validation_result: Dict[str, Any],
                       enrichment_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform quality assurance on provider using validation and enrichment results.
        
        Args:
            provider_data: Original provider data
            validation_result: Result from ValidationAgent
            enrichment_result: Result from EnrichmentAgent
            
        Returns:
            QA assessment with final confidence scores and review requirements
        """
        qa_result = {
            "provider_id": provider_data.get("provider_id") or provider_data.get("npi"),
            "resolved_fields": {},
            "overall_confidence": 0.0,
            "flags": [],
            "requires_review": False,
            "priority": 0,
            "risk_level": "low",
            "status": "pending",
            "timestamp": datetime.now().isoformat()
        }
        
        # Combine all evidence
        all_evidence = []
        if validation_result.get("source_evidence"):
            all_evidence.extend(validation_result["source_evidence"])
        if enrichment_result.get("source_evidence"):
            all_evidence.extend(enrichment_result["source_evidence"])
        
        # Resolve each field
        fields_to_resolve = ["npi", "phone", "address", "license", "medical_school", "specialty"]
        
        for field in fields_to_resolve:
            field_evidence = [e for e in all_evidence if e.get("field_name") == field]
            if field_evidence:
                resolved = self._resolve_field(field, field_evidence)
                qa_result["resolved_fields"][field] = resolved
        
        # Detect fraud
        fraud_flags = self._detect_fraud(provider_data, validation_result)
        qa_result["flags"].extend(fraud_flags)
        
        # Add validation flags
        if validation_result.get("flags"):
            qa_result["flags"].extend(validation_result["flags"])
        
        # Calculate overall confidence
        qa_result["overall_confidence"] = self._calculate_overall_confidence(
            qa_result["resolved_fields"],
            validation_result,
            enrichment_result
        )
        
        # Determine review requirements
        review_info = self._determine_review_requirements(
            qa_result["overall_confidence"],
            qa_result["flags"],
            provider_data
        )
        
        qa_result["requires_review"] = review_info["requires_review"]
        qa_result["priority"] = review_info["priority"]
        qa_result["risk_level"] = review_info["risk_level"]
        
        # Determine status
        if qa_result["overall_confidence"] >= self.thresholds["high"] and not qa_result["flags"]:
            qa_result["status"] = "approved"
        elif qa_result["requires_review"]:
            qa_result["status"] = "needs_review"
        else:
            qa_result["status"] = "flagged"
        
        return qa_result
    
    def _resolve_field(self, field_name: str, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Resolve conflicts for a single field using evidence.
        
        Args:
            field_name: Name of the field
            evidence_list: List of evidence for this field
            
        Returns:
            Resolved field value with confidence
        """
        if not evidence_list:
            return {
                "value": None,
                "confidence": 0.0,
                "source": None,
                "conflicts": False
            }
        
        # Check for conflicts (different values from different sources)
        unique_values = {}
        for evidence in evidence_list:
            value = str(evidence.get("source_value", ""))
            source = evidence.get("source_name", "")
            weight = evidence.get("source_confidence_weight", 0.5)
            
            if value not in unique_values:
                unique_values[value] = []
            unique_values[value].append({"source": source, "weight": weight})
        
        # If only one value, no conflict
        if len(unique_values) == 1:
            value = list(unique_values.keys())[0]
            avg_weight = sum(e["weight"] for e in unique_values[value]) / len(unique_values[value])
            
            return {
                "value": value,
                "confidence": avg_weight,
                "source": unique_values[value][0]["source"],
                "conflicts": False
            }
        
        # Multiple values - resolve conflict using weighted voting
        value_scores = {}
        for value, sources in unique_values.items():
            total_weight = sum(s["weight"] for s in sources)
            value_scores[value] = total_weight
        
        # Get highest weighted value
        best_value = max(value_scores, key=value_scores.get)
        confidence = value_scores[best_value] / sum(value_scores.values())
        
        return {
            "value": best_value,
            "confidence": confidence,
            "source": "weighted_resolution",
            "conflicts": True,
            "alternatives": [{"value": v, "score": s} for v, s in value_scores.items() if v != best_value]
        }
    
    def _detect_fraud(self, provider_data: Dict[str, Any],
                     validation_result: Dict[str, Any]) -> List[str]:
        """
        Detect potential fraud patterns.
        
        Args:
            provider_data: Provider data
            validation_result: Validation result
            
        Returns:
            List of fraud flags
        """
        flags = []
        
        # Check phone patterns
        phone = str(provider_data.get("phone", ""))
        for pattern in self.fraud_patterns["phone"]:
            if re.search(pattern, phone):
                flags.append(f"Suspicious phone pattern: {pattern}")
        
        # Check address patterns
        address = str(provider_data.get("street_address", ""))
        for pattern in self.fraud_patterns["address"]:
            if re.search(pattern, address, re.IGNORECASE):
                flags.append(f"Suspicious address pattern: PO Box")
        
        # Check email patterns
        email = str(provider_data.get("email", ""))
        for pattern in self.fraud_patterns["email"]:
            if re.search(pattern, email, re.IGNORECASE):
                flags.append(f"Suspicious email pattern")
        
        # Check for expired licenses
        if provider_data.get("license_expiration_date"):
            try:
                exp_date = date_parser.parse(str(provider_data["license_expiration_date"]))
                if exp_date < datetime.now():
                    flags.append(f"Expired license: {provider_data['license_expiration_date']}")
            except:
                pass
        
        return flags
    
    def _calculate_overall_confidence(self, resolved_fields: Dict[str, Any],
                                     validation_result: Dict[str, Any],
                                     enrichment_result: Dict[str, Any]) -> float:
        """
        Calculate overall confidence score.
        
        Args:
            resolved_fields: Resolved field values
            validation_result: Validation result
            enrichment_result: Enrichment result
            
        Returns:
            Overall confidence score (0.0-1.0)
        """
        # Field weights
        field_weights = {
            "npi": 2.0,
            "license": 1.5,
            "phone": 1.0,
            "address": 1.0,
            "specialty": 1.0,
            "medical_school": 0.8,
            "email": 0.5
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for field, data in resolved_fields.items():
            confidence = data.get("confidence", 0.0)
            weight = field_weights.get(field, 1.0)
            
            weighted_sum += confidence * weight
            total_weight += weight
        
        if total_weight > 0:
            return weighted_sum / total_weight
        
        return 0.0
    
    def _determine_review_requirements(self, confidence: float,
                                      flags: List[str],
                                      provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine if manual review is required.
        
        Args:
            confidence: Overall confidence score
            flags: List of flags
            provider_data: Provider data
            
        Returns:
            Review requirements dictionary
        """
        requires_review = False
        priority = 0
        risk_level = "low"
        
        # Low confidence requires review
        if confidence < self.thresholds["medium"]:
            requires_review = True
            priority += 20
        
        # Flags increase priority
        if flags:
            requires_review = True
            priority += len(flags) * 10
        
        # Check for high-risk flags
        high_risk_keywords = ["fraud", "suspicious", "expired", "invalid"]
        for flag in flags:
            if any(keyword in flag.lower() for keyword in high_risk_keywords):
                risk_level = "high"
                priority += 30
                break
        
        # Medium risk
        if risk_level == "low" and (confidence < self.thresholds["high"] or flags):
            risk_level = "medium"
        
        # Cap priority at 100
        priority = min(priority, 100)
        
        return {
            "requires_review": requires_review,
            "priority": priority,
            "risk_level": risk_level
        }
    
    def assess_batch(self, providers: List[Dict[str, Any]],
                    validation_results: List[Dict[str, Any]],
                    enrichment_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Assess multiple providers in batch.
        
        Args:
            providers: List of provider dictionaries
            validation_results: List of validation results
            enrichment_results: List of enrichment results
            
        Returns:
            List of QA assessment results
        """
        results = []
        
        for i, provider in enumerate(providers):
            print(f"Assessing provider {i+1}/{len(providers)}: {provider.get('npi') or provider.get('provider_id')}")
            
            validation = validation_results[i] if i < len(validation_results) else {}
            enrichment = enrichment_results[i] if i < len(enrichment_results) else {}
            
            result = self.assess_provider(provider, validation, enrichment)
            results.append(result)
        
        return results


if __name__ == "__main__":
    # Test the ADK QA agent
    agent = QAAgentADK()
    
    test_provider = {
        "provider_id": "9999123456",
        "npi": "9999123456",
        "phone": "(555) 555-1234",  # Suspicious
        "email": "test@example.com"  # Suspicious
    }
    
    test_validation = {
        "fields_validated": {
            "npi": {"valid": True, "confidence": 0.9},
            "phone": {"valid": False, "confidence": 0.3}
        },
        "source_evidence": [],
        "flags": ["Phone validation failed"]
    }
    
    test_enrichment = {
        "enriched_fields": {},
        "source_evidence": []
    }
    
    result = agent.assess_provider(test_provider, test_validation, test_enrichment)
    print("\nQA Assessment Result:")
    print(f"Status: {result['status']}")
    print(f"Confidence: {result['overall_confidence']:.3f}")
    print(f"Requires Review: {result['requires_review']}")
    print(f"Priority: {result['priority']}")
    print(f"Risk Level: {result['risk_level']}")
    print(f"Flags: {result['flags']}")
