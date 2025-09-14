import re
import math
from typing import List, Dict, Any, Tuple, Optional

class SpatialPreprocessor:
    """
    Preprocesses word coordinates to identify field structures and format text 
    for improved LLM understanding of document layout
    """
    
    def __init__(self, proximity_threshold_multiplier: float = 2.0):
        """
        Initialize spatial preprocessor
        
        Args:
            proximity_threshold_multiplier: Multiplier for average spacing to determine word groupings
        """
        self.proximity_threshold_multiplier = proximity_threshold_multiplier
        self.field_keywords = [
            'name', 'id', 'number', 'no', 'code', 'date', 'time', 'status', 'type',
            'group', 'class', 'category', 'dept', 'department', 'title', 'position', 
            'employee', 'emp', 'staff', 'person', 'user', 'customer', 'client',
            'address', 'phone', 'email', 'ssn', 'tax', 'salary', 'rate', 'amount',
            'total', 'sum', 'balance', 'payment', 'account', 'reference', 'ref'
        ]
    
    def preprocess_document(self, word_coordinates: List[Dict[str, Any]]) -> str:
        """
        Main preprocessing function that converts word coordinates into 
        spatially-formatted text for LLM consumption
        
        Args:
            word_coordinates: List of word dictionaries with coordinate information
            
        Returns:
            Formatted text string with proper spacing and field identification
        """
        if not word_coordinates:
            return ""
        
        # Group words into lines
        lines = self.group_words_into_lines(word_coordinates)
        
        # Process lines with multi-line field-value pair detection
        formatted_lines = self.process_multiline_fields(lines)
        
        return "\n".join(formatted_lines)
    
    def process_multiline_fields(self, lines: List[List[Dict[str, Any]]]) -> List[str]:
        """
        Process lines with awareness of multi-line field-value patterns
        
        Args:
            lines: List of lines, where each line is a list of words
            
        Returns:
            List of formatted text lines
        """
        formatted_lines = []
        i = 0
        
        while i < len(lines):
            current_line = lines[i]
            
            # Check if this line contains field patterns
            if self.line_contains_field_patterns(current_line):
                # Process with potential next line for values
                next_line = lines[i + 1] if i + 1 < len(lines) else None
                formatted_text = self.process_field_line_with_values(current_line, next_line)
                
                # Check if we consumed the next line
                if next_line and self.is_value_line_for_fields(current_line, next_line):
                    formatted_lines.append(formatted_text)
                    i += 2  # Skip the next line as it was consumed
                else:
                    formatted_lines.append(formatted_text)
                    i += 1
            else:
                # Regular line processing
                formatted_line = self.process_line_for_fields(current_line)
                if formatted_line.strip():
                    formatted_lines.append(formatted_line)
                i += 1
        
        return formatted_lines
    
    def line_contains_field_patterns(self, line_words: List[Dict[str, Any]]) -> bool:
        """Check if a line contains field patterns"""
        if not line_words:
            return False
            
        # Look for field-like words in the line
        for word in line_words:
            if self.is_field_pattern([word]):
                return True
        return False
    
    def is_value_line_for_fields(self, field_line: List[Dict[str, Any]], value_line: List[Dict[str, Any]]) -> bool:
        """
        Determine if the value_line contains values for fields in field_line
        
        Args:
            field_line: Line containing potential field labels
            value_line: Line that might contain corresponding values
            
        Returns:
            True if value_line appears to contain values for field_line
        """
        if not field_line or not value_line:
            return False
        
        # Check if value line words are positioned under field line words
        field_x_positions = [w['center_x'] for w in field_line]
        value_x_positions = [w['center_x'] for w in value_line]
        
        # Check for vertical alignment (values under fields)
        alignments = 0
        tolerance = 30  # pixels
        
        for field_x in field_x_positions:
            for value_x in value_x_positions:
                if abs(field_x - value_x) <= tolerance:
                    alignments += 1
                    break
        
        # If at least one field has a value below it, consider it a value line
        return alignments > 0
    
    def process_field_line_with_values(self, field_line: List[Dict[str, Any]], value_line: List[Dict[str, Any]] = None) -> str:
        """
        Process a field line and associate it with values from the next line
        
        Args:
            field_line: Line containing field labels
            value_line: Optional line containing values
            
        Returns:
            Formatted text with field-value pairs
        """
        if not field_line:
            return ""
        
        # Group field line into clusters
        field_clusters = self.cluster_words_by_proximity(field_line)
        
        # Group value line into clusters if available
        value_clusters = []
        if value_line:
            value_clusters = self.cluster_words_by_proximity(value_line)
        
        # Match field clusters to value clusters by position
        field_value_pairs = []
        
        for field_cluster in field_clusters:
            if self.is_field_pattern(field_cluster):
                field_name = " ".join([w["text"] for w in field_cluster])
                field_center_x = sum(w['center_x'] for w in field_cluster) / len(field_cluster)
                
                # Find matching value cluster by X position
                best_value = None
                min_distance = float('inf')
                tolerance = 50  # pixels
                
                for value_cluster in value_clusters:
                    value_center_x = sum(w['center_x'] for w in value_cluster) / len(value_cluster)
                    distance = abs(field_center_x - value_center_x)
                    
                    if distance <= tolerance and distance < min_distance:
                        if not self.is_field_pattern(value_cluster):  # Make sure it's not another field
                            best_value = " ".join([w["text"] for w in value_cluster])
                            min_distance = distance
                
                if best_value:
                    field_value_pairs.append(f"{field_name}:\t{best_value}")
                else:
                    field_value_pairs.append(f"{field_name}:\t[EMPTY]")
            else:
                # Not a field pattern, just add as regular text
                cluster_text = " ".join([w["text"] for w in field_cluster])
                field_value_pairs.append(cluster_text)
        
        return "    ".join(field_value_pairs)
    
    def group_words_into_lines(self, words: List[Dict[str, Any]], y_tolerance: float = 5.0) -> List[List[Dict[str, Any]]]:
        """
        Group words that are on the same horizontal line
        
        Args:
            words: List of word dictionaries
            y_tolerance: Maximum Y-coordinate difference to consider words on same line
            
        Returns:
            List of lines, where each line is a list of words
        """
        if not words:
            return []
        
        # Sort words by Y coordinate first, then X coordinate
        sorted_words = sorted(words, key=lambda w: (w["y0"], w["x0"]))
        
        lines = []
        current_line = [sorted_words[0]]
        current_y = sorted_words[0]["y0"]
        
        for word in sorted_words[1:]:
            # Check if word is on the same line (within Y tolerance)
            if abs(word["y0"] - current_y) <= y_tolerance:
                current_line.append(word)
            else:
                # Sort current line by X coordinate and add to lines
                current_line.sort(key=lambda w: w["x0"])
                lines.append(current_line)
                
                # Start new line
                current_line = [word]
                current_y = word["y0"]
        
        # Add the last line
        if current_line:
            current_line.sort(key=lambda w: w["x0"])
            lines.append(current_line)
        
        return lines
    
    def process_line_for_fields(self, line_words: List[Dict[str, Any]]) -> str:
        """
        Process a line of words to identify field patterns and format appropriately
        
        Args:
            line_words: List of words on the same line
            
        Returns:
            Formatted line string
        """
        if not line_words:
            return ""
        
        # Calculate word spacing to identify clusters
        word_clusters = self.cluster_words_by_proximity(line_words)
        
        # Identify field patterns in clusters
        formatted_parts = []
        for cluster in word_clusters:
            cluster_text = " ".join([w["text"] for w in cluster])
            
            # Check if this cluster represents a field pattern
            if self.is_field_pattern(cluster):
                formatted_field = self.format_as_field_cluster(cluster, word_clusters)
                formatted_parts.append(formatted_field)
            else:
                formatted_parts.append(cluster_text)
        
        return "    ".join(formatted_parts)  # Use consistent spacing between clusters
    
    def cluster_words_by_proximity(self, line_words: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Cluster words on a line based on their spatial proximity
        
        Args:
            line_words: Words on the same line, sorted by X coordinate
            
        Returns:
            List of word clusters
        """
        if len(line_words) <= 1:
            return [line_words]
        
        # Calculate average spacing between consecutive words
        spacings = []
        for i in range(len(line_words) - 1):
            current_word = line_words[i]
            next_word = line_words[i + 1]
            spacing = next_word["x0"] - current_word["x1"]
            spacings.append(spacing)
        
        if not spacings:
            return [line_words]
        
        avg_spacing = sum(spacings) / len(spacings)
        cluster_threshold = avg_spacing * self.proximity_threshold_multiplier
        
        # Group words into clusters based on spacing
        clusters = []
        current_cluster = [line_words[0]]
        
        for i in range(1, len(line_words)):
            spacing = line_words[i]["x0"] - line_words[i-1]["x1"]
            
            if spacing <= cluster_threshold:
                current_cluster.append(line_words[i])
            else:
                clusters.append(current_cluster)
                current_cluster = [line_words[i]]
        
        clusters.append(current_cluster)
        return clusters
    
    def is_field_pattern(self, word_cluster: List[Dict[str, Any]]) -> bool:
        """
        Determine if a word cluster represents a field label pattern
        
        Args:
            word_cluster: List of words in the cluster
            
        Returns:
            True if cluster appears to be a field label
        """
        if not word_cluster:
            return False
        
        cluster_text = " ".join([w["text"].lower() for w in word_cluster])
        original_text = " ".join([w["text"] for w in word_cluster])
        
        # Skip obvious value patterns (numbers, dates, single letters)
        if self.is_obvious_value_pattern(original_text):
            return False
        
        # Pattern 1: Contains field keywords
        if any(keyword in cluster_text for keyword in self.field_keywords):
            return True
        
        # Pattern 2: Ends with common field indicators
        field_endings = [':', '#', 'no', 'id', 'code', 'name', 'date', 'type', 'status', 'group']
        if any(cluster_text.endswith(ending) for ending in field_endings):
            return True
        
        # Pattern 3: Title case pattern (multiple capitalized words) - but not all caps
        words = [w["text"] for w in word_cluster]
        if len(words) >= 2:
            title_case_count = sum(1 for word in words if word and word[0].isupper() and not word.isupper())
            if title_case_count >= len(words) * 0.7:  # At least 70% are title case
                return True
        
        # Pattern 4: Common field names (case-insensitive)
        common_fields = ['status', 'emp', 'employee', 'position', 'title', 'gender', 'marital', 
                        'hire', 'term', 'supervisor', 'department', 'division', 'location']
        if any(field in cluster_text for field in common_fields):
            return True
        
        # Pattern 5: Ends with specific field words
        field_words = original_text.split()
        if field_words:
            last_word = field_words[-1].lower()
            if last_word in ['id', 'no', 'type', 'code', 'date', 'status', 'group', 'name', 'title']:
                return True
        
        return False
    
    def is_obvious_value_pattern(self, text: str) -> bool:
        """
        Check if text is obviously a value, not a field label
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears to be a value
        """
        text = text.strip()
        
        # Single letter (like "A", "M", "S")
        if len(text) == 1 and text.isalpha():
            return True
        
        # Pure numbers
        if text.replace('.', '').replace(',', '').replace('-', '').replace('/', '').isdigit():
            return True
        
        # Currency amounts
        if text.startswith('$') or text.endswith('%'):
            return True
        
        # Dates (MM/DD/YYYY pattern)
        import re
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', text):
            return True
        
        # Phone numbers
        if re.match(r'\d{3}-\d{3}-\d{4}', text):
            return True
        
        # SSN pattern
        if re.match(r'\d{3}-\d{2}-\d{4}', text):
            return True
        
        # All uppercase short codes (but not field names)
        if text.isupper() and len(text) <= 6 and not any(keyword in text.lower() for keyword in self.field_keywords):
            return True
        
        return False
    
    def format_as_field_cluster(self, field_cluster: List[Dict[str, Any]], all_clusters: List[List[Dict[str, Any]]]) -> str:
        """
        Format a field cluster with proper spacing for LLM understanding
        
        Args:
            field_cluster: The cluster identified as a field
            all_clusters: All clusters on the line for context
            
        Returns:
            Formatted field string
        """
        field_name = " ".join([w["text"] for w in field_cluster])
        
        # Find the next cluster (potential field value)
        try:
            field_index = all_clusters.index(field_cluster)
            if field_index < len(all_clusters) - 1:
                value_cluster = all_clusters[field_index + 1]
                field_value = " ".join([w["text"] for w in value_cluster])
                
                # Check if value cluster also looks like a field (indicates current field is empty)
                if self.is_field_pattern(value_cluster):
                    return f"{field_name}:\t[EMPTY]"
                else:
                    return f"{field_name}:\t{field_value}"
            else:
                return f"{field_name}:\t[EMPTY]"
        except ValueError:
            return f"{field_name}:\t[EMPTY]"
    
    def calculate_word_spacing_stats(self, word_coordinates: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate statistics about word spacing in the document
        
        Args:
            word_coordinates: List of word dictionaries
            
        Returns:
            Dictionary with spacing statistics
        """
        if len(word_coordinates) < 2:
            return {"avg_spacing": 0, "median_spacing": 0, "spacing_std": 0}
        
        spacings = []
        sorted_words = sorted(word_coordinates, key=lambda w: (w["y0"], w["x0"]))
        
        for i in range(len(sorted_words) - 1):
            current = sorted_words[i]
            next_word = sorted_words[i + 1]
            
            # Only calculate spacing for words on the same line
            if abs(current["y0"] - next_word["y0"]) <= 5:
                spacing = next_word["x0"] - current["x1"]
                if spacing >= 0:  # Ignore overlapping words
                    spacings.append(spacing)
        
        if not spacings:
            return {"avg_spacing": 0, "median_spacing": 0, "spacing_std": 0}
        
        avg_spacing = sum(spacings) / len(spacings)
        sorted_spacings = sorted(spacings)
        median_spacing = sorted_spacings[len(sorted_spacings) // 2]
        
        # Calculate standard deviation
        variance = sum((s - avg_spacing) ** 2 for s in spacings) / len(spacings)
        spacing_std = math.sqrt(variance)
        
        return {
            "avg_spacing": avg_spacing,
            "median_spacing": median_spacing, 
            "spacing_std": spacing_std
        }
    
    def identify_table_regions(self, word_coordinates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify potential table regions based on word alignment patterns
        
        Args:
            word_coordinates: List of word dictionaries
            
        Returns:
            List of table region dictionaries
        """
        lines = self.group_words_into_lines(word_coordinates)
        table_regions = []
        
        # Look for lines with consistent column alignment
        potential_table_lines = []
        for line_words in lines:
            if len(line_words) >= 3:  # Minimum columns for a table
                x_positions = [w["x0"] for w in line_words]
                # Check if X positions show regular spacing (table-like)
                if self.has_regular_spacing(x_positions):
                    potential_table_lines.append(line_words)
        
        # Group consecutive table lines
        if potential_table_lines:
            current_table = [potential_table_lines[0]]
            
            for i in range(1, len(potential_table_lines)):
                # Check if this line is vertically close to the previous
                prev_line_y = max(w["y1"] for w in current_table[-1])
                curr_line_y = min(w["y0"] for w in potential_table_lines[i])
                
                if curr_line_y - prev_line_y <= 20:  # Within reasonable line spacing
                    current_table.append(potential_table_lines[i])
                else:
                    # Save current table and start new one
                    if len(current_table) >= 2:  # Minimum rows for a table
                        table_regions.append(self.create_table_region(current_table))
                    current_table = [potential_table_lines[i]]
            
            # Add the last table
            if len(current_table) >= 2:
                table_regions.append(self.create_table_region(current_table))
        
        return table_regions
    
    def has_regular_spacing(self, x_positions: List[float], tolerance: float = 10.0) -> bool:
        """
        Check if X positions show regular spacing indicative of table columns
        
        Args:
            x_positions: List of X coordinates
            tolerance: Acceptable deviation from regular spacing
            
        Returns:
            True if spacing appears regular
        """
        if len(x_positions) < 3:
            return False
        
        spacings = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
        avg_spacing = sum(spacings) / len(spacings)
        
        # Check if all spacings are within tolerance of average
        return all(abs(spacing - avg_spacing) <= tolerance for spacing in spacings)
    
    def create_table_region(self, table_lines: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Create a table region descriptor from table lines
        
        Args:
            table_lines: List of lines that form a table
            
        Returns:
            Table region dictionary
        """
        # Get bounding box of entire table
        all_words = [word for line in table_lines for word in line]
        min_x = min(w["x0"] for w in all_words)
        max_x = max(w["x1"] for w in all_words)
        min_y = min(w["y0"] for w in all_words)
        max_y = max(w["y1"] for w in all_words)
        
        # Identify potential headers (first line)
        headers = [w["text"] for w in table_lines[0]]
        
        return {
            "type": "table",
            "bbox": [min_x, min_y, max_x, max_y],
            "headers": headers,
            "row_count": len(table_lines),
            "column_count": len(headers),
            "lines": table_lines
        }