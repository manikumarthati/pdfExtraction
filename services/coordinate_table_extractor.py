"""
Coordinate-based table extraction using PDF word coordinates
Handles complex table layouts with proper column boundary detection
"""
from typing import List, Dict, Any, Optional, Tuple
import re

class CoordinateTableExtractor:
    def __init__(self, word_coordinates: List[Dict], tolerance: float = 5.0):
        """
        Initialize with word coordinates from PDF
        
        Args:
            word_coordinates: List of word data with x0, y0, x1, y1, center_x, center_y, text
            tolerance: Y-coordinate tolerance for grouping words into rows
        """
        self.word_coordinates = word_coordinates
        self.tolerance = tolerance
    
    def extract_table_data(self, table_headers: List[str], table_region: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Extract table data using coordinate-based column boundary detection
        
        Args:
            table_headers: List of column header names
            table_region: Optional dict with y_min, y_max to limit extraction area
            
        Returns:
            List of dictionaries representing table rows
        """
        if not table_headers or not self.word_coordinates:
            return []
        
        # Filter words to table region if specified
        relevant_words = self._filter_words_to_region(table_region) if table_region else self.word_coordinates
        
        # Find header positions and establish column boundaries
        column_boundaries = self._establish_column_boundaries(table_headers, relevant_words)
        
        if not column_boundaries:
            return []
        
        # Group words into rows
        rows = self._group_words_into_rows(relevant_words)
        
        # Extract data from each row
        table_data = []
        header_row_y = self._find_header_row_y(table_headers, relevant_words)
        
        for row in rows:
            # Skip header row and empty rows
            if header_row_y and abs(row['y_center'] - header_row_y) < self.tolerance:
                continue
            if not row['words']:
                continue
                
            row_data = self._extract_row_data(row['words'], column_boundaries)
            if any(value for value in row_data.values()):  # Skip completely empty rows
                table_data.append(row_data)
        
        return table_data
    
    def _filter_words_to_region(self, region: Dict) -> List[Dict]:
        """Filter words to specified y-coordinate region"""
        return [
            word for word in self.word_coordinates
            if region.get('y_min', 0) <= word['center_y'] <= region.get('y_max', float('inf'))
        ]
    
    def _establish_column_boundaries(self, table_headers: List[str], words: List[Dict]) -> List[Dict]:
        """
        Establish column boundaries using header positions and midpoint calculation
        
        Returns:
            List of column boundary definitions with left/right x-coordinates
        """
        header_positions = []
        
        # Find position of each header
        for header in table_headers:
            header_words = self._find_header_words(header, words)
            if header_words:
                # Calculate header extent
                left_x = min(word['x0'] for word in header_words)
                right_x = max(word['x1'] for word in header_words)
                center_x = (left_x + right_x) / 2
                
                header_positions.append({
                    'header': header,
                    'left_x': left_x,
                    'right_x': right_x,
                    'center_x': center_x,
                    'words': header_words
                })
        
        if not header_positions:
            return []
        
        # Sort headers by x-position
        sorted_headers = sorted(header_positions, key=lambda h: h['center_x'])
        
        # Calculate column boundaries using midpoints
        column_boundaries = []
        
        for i, header in enumerate(sorted_headers):
            if i == 0:
                # First column: from document left edge to midpoint with next column
                left_boundary = 0
                if i + 1 < len(sorted_headers):
                    right_boundary = (header['center_x'] + sorted_headers[i + 1]['center_x']) / 2
                else:
                    right_boundary = float('inf')
            elif i == len(sorted_headers) - 1:
                # Last column: from midpoint with previous to document right edge
                left_boundary = (sorted_headers[i - 1]['center_x'] + header['center_x']) / 2
                right_boundary = float('inf')
            else:
                # Middle columns: between midpoints with adjacent columns
                left_boundary = (sorted_headers[i - 1]['center_x'] + header['center_x']) / 2
                right_boundary = (header['center_x'] + sorted_headers[i + 1]['center_x']) / 2
            
            column_boundaries.append({
                'header': header['header'],
                'left_x': left_boundary,
                'right_x': right_boundary,
                'header_center': header['center_x']
            })
        
        return column_boundaries
    
    def _find_header_words(self, header_text: str, words: List[Dict]) -> List[Dict]:
        """
        Find words that make up a table header, handling multi-word headers
        """
        header_words = header_text.split()
        if len(header_words) == 1:
            # Single word header - exact match
            return [word for word in words if word['text'].strip() == header_text.strip()]
        
        # Multi-word header - find consecutive words that match
        matched_sequences = []
        
        for i in range(len(words) - len(header_words) + 1):
            word_sequence = words[i:i + len(header_words)]
            sequence_text = ' '.join(word['text'] for word in word_sequence)
            
            if sequence_text.strip() == header_text.strip():
                # Check if words are reasonably close together (same line)
                y_positions = [word['center_y'] for word in word_sequence]
                if max(y_positions) - min(y_positions) <= self.tolerance:
                    matched_sequences.append(word_sequence)
        
        # Return the best match (first found, or could add scoring logic)
        return matched_sequences[0] if matched_sequences else []
    
    def _group_words_into_rows(self, words: List[Dict]) -> List[Dict]:
        """
        Group words into rows based on y-coordinate proximity
        """
        if not words:
            return []
        
        # Sort words by y-coordinate
        sorted_words = sorted(words, key=lambda w: w['center_y'])
        
        rows = []
        current_row = {'words': [sorted_words[0]], 'y_center': sorted_words[0]['center_y']}
        
        for word in sorted_words[1:]:
            if abs(word['center_y'] - current_row['y_center']) <= self.tolerance:
                # Same row
                current_row['words'].append(word)
            else:
                # New row
                rows.append(current_row)
                current_row = {'words': [word], 'y_center': word['center_y']}
        
        # Add the last row
        if current_row['words']:
            rows.append(current_row)
        
        # Sort words within each row by x-coordinate
        for row in rows:
            row['words'] = sorted(row['words'], key=lambda w: w['center_x'])
        
        return rows
    
    def _find_header_row_y(self, table_headers: List[str], words: List[Dict]) -> Optional[float]:
        """Find the y-coordinate of the header row to exclude it from data extraction"""
        for header in table_headers:
            header_words = self._find_header_words(header, words)
            if header_words:
                return sum(word['center_y'] for word in header_words) / len(header_words)
        return None
    
    def _extract_row_data(self, row_words: List[Dict], column_boundaries: List[Dict]) -> Dict[str, Any]:
        """
        Extract data from a single row by assigning words to columns based on boundaries
        """
        row_data = {boundary['header']: None for boundary in column_boundaries}
        
        # Group consecutive words that belong to the same column
        column_word_groups = {boundary['header']: [] for boundary in column_boundaries}
        
        for word in row_words:
            word_center_x = word['center_x']
            
            # Find which column this word belongs to
            assigned_column = None
            for boundary in column_boundaries:
                if boundary['left_x'] <= word_center_x < boundary['right_x']:
                    assigned_column = boundary['header']
                    break
            
            # Fallback: assign to closest column if not within any boundary
            if assigned_column is None:
                closest_boundary = min(
                    column_boundaries,
                    key=lambda b: abs(b['header_center'] - word_center_x)
                )
                assigned_column = closest_boundary['header']
            
            if assigned_column:
                column_word_groups[assigned_column].append(word)
        
        # Convert word groups to text values
        for column, word_group in column_word_groups.items():
            if word_group:
                # Sort words by x-position and combine
                sorted_words = sorted(word_group, key=lambda w: w['x0'])
                combined_text = ' '.join(word['text'] for word in sorted_words).strip()
                row_data[column] = combined_text if combined_text else None
            else:
                row_data[column] = None
        
        return row_data
    
    def get_extraction_debug_info(self, table_headers: List[str]) -> Dict[str, Any]:
        """
        Get debug information about the extraction process
        """
        column_boundaries = self._establish_column_boundaries(table_headers, self.word_coordinates)
        rows = self._group_words_into_rows(self.word_coordinates)
        
        return {
            'total_words': len(self.word_coordinates),
            'total_rows_identified': len(rows),
            'column_boundaries': column_boundaries,
            'header_positions': [
                {
                    'header': boundary['header'],
                    'left_boundary': boundary['left_x'],
                    'right_boundary': boundary['right_x'],
                    'center': boundary['header_center']
                }
                for boundary in column_boundaries
            ]
        }