"""
MedGuard AI - OCR Orchestrator
Coordinates PDF→OCR→Entity extraction→Validation pipeline
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import time

from .pdf_processor import PDFProcessor
from .text_extractor import TextExtractor
from .entity_parser import EntityParser

logger = logging.getLogger(__name__)


class OCROrchestrator:
    """Orchestrate the complete OCR pipeline for provider document processing."""
    
    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        dpi: int = 300,
        fuzzy_threshold: int = 80
    ):
        """
        Initialize OCR orchestrator.
        
        Args:
            tesseract_cmd: Path to tesseract executable (auto-detect if None)
            dpi: Resolution for PDF→Image conversion
            fuzzy_threshold: Minimum fuzzy match score for entity extraction
        """
        self.pdf_processor = PDFProcessor(dpi=dpi)
        self.text_extractor = TextExtractor(tesseract_cmd=tesseract_cmd)
        self.entity_parser = EntityParser(fuzzy_threshold=fuzzy_threshold)
        
        logger.info("Initialized OCROrchestrator")
    
    def process_pdf(self, pdf_path: str, pages: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Process a single PDF through the complete OCR pipeline.
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to process (1-indexed). If None, process all.
            
        Returns:
            Dictionary with OCR results and extracted provider data
        """
        start_time = time.time()
        pdf_path = Path(pdf_path)
        
        logger.info(f"Starting OCR pipeline for: {pdf_path.name}")
        
        try:
            # Step 1: Load and assess PDF
            logger.info("Step 1: Loading PDF...")
            pdf_metadata = self.pdf_processor.load_pdf(pdf_path)
            quality_assessment = self.pdf_processor.assess_pdf_quality(pdf_path)
            
            # Step 2: Extract text from PDF pages
            logger.info("Step 2: Extracting text...")
            pdf_pages = self.pdf_processor.extract_pages(pdf_path, pages)
            
            # Step 3: If scanned PDF, perform OCR
            ocr_results = []
            
            if quality_assessment['requires_ocr']:
                logger.info("Step 3: Converting to images and performing OCR...")
                images = self.pdf_processor.pdf_to_images(pdf_path, pages)
                
                for img_data in images:
                    # Preprocess image
                    processed_img = self.pdf_processor.preprocess_image(img_data['image'])
                    
                    # Extract text with OCR
                    ocr_result = self.text_extractor.extract_text(processed_img)
                    ocr_result['page_number'] = img_data['page_number']
                    
                    # Quality assessment
                    quality = self.text_extractor.assess_ocr_quality(ocr_result)
                    ocr_result['quality_assessment'] = quality
                    
                    ocr_results.append(ocr_result)
                    
                    logger.info(
                        f"  Page {img_data['page_number']}: "
                        f"{ocr_result['word_count']} words, "
                        f"{ocr_result['avg_confidence']:.1f}% confidence"
                    )
            else:
                # Use extracted PDF text
                logger.info("Step 3: Using embedded PDF text (no OCR needed)")
                for page in pdf_pages:
                    ocr_results.append({
                        'page_number': page['page_number'],
                        'text': page['text'],
                        'char_count': len(page['text']),
                        'word_count': len(page['text'].split()),
                        'line_count': len(page['text'].splitlines()),
                        'avg_confidence': 100,  # Embedded text is 100% confident
                        'quality_score': 100,
                        'quality_assessment': {
                            'quality': 'excellent',
                            'requires_review': False
                        }
                    })
            
            # Step 4: Combine text from all pages
            logger.info("Step 4: Combining text from all pages...")
            combined_text = '\n\n'.join([r['text'] for r in ocr_results])
            
            # Step 5: Extract provider entities
            logger.info("Step 5: Extracting provider entities...")
            provider_data = self.entity_parser.parse_provider(combined_text)
            
            # Step 6: Validate extracted data
            logger.info("Step 6: Validating extracted data...")
            validation_result = self.entity_parser.validate_extracted_data(provider_data)
            
            # Calculate overall confidence
            avg_ocr_confidence = sum(r['avg_confidence'] for r in ocr_results) / len(ocr_results)
            extraction_confidence = provider_data.get('extraction_confidence', 0)
            overall_confidence = (avg_ocr_confidence * 0.4 + extraction_confidence * 0.6)
            
            duration = time.time() - start_time
            
            result = {
                'success': True,
                'file_name': pdf_path.name,
                'file_path': str(pdf_path),
                'pdf_metadata': pdf_metadata,
                'quality_assessment': quality_assessment,
                'ocr_results': ocr_results,
                'combined_text': combined_text,
                'provider_data': provider_data,
                'validation': validation_result,
                'confidence': {
                    'ocr_confidence': round(avg_ocr_confidence, 2),
                    'extraction_confidence': round(extraction_confidence, 2),
                    'overall_confidence': round(overall_confidence, 2)
                },
                'processing_time': round(duration, 2),
                'requires_review': (
                    overall_confidence < 70 or
                    validation_result['requires_review'] or
                    any(r['quality_assessment'].get('requires_review', False) for r in ocr_results)
                )
            }
            
            logger.info(
                f"✓ OCR pipeline complete: "
                f"{overall_confidence:.1f}% confidence, "
                f"{duration:.2f}s"
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"OCR pipeline failed: {e}")
            
            return {
                'success': False,
                'file_name': pdf_path.name,
                'file_path': str(pdf_path),
                'error': str(e),
                'processing_time': round(duration, 2)
            }
    
    def process_batch(
        self,
        pdf_paths: List[str],
        max_workers: int = 4
    ) -> Dict[str, Any]:
        """
        Process multiple PDFs in batch.
        
        Args:
            pdf_paths: List of PDF file paths
            max_workers: Maximum parallel workers (not implemented yet)
            
        Returns:
            Dictionary with batch processing results
        """
        start_time = time.time()
        
        logger.info(f"Starting batch OCR for {len(pdf_paths)} PDFs")
        
        results = []
        successful = 0
        failed = 0
        
        for pdf_path in pdf_paths:
            result = self.process_pdf(pdf_path)
            results.append(result)
            
            if result['success']:
                successful += 1
            else:
                failed += 1
        
        duration = time.time() - start_time
        
        # Calculate aggregate statistics
        avg_confidence = sum(
            r['confidence']['overall_confidence']
            for r in results if r['success']
        ) / successful if successful > 0 else 0
        
        total_pages = sum(
            len(r['ocr_results'])
            for r in results if r['success']
        )
        
        batch_result = {
            'total_pdfs': len(pdf_paths),
            'successful': successful,
            'failed': failed,
            'total_pages': total_pages,
            'avg_confidence': round(avg_confidence, 2),
            'total_time': round(duration, 2),
            'avg_time_per_pdf': round(duration / len(pdf_paths), 2) if pdf_paths else 0,
            'results': results
        }
        
        logger.info(
            f"✓ Batch OCR complete: "
            f"{successful}/{len(pdf_paths)} successful, "
            f"{avg_confidence:.1f}% avg confidence, "
            f"{duration:.2f}s total"
        )
        
        return batch_result
    
    def extract_to_validation_format(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert OCR result to format compatible with Phase 2 validation agents.
        
        Args:
            ocr_result: Result from process_pdf()
            
        Returns:
            Provider data formatted for validation pipeline
        """
        if not ocr_result['success']:
            return None
        
        provider_data = ocr_result['provider_data']
        
        # Extract values from nested structure
        def get_value(field):
            if field and isinstance(field, dict):
                return field.get('value')
            return field
        
        # Handle address specially
        address = get_value(provider_data.get('address'))
        if isinstance(address, dict):
            address_line = address.get('street', '')
            city = address.get('city', '')
            state = address.get('state', '')
            zip_code = address.get('zip', '')
        else:
            address_line = city = state = zip_code = ''
        
        validation_format = {
            'npi': get_value(provider_data.get('npi')),
            'first_name': get_value(provider_data.get('name', '')).split()[0] if get_value(provider_data.get('name')) else '',
            'last_name': ' '.join(get_value(provider_data.get('name', '')).split()[1:]) if get_value(provider_data.get('name')) else '',
            'degree': get_value(provider_data.get('degree')),
            'specialty': get_value(provider_data.get('specialty')),
            'phone': get_value(provider_data.get('phone')),
            'email': get_value(provider_data.get('email')),
            'address_line1': address_line,
            'city': city,
            'state': state,
            'zip_code': zip_code,
            'license_number': get_value(provider_data.get('license')),
            'source': 'ocr',
            'source_file': ocr_result['file_name'],
            'ocr_confidence': ocr_result['confidence']['overall_confidence']
        }
        
        return validation_format
    
    def generate_ocr_report(self, batch_result: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Generate human-readable report of OCR batch processing.
        
        Args:
            batch_result: Result from process_batch()
            output_path: Optional path to save report
            
        Returns:
            Report text
        """
        lines = []
        lines.append("=" * 70)
        lines.append("MEDGUARD AI - OCR PROCESSING REPORT")
        lines.append("=" * 70)
        lines.append("")
        
        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 70)
        lines.append(f"Total PDFs Processed: {batch_result['total_pdfs']}")
        lines.append(f"Successful: {batch_result['successful']}")
        lines.append(f"Failed: {batch_result['failed']}")
        lines.append(f"Total Pages: {batch_result['total_pages']}")
        lines.append(f"Average Confidence: {batch_result['avg_confidence']:.2f}%")
        lines.append(f"Total Processing Time: {batch_result['total_time']:.2f}s")
        lines.append(f"Average Time Per PDF: {batch_result['avg_time_per_pdf']:.2f}s")
        lines.append("")
        
        # Per-file results
        lines.append("DETAILED RESULTS")
        lines.append("-" * 70)
        
        for result in batch_result['results']:
            if result['success']:
                lines.append(f"\n[PASS] {result['file_name']}")
                lines.append(f"  Pages: {len(result['ocr_results'])}")
                lines.append(f"  Overall Confidence: {result['confidence']['overall_confidence']:.1f}%")
                lines.append(f"  Processing Time: {result['processing_time']:.2f}s")
                lines.append(f"  Quality: {result['quality_assessment']['quality']}")
                lines.append(f"  Requires Review: {result['requires_review']}")
                
                # Show extracted fields
                provider = result['provider_data']
                extracted = [k for k, v in provider.items() if v and k != 'extraction_confidence']
                lines.append(f"  Extracted Fields: {', '.join(extracted)}")
                
                if result['validation']['issues']:
                    lines.append(f"  Issues: {', '.join(result['validation']['issues'])}")
                if result['validation']['warnings']:
                    lines.append(f"  Warnings: {', '.join(result['validation']['warnings'])}")
            else:
                lines.append(f"\n[FAIL] {result['file_name']}")
                lines.append(f"  Error: {result['error']}")
        
        lines.append("")
        lines.append("=" * 70)
        
        report = '\n'.join(lines)
        
        # Save if output path provided
        if output_path:
            Path(output_path).write_text(report)
            logger.info(f"Report saved to: {output_path}")
        
        return report
