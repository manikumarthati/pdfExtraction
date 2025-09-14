"""
Result merger for combining multi-page extraction results
"""
import json
from typing import Dict, Any, List
from datetime import datetime

class ResultMerger:
    def __init__(self):
        pass

    def merge_multipage_results(self, page_results: List[Dict[str, Any]],
                              template_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge results from all pages into a single structured document
        """

        # Sort results by page number to ensure correct order
        sorted_results = sorted(page_results,
                              key=lambda x: x.get('page_metadata', {}).get('page_number', 0))

        # Initialize merged result structure
        merged_result = {
            'document_metadata': {
                'total_pages': len(page_results),
                'processing_timestamp': datetime.now().isoformat(),
                'template_used': template_metadata,
                'extraction_method': 'multi_page_enhanced'
            },
            'merged_data': {},
            'page_specific_data': [],
            'table_data': [],
            'extraction_summary': {
                'successful_pages': 0,
                'failed_pages': 0,
                'total_fields_extracted': 0,
                'total_table_rows': 0
            }
        }

        # Process each page result
        form_fields = {}
        table_collections = {}

        for page_result in sorted_results:
            page_num = page_result.get('page_metadata', {}).get('page_number', 0)

            try:
                # Process form fields (single values per document)
                if 'extracted_data' in page_result:
                    form_fields.update(
                        self._process_page_form_fields(page_result['extracted_data'], page_num)
                    )

                # Process table data (accumulate rows across pages)
                if 'table_data' in page_result:
                    self._process_page_table_data(
                        page_result['table_data'], table_collections, page_num
                    )

                # Store page-specific information
                merged_result['page_specific_data'].append({
                    'page_number': page_num,
                    'extraction_success': True,
                    'fields_on_page': len(page_result.get('extracted_data', {})),
                    'tables_on_page': len(page_result.get('table_data', [])),
                    'page_metadata': page_result.get('page_metadata', {})
                })

                merged_result['extraction_summary']['successful_pages'] += 1
                merged_result['extraction_summary']['total_fields_extracted'] += len(
                    page_result.get('extracted_data', {})
                )

            except Exception as e:
                print(f"ERROR merging page {page_num}: {str(e)}")
                merged_result['page_specific_data'].append({
                    'page_number': page_num,
                    'extraction_success': False,
                    'error': str(e)
                })
                merged_result['extraction_summary']['failed_pages'] += 1

        # Finalize merged data
        merged_result['merged_data'] = form_fields
        merged_result['table_data'] = self._finalize_table_collections(table_collections)
        merged_result['extraction_summary']['total_table_rows'] = sum(
            len(table.get('rows', [])) for table in merged_result['table_data']
        )

        return merged_result

    def _process_page_form_fields(self, extracted_data: Dict[str, Any], page_num: int) -> Dict[str, Any]:
        """
        Process form fields from a single page
        Form fields typically appear once per document, so we take the first non-null value
        """
        processed_fields = {}

        for field_name, field_value in extracted_data.items():
            if field_value is not None and str(field_value).strip():
                # If field already exists, check if new value is more complete
                if field_name in processed_fields:
                    existing_value = processed_fields[field_name].get('value')
                    if len(str(field_value)) > len(str(existing_value)):
                        processed_fields[field_name] = {
                            'value': field_value,
                            'source_page': page_num,
                            'conflict_detected': True
                        }
                    else:
                        processed_fields[field_name]['conflict_detected'] = True
                else:
                    processed_fields[field_name] = {
                        'value': field_value,
                        'source_page': page_num,
                        'conflict_detected': False
                    }

        return processed_fields

    def _process_page_table_data(self, table_data: List[Dict[str, Any]],
                               table_collections: Dict[str, Dict], page_num: int):
        """
        Process table data from a single page
        Tables accumulate rows across multiple pages
        """
        for table in table_data:
            table_name = table.get('table_name', f'Table_{len(table_collections) + 1}')

            if table_name not in table_collections:
                table_collections[table_name] = {
                    'table_name': table_name,
                    'headers': table.get('headers', []),
                    'rows': [],
                    'source_pages': [],
                    'row_count_by_page': {}
                }

            # Add rows from this page
            page_rows = table.get('rows', [])
            table_collections[table_name]['rows'].extend(page_rows)
            table_collections[table_name]['source_pages'].append(page_num)
            table_collections[table_name]['row_count_by_page'][page_num] = len(page_rows)

    def _finalize_table_collections(self, table_collections: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """
        Finalize table collections with metadata
        """
        finalized_tables = []

        for table_name, table_data in table_collections.items():
            finalized_table = {
                'table_name': table_name,
                'headers': table_data['headers'],
                'rows': table_data['rows'],
                'metadata': {
                    'total_rows': len(table_data['rows']),
                    'source_pages': sorted(table_data['source_pages']),
                    'rows_by_page': table_data['row_count_by_page'],
                    'spans_multiple_pages': len(table_data['source_pages']) > 1
                }
            }
            finalized_tables.append(finalized_table)

        return finalized_tables

    def create_final_json_output(self, merged_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create clean final JSON output for user download
        """

        # Extract clean field values
        clean_fields = {}
        for field_name, field_info in merged_result['merged_data'].items():
            if isinstance(field_info, dict) and 'value' in field_info:
                clean_fields[field_name] = field_info['value']
            else:
                clean_fields[field_name] = field_info

        # Create clean table data
        clean_tables = []
        for table in merged_result['table_data']:
            clean_table = {
                'table_name': table['table_name'],
                'headers': table['headers'],
                'data': table['rows'],
                'total_rows': len(table['rows'])
            }
            clean_tables.append(clean_table)

        # Final clean output
        final_output = {
            'document_info': {
                'total_pages_processed': merged_result['document_metadata']['total_pages'],
                'extraction_date': merged_result['document_metadata']['processing_timestamp'],
                'extraction_method': 'AI-assisted with human validation'
            },
            'extracted_fields': clean_fields,
            'extracted_tables': clean_tables,
            'processing_summary': {
                'total_fields': len(clean_fields),
                'total_tables': len(clean_tables),
                'total_table_rows': sum(table['total_rows'] for table in clean_tables),
                'successful_pages': merged_result['extraction_summary']['successful_pages'],
                'failed_pages': merged_result['extraction_summary']['failed_pages']
            }
        }

        return final_output

    def detect_conflicts_and_anomalies(self, merged_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potential conflicts or anomalies in merged data
        """
        conflicts = {
            'field_conflicts': [],
            'table_anomalies': [],
            'structural_issues': [],
            'confidence_warnings': []
        }

        # Check for field conflicts
        for field_name, field_info in merged_result['merged_data'].items():
            if isinstance(field_info, dict) and field_info.get('conflict_detected'):
                conflicts['field_conflicts'].append({
                    'field': field_name,
                    'issue': 'Multiple different values found across pages',
                    'resolution': 'Using longest/most complete value'
                })

        # Check for table anomalies
        for table in merged_result['table_data']:
            if table['metadata']['spans_multiple_pages']:
                # Check for header consistency across pages
                row_lengths = [len(row) for row in table['rows'] if isinstance(row, dict)]
                if len(set(row_lengths)) > 1:
                    conflicts['table_anomalies'].append({
                        'table': table['table_name'],
                        'issue': 'Inconsistent row structure across pages',
                        'details': f"Row lengths vary: {set(row_lengths)}"
                    })

        return conflicts