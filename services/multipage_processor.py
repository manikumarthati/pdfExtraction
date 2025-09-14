"""
Multi-page PDF processing with intelligent template creation and application
"""
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from .pdf_processor import PDFProcessor
from .openai_service import OpenAIService
from .feedback_analyzer import FeedbackAnalyzer
from .result_merger import ResultMerger

class MultiPageProcessor:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service
        self.feedback_analyzer = FeedbackAnalyzer(openai_service)
        self.result_merger = ResultMerger()

    def get_page_thumbnails(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Get thumbnail info for all pages for user selection"""
        pdf_processor = PDFProcessor(pdf_path)

        thumbnails = []
        for page_num in range(pdf_processor.get_page_count()):
            page_data = pdf_processor.extract_text_and_structure(page_num)

            # Get text preview for user to identify page content
            text_preview = page_data['text'][:200] + "..." if len(page_data['text']) > 200 else page_data['text']

            thumbnails.append({
                'page_number': page_num + 1,  # Human-readable page numbers
                'text_preview': text_preview,
                'page_dimensions': {
                    'width': page_data['page_width'],
                    'height': page_data['page_height']
                },
                'word_count': len(page_data['text'].split()),
                'has_tables': self._detect_potential_tables(page_data['text'])
            })

        pdf_processor.close()
        return thumbnails

    def extract_validation_page(self, pdf_path: str, validation_page_num: int,
                              step1_result: Dict[str, Any], step2_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from user-selected validation page"""
        pdf_processor = PDFProcessor(pdf_path)

        # Extract the specific validation page
        page_data = pdf_processor.extract_text_and_structure(validation_page_num)

        # Use existing extraction logic
        if step2_result.get('extraction_method') == 'vision':
            result = self.openai_service.extract_data_with_vision(
                pdf_path, step2_result, page_num=validation_page_num
            )
        else:
            result = self.openai_service.extract_data(
                page_data['text'], step2_result, page_data.get('word_coordinates')
            )

        # Add page metadata
        result['page_metadata'] = {
            'page_number': validation_page_num + 1,
            'is_validation_page': True,
            'extraction_timestamp': datetime.now().isoformat()
        }

        pdf_processor.close()
        return result

    def create_enhanced_template(self, validation_result: Dict[str, Any],
                               user_feedback: str, step2_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced extraction template from user feedback"""

        # Analyze user feedback to understand corrections
        feedback_analysis = self.feedback_analyzer.analyze_user_feedback(
            user_feedback=user_feedback,
            original_result=validation_result,
            document_structure=step2_structure
        )

        # Generate enhanced extraction instructions
        enhanced_template = {
            'base_structure': step2_structure,
            'extraction_enhancements': feedback_analysis['extraction_enhancements'],
            'validation_rules': feedback_analysis['validation_rules'],
            'enhanced_instructions': feedback_analysis['enhanced_instructions'],
            'template_metadata': {
                'created_from_page': validation_result['page_metadata']['page_number'],
                'feedback_applied': user_feedback,
                'creation_timestamp': datetime.now().isoformat(),
                'template_version': '1.0'
            }
        }

        return enhanced_template

    def process_all_pages(self, pdf_path: str, enhanced_template: Dict[str, Any]) -> Dict[str, Any]:
        """Process all pages using the enhanced template"""
        pdf_processor = PDFProcessor(pdf_path)
        total_pages = pdf_processor.get_page_count()

        # Track processing progress
        processing_status = {
            'total_pages': total_pages,
            'completed_pages': 0,
            'failed_pages': [],
            'page_results': [],
            'processing_start_time': datetime.now().isoformat()
        }

        # Process each page
        for page_num in range(total_pages):
            try:
                page_result = self._process_single_page(
                    pdf_processor, page_num, enhanced_template
                )
                processing_status['page_results'].append(page_result)
                processing_status['completed_pages'] += 1

            except Exception as e:
                error_info = {
                    'page_number': page_num + 1,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                processing_status['failed_pages'].append(error_info)
                print(f"ERROR processing page {page_num + 1}: {str(e)}")

        pdf_processor.close()
        processing_status['processing_end_time'] = datetime.now().isoformat()

        return processing_status

    def _process_single_page(self, pdf_processor: PDFProcessor, page_num: int,
                           enhanced_template: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single page with enhanced template"""

        # Extract page data
        page_data = pdf_processor.extract_text_and_structure(page_num)

        # Use enhanced extraction logic
        if enhanced_template.get('extraction_method') == 'vision':
            result = self.openai_service.extract_data_with_vision_enhanced(
                pdf_processor.pdf_path, enhanced_template, page_num=page_num
            )
        else:
            result = self.openai_service.extract_data_enhanced(
                page_data['text'], enhanced_template, page_data.get('word_coordinates')
            )

        # Add page metadata
        result['page_metadata'] = {
            'page_number': page_num + 1,
            'extraction_timestamp': datetime.now().isoformat(),
            'template_version': enhanced_template['template_metadata']['template_version']
        }

        return result

    def merge_page_results(self, page_results: List[Dict[str, Any]],
                         enhanced_template: Dict[str, Any]) -> Dict[str, Any]:
        """Merge all page extraction results into final document"""

        return self.result_merger.merge_multipage_results(
            page_results=page_results,
            template_metadata=enhanced_template['template_metadata']
        )

    def _detect_potential_tables(self, text: str) -> bool:
        """Quick heuristic to detect if page might contain tables"""
        lines = text.split('\n')

        # Look for patterns that suggest tabular data
        aligned_lines = 0
        for line in lines:
            if len(line.split()) >= 3:  # Multiple columns
                aligned_lines += 1

        return aligned_lines >= 3  # At least 3 lines with multiple columns

    def get_processing_status(self, processing_id: str) -> Dict[str, Any]:
        """Get real-time status of multi-page processing"""
        # This would integrate with a background job system
        # For now, return mock status
        return {
            'processing_id': processing_id,
            'status': 'in_progress',
            'completed_pages': 5,
            'total_pages': 10,
            'estimated_completion': '2 minutes',
            'current_page': 6
        }