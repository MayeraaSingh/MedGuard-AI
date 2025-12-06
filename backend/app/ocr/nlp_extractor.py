"""
MedGuard AI - OpenAI/HuggingFace NLP Integration
Advanced entity extraction for degraded OCR text
"""

import logging
import os
from typing import Dict, Any, Optional, List
import re

logger = logging.getLogger(__name__)


class NLPEntityExtractor:
    """Advanced NLP-based entity extraction for low-quality OCR text."""
    
    def __init__(self, provider: str = 'openai', api_key: Optional[str] = None):
        """
        Initialize NLP entity extractor.
        
        Args:
            provider: 'openai' or 'huggingface'
            api_key: API key (reads from env if not provided)
        """
        self.provider = provider
        self.api_key = api_key or os.getenv(f'{provider.upper()}_API_KEY')
        
        if not self.api_key:
            logger.warning(f"No API key found for {provider}. NLP extraction will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"Initialized NLPEntityExtractor with provider={provider}")
    
    def extract_entities(self, text: str, ocr_confidence: float) -> Optional[Dict[str, Any]]:
        """
        Extract entities using NLP when OCR confidence is low.
        
        Args:
            text: OCR-extracted text
            ocr_confidence: OCR confidence score (0-100)
            
        Returns:
            Dictionary of extracted entities or None if not enabled
        """
        if not self.enabled:
            logger.debug("NLP extraction disabled (no API key)")
            return None
        
        # Only use NLP for low-confidence OCR
        if ocr_confidence > 80:
            logger.debug(f"OCR confidence {ocr_confidence}% is high, skipping NLP")
            return None
        
        logger.info(f"Using {self.provider} NLP for entity extraction (OCR confidence: {ocr_confidence}%)")
        
        if self.provider == 'openai':
            return self._extract_with_openai(text)
        elif self.provider == 'huggingface':
            return self._extract_with_huggingface(text)
        else:
            logger.error(f"Unknown provider: {self.provider}")
            return None
    
    def _extract_with_openai(self, text: str) -> Dict[str, Any]:
        """Extract entities using OpenAI API."""
        try:
            import openai
            
            openai.api_key = self.api_key
            
            # Construct prompt for entity extraction
            prompt = f"""Extract the following provider information from this medical document text:
- NPI (10-digit number)
- Provider Name (first and last)
- Medical Degree (MD, DO, NP, etc.)
- Specialty
- Phone Number
- Email Address
- Street Address
- City
- State (2-letter code)
- ZIP Code
- License Number

Text:
{text}

Return as JSON with keys: npi, name, degree, specialty, phone, email, street, city, state, zip, license.
If a field is not found, use null."""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a medical data extraction assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            # Parse JSON response
            import json
            result_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                extracted = json.loads(json_match.group(0))
                
                logger.info(f"OpenAI extracted {len([v for v in extracted.values() if v])} fields")
                return {
                    'extracted': extracted,
                    'confidence': 85,  # High confidence for GPT extraction
                    'method': 'openai_gpt'
                }
            else:
                logger.warning("Could not parse JSON from OpenAI response")
                return None
                
        except ImportError:
            logger.error("openai package not installed. Install with: pip install openai")
            return None
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}")
            return None
    
    def _extract_with_huggingface(self, text: str) -> Dict[str, Any]:
        """Extract entities using HuggingFace transformers."""
        try:
            from transformers import pipeline
            
            # Load NER pipeline
            ner_pipeline = pipeline(
                "ner",
                model="dslim/bert-base-NER",
                aggregation_strategy="simple"
            )
            
            # Extract named entities
            entities = ner_pipeline(text)
            
            # Map entities to provider fields
            extracted = {
                'name': None,
                'city': None,
                'state': None,
                'organization': None
            }
            
            for entity in entities:
                entity_type = entity['entity_group']
                entity_text = entity['word']
                confidence = entity['score']
                
                if entity_type == 'PER' and not extracted['name']:
                    extracted['name'] = entity_text
                elif entity_type == 'LOC':
                    if not extracted['city']:
                        extracted['city'] = entity_text
                    elif not extracted['state']:
                        extracted['state'] = entity_text
                elif entity_type == 'ORG' and not extracted['organization']:
                    extracted['organization'] = entity_text
            
            # Use regex for structured data (NPI, phone, etc.)
            # HuggingFace NER is better for names/locations
            npi_match = re.search(r'\b(\d{10})\b', text)
            if npi_match:
                extracted['npi'] = npi_match.group(1)
            
            phone_match = re.search(r'\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b', text)
            if phone_match:
                extracted['phone'] = phone_match.group(1)
            
            logger.info(f"HuggingFace extracted {len([v for v in extracted.values() if v])} fields")
            return {
                'extracted': extracted,
                'confidence': 75,  # Medium confidence for transformer NER
                'method': 'huggingface_ner'
            }
            
        except ImportError:
            logger.error("transformers package not installed. Install with: pip install transformers torch")
            return None
        except Exception as e:
            logger.error(f"HuggingFace extraction failed: {e}")
            return None
    
    def merge_with_ocr_results(
        self,
        ocr_extraction: Dict[str, Any],
        nlp_extraction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge NLP extraction with OCR extraction, preferring higher confidence.
        
        Args:
            ocr_extraction: Results from EntityParser
            nlp_extraction: Results from NLP extraction
            
        Returns:
            Merged results with confidence scores
        """
        if not nlp_extraction:
            return ocr_extraction
        
        merged = ocr_extraction.copy()
        nlp_data = nlp_extraction['extracted']
        nlp_confidence = nlp_extraction['confidence']
        
        for field, nlp_value in nlp_data.items():
            if not nlp_value:
                continue
            
            # Get OCR value and confidence
            ocr_field = merged.get(field)
            if ocr_field and isinstance(ocr_field, dict):
                ocr_confidence = ocr_field.get('confidence', 0)
                ocr_value = ocr_field.get('value')
            else:
                ocr_confidence = 0
                ocr_value = ocr_field
            
            # Use NLP value if OCR confidence is low or field is missing
            if not ocr_value or ocr_confidence < nlp_confidence:
                merged[field] = {
                    'value': nlp_value,
                    'confidence': nlp_confidence,
                    'method': nlp_extraction['method']
                }
                logger.debug(f"Using NLP value for {field}: {nlp_value}")
        
        return merged


# Singleton instance
_nlp_extractor = None


def get_nlp_extractor(provider: str = 'openai') -> NLPEntityExtractor:
    """Get or create NLP extractor instance."""
    global _nlp_extractor
    
    if _nlp_extractor is None:
        _nlp_extractor = NLPEntityExtractor(provider=provider)
    
    return _nlp_extractor
