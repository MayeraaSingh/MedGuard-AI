"""
MedGuard AI - PDF Processor
Handles PDF loading, page extraction, and PDF→Image conversion
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image
import PyPDF2
import io

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Process PDF files for OCR extraction."""
    
    def __init__(self, dpi: int = 300):
        """
        Initialize PDF processor.
        
        Args:
            dpi: Resolution for PDF→Image conversion (default 300 for OCR)
        """
        self.dpi = dpi
        logger.info(f"Initialized PDFProcessor with DPI={dpi}")
    
    def load_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Load PDF file and extract metadata.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with PDF metadata and pages
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Extract metadata
                metadata = {
                    'file_path': str(pdf_path),
                    'file_name': pdf_path.name,
                    'file_size': pdf_path.stat().st_size,
                    'num_pages': len(pdf_reader.pages),
                    'is_encrypted': pdf_reader.is_encrypted,
                    'metadata': {}
                }
                
                # Get PDF metadata if available
                if pdf_reader.metadata:
                    metadata['metadata'] = {
                        'title': pdf_reader.metadata.get('/Title', ''),
                        'author': pdf_reader.metadata.get('/Author', ''),
                        'subject': pdf_reader.metadata.get('/Subject', ''),
                        'creator': pdf_reader.metadata.get('/Creator', ''),
                    }
                
                logger.info(f"Loaded PDF: {pdf_path.name} ({metadata['num_pages']} pages)")
                return metadata
                
        except Exception as e:
            logger.error(f"Error loading PDF {pdf_path}: {e}")
            raise
    
    def extract_pages(self, pdf_path: str, page_numbers: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Extract specific pages from PDF.
        
        Args:
            pdf_path: Path to PDF file
            page_numbers: List of page numbers to extract (1-indexed). If None, extract all pages.
            
        Returns:
            List of page dictionaries with text and metadata
        """
        pdf_path = Path(pdf_path)
        pages = []
        
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Default to all pages if not specified
                if page_numbers is None:
                    page_numbers = list(range(1, len(pdf_reader.pages) + 1))
                
                for page_num in page_numbers:
                    # Convert to 0-indexed
                    page_idx = page_num - 1
                    
                    if page_idx < 0 or page_idx >= len(pdf_reader.pages):
                        logger.warning(f"Page {page_num} out of range, skipping")
                        continue
                    
                    page = pdf_reader.pages[page_idx]
                    
                    # Extract text (may be empty for scanned PDFs)
                    try:
                        text = page.extract_text()
                    except Exception as e:
                        logger.warning(f"Could not extract text from page {page_num}: {e}")
                        text = ""
                    
                    page_data = {
                        'page_number': page_num,
                        'text': text,
                        'has_text': bool(text.strip()),
                        'width': float(page.mediabox.width),
                        'height': float(page.mediabox.height)
                    }
                    
                    pages.append(page_data)
                    logger.debug(f"Extracted page {page_num}: {len(text)} chars")
                
                logger.info(f"Extracted {len(pages)} pages from {pdf_path.name}")
                return pages
                
        except Exception as e:
            logger.error(f"Error extracting pages from {pdf_path}: {e}")
            raise
    
    def pdf_to_images(self, pdf_path: str, page_numbers: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Convert PDF pages to images for OCR.
        
        Args:
            pdf_path: Path to PDF file
            page_numbers: List of page numbers to convert (1-indexed). If None, convert all pages.
            
        Returns:
            List of page dictionaries with PIL Image objects
        """
        try:
            # Use pdf2image if available, otherwise fallback to PyMuPDF
            try:
                from pdf2image import convert_from_path
                
                # Convert PDF to images
                if page_numbers:
                    # pdf2image uses 1-indexed pages
                    images = convert_from_path(
                        pdf_path,
                        dpi=self.dpi,
                        first_page=min(page_numbers),
                        last_page=max(page_numbers)
                    )
                else:
                    images = convert_from_path(pdf_path, dpi=self.dpi)
                
                results = []
                for idx, image in enumerate(images, start=1):
                    results.append({
                        'page_number': idx,
                        'image': image,
                        'width': image.width,
                        'height': image.height,
                        'mode': image.mode,
                        'dpi': self.dpi
                    })
                
                logger.info(f"Converted {len(results)} pages to images at {self.dpi} DPI")
                return results
                
            except ImportError:
                # Fallback: Try PyMuPDF (fitz)
                try:
                    import fitz  # PyMuPDF
                    
                    doc = fitz.open(pdf_path)
                    results = []
                    
                    # Default to all pages if not specified
                    if page_numbers is None:
                        page_numbers = list(range(1, len(doc) + 1))
                    
                    for page_num in page_numbers:
                        page_idx = page_num - 1
                        
                        if page_idx < 0 or page_idx >= len(doc):
                            continue
                        
                        page = doc[page_idx]
                        
                        # Convert to image
                        mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
                        pix = page.get_pixmap(matrix=mat)
                        
                        # Convert to PIL Image
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        
                        results.append({
                            'page_number': page_num,
                            'image': img,
                            'width': img.width,
                            'height': img.height,
                            'mode': img.mode,
                            'dpi': self.dpi
                        })
                    
                    doc.close()
                    logger.info(f"Converted {len(results)} pages to images using PyMuPDF")
                    return results
                    
                except ImportError:
                    # Last resort: Simple extraction with PyPDF2 (limited quality)
                    logger.warning("pdf2image and PyMuPDF not available. Using PyPDF2 (limited quality)")
                    
                    # For now, return empty list and log warning
                    # In production, would recommend installing pdf2image
                    logger.error("Cannot convert PDF to images without pdf2image or PyMuPDF")
                    return []
        
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            raise
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results.
        
        Args:
            image: PIL Image object
            
        Returns:
            Preprocessed PIL Image
        """
        try:
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Increase contrast (simple approach)
            from PIL import ImageEnhance
            
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Increase sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            logger.debug("Preprocessed image for OCR")
            return image
            
        except Exception as e:
            logger.warning(f"Error preprocessing image: {e}")
            return image
    
    def assess_pdf_quality(self, pdf_path: str) -> Dict[str, Any]:
        """
        Assess PDF quality for OCR readiness.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with quality assessment
        """
        try:
            metadata = self.load_pdf(pdf_path)
            pages = self.extract_pages(pdf_path)
            
            # Calculate metrics
            total_text = sum(len(p['text']) for p in pages)
            pages_with_text = sum(1 for p in pages if p['has_text'])
            
            # Determine if PDF is scanned or text-based
            is_scanned = pages_with_text < len(pages) * 0.5
            
            # Estimate quality
            if pages_with_text == len(pages) and total_text > 500:
                quality = 'high'  # Text-based PDF with content
            elif is_scanned:
                quality = 'low'   # Scanned PDF, needs OCR
            else:
                quality = 'medium'
            
            assessment = {
                'file_name': metadata['file_name'],
                'num_pages': metadata['num_pages'],
                'total_chars': total_text,
                'pages_with_text': pages_with_text,
                'is_scanned': is_scanned,
                'quality': quality,
                'requires_ocr': is_scanned or total_text < 100
            }
            
            logger.info(f"PDF quality assessment: {quality} (scanned={is_scanned})")
            return assessment
            
        except Exception as e:
            logger.error(f"Error assessing PDF quality: {e}")
            raise
