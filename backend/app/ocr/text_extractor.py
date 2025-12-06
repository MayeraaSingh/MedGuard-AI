"""
MedGuard AI - Text Extractor
Tesseract OCR integration with confidence scoring
"""

import logging
from typing import Dict, Any, List, Optional
from PIL import Image
import pytesseract
import re

logger = logging.getLogger(__name__)


class TextExtractor:
    """Extract text from images using Tesseract OCR."""
    
    def __init__(self, tesseract_cmd: Optional[str] = None, lang: str = 'eng'):
        """
        Initialize text extractor.
        
        Args:
            tesseract_cmd: Path to tesseract executable (auto-detect if None)
            lang: Language for OCR (default 'eng')
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        self.lang = lang
        logger.info(f"Initialized TextExtractor with language={lang}")
    
    def extract_text(self, image: Image.Image) -> Dict[str, Any]:
        """
        Extract text from image using OCR.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with extracted text and confidence scores
        """
        try:
            # Get detailed OCR data
            ocr_data = pytesseract.image_to_data(
                image,
                lang=self.lang,
                output_type=pytesseract.Output.DICT
            )
            
            # Get plain text
            text = pytesseract.image_to_string(image, lang=self.lang)
            
            # Calculate confidence scores
            confidences = [
                int(conf) for conf in ocr_data['conf']
                if conf != '-1'  # -1 indicates no text detected
            ]
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Count words by confidence level
            high_conf = sum(1 for c in confidences if c >= 80)
            medium_conf = sum(1 for c in confidences if 60 <= c < 80)
            low_conf = sum(1 for c in confidences if c < 60)
            
            result = {
                'text': text.strip(),
                'char_count': len(text),
                'word_count': len(text.split()),
                'line_count': len(text.splitlines()),
                'avg_confidence': round(avg_confidence, 2),
                'confidence_distribution': {
                    'high': high_conf,
                    'medium': medium_conf,
                    'low': low_conf
                },
                'quality_score': self._calculate_quality_score(avg_confidence, text)
            }
            
            logger.info(f"Extracted {result['word_count']} words with {avg_confidence:.1f}% confidence")
            return result
            
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            raise
    
    def extract_with_layout(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Extract text with layout information (bounding boxes).
        
        Args:
            image: PIL Image object
            
        Returns:
            List of text blocks with position and confidence
        """
        try:
            ocr_data = pytesseract.image_to_data(
                image,
                lang=self.lang,
                output_type=pytesseract.Output.DICT
            )
            
            blocks = []
            n_boxes = len(ocr_data['text'])
            
            for i in range(n_boxes):
                text = ocr_data['text'][i].strip()
                conf = int(ocr_data['conf'][i])
                
                if text and conf > 0:  # Only include detected text
                    block = {
                        'text': text,
                        'confidence': conf,
                        'level': ocr_data['level'][i],
                        'page_num': ocr_data['page_num'][i],
                        'block_num': ocr_data['block_num'][i],
                        'line_num': ocr_data['line_num'][i],
                        'word_num': ocr_data['word_num'][i],
                        'left': ocr_data['left'][i],
                        'top': ocr_data['top'][i],
                        'width': ocr_data['width'][i],
                        'height': ocr_data['height'][i]
                    }
                    blocks.append(block)
            
            logger.info(f"Extracted {len(blocks)} text blocks with layout")
            return blocks
            
        except Exception as e:
            logger.error(f"Layout extraction error: {e}")
            raise
    
    def _calculate_quality_score(self, confidence: float, text: str) -> float:
        """
        Calculate overall quality score for OCR result.
        
        Args:
            confidence: Average OCR confidence
            text: Extracted text
            
        Returns:
            Quality score 0-100
        """
        # Base score from confidence
        score = confidence
        
        # Penalty for very short text
        if len(text) < 50:
            score *= 0.8
        
        # Penalty for unusual character ratio
        if text:
            alpha_ratio = sum(c.isalpha() for c in text) / len(text)
            if alpha_ratio < 0.3:  # Less than 30% letters
                score *= 0.9
        
        # Bonus for well-structured text (has newlines, proper spacing)
        if '\n' in text and '  ' not in text:
            score *= 1.05
        
        return min(100, max(0, score))
    
    def assess_ocr_quality(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess OCR quality and provide recommendations.
        
        Args:
            ocr_result: Result from extract_text()
            
        Returns:
            Quality assessment with recommendations
        """
        avg_conf = ocr_result['avg_confidence']
        quality_score = ocr_result['quality_score']
        
        # Determine quality level
        if quality_score >= 80:
            quality = 'excellent'
            recommendation = 'Proceed with entity extraction'
        elif quality_score >= 60:
            quality = 'good'
            recommendation = 'Suitable for extraction, may need validation'
        elif quality_score >= 40:
            quality = 'fair'
            recommendation = 'Consider image preprocessing or manual review'
        else:
            quality = 'poor'
            recommendation = 'Recommend manual data entry or document rescan'
        
        assessment = {
            'quality': quality,
            'quality_score': quality_score,
            'avg_confidence': avg_conf,
            'recommendation': recommendation,
            'requires_review': quality_score < 60,
            'requires_manual_entry': quality_score < 40
        }
        
        logger.info(f"OCR quality: {quality} (score={quality_score:.1f})")
        return assessment
    
    def detect_language(self, image: Image.Image) -> str:
        """
        Detect language of text in image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Language code (e.g., 'eng', 'spa')
        """
        try:
            # Get OSD (Orientation and Script Detection)
            osd = pytesseract.image_to_osd(image)
            
            # Parse language from OSD
            for line in osd.splitlines():
                if line.startswith('Script:'):
                    script = line.split(':')[1].strip()
                    logger.info(f"Detected script: {script}")
                    return 'eng'  # Default to English for now
            
            return 'eng'
            
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return 'eng'
    
    def extract_structured_data(self, image: Image.Image, patterns: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract structured data using regex patterns.
        
        Args:
            image: PIL Image object
            patterns: Dictionary of field names to regex patterns
            
        Returns:
            Dictionary of extracted fields with confidence
        """
        try:
            # Extract text
            ocr_result = self.extract_text(image)
            text = ocr_result['text']
            
            # Extract layout for field-level confidence
            blocks = self.extract_with_layout(image)
            
            extracted = {}
            
            for field_name, pattern in patterns.items():
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                field_values = []
                for match in matches:
                    value = match.group(1) if match.groups() else match.group(0)
                    
                    # Find confidence for this text region
                    confidence = self._find_confidence_for_text(value, blocks)
                    
                    field_values.append({
                        'value': value.strip(),
                        'confidence': confidence,
                        'position': match.span()
                    })
                
                if field_values:
                    # Take highest confidence match
                    best_match = max(field_values, key=lambda x: x['confidence'])
                    extracted[field_name] = best_match
                else:
                    extracted[field_name] = None
            
            logger.info(f"Extracted {len([v for v in extracted.values() if v])} structured fields")
            return extracted
            
        except Exception as e:
            logger.error(f"Structured extraction error: {e}")
            raise
    
    def _find_confidence_for_text(self, text: str, blocks: List[Dict[str, Any]]) -> float:
        """
        Find OCR confidence for a specific text string.
        
        Args:
            text: Text to find
            blocks: OCR blocks with confidence scores
            
        Returns:
            Confidence score 0-100
        """
        # Simple approach: find blocks that contain this text
        confidences = []
        
        for block in blocks:
            if text.lower() in block['text'].lower():
                confidences.append(block['confidence'])
        
        return sum(confidences) / len(confidences) if confidences else 0
