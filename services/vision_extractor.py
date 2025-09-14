"""
Vision-based PDF extraction using GPT-4o's vision capabilities
Converts PDF pages to images and uses AI vision for accurate extraction
"""

import fitz  # PyMuPDF
import base64
import io
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image
from openai import OpenAI
import json
import time
import os

class VisionBasedExtractor:
    def __init__(self, api_key: str):
        """Initialize the vision-based extractor with OpenAI API key"""
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"  # GPT-4o with vision capabilities
        
    def convert_pdf_to_image(self, pdf_path: str, page_num: int = 0, dpi: int = 300) -> bytes:
        """
        Convert PDF page to high-quality image
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to convert (0-indexed)
            dpi: Resolution for image conversion (200 DPI recommended for text clarity)
            
        Returns:
            Image data as bytes in PNG format
        """
        try:
            # Open PDF
            doc = fitz.open(pdf_path)
            
            if page_num >= len(doc):
                raise ValueError(f"Page {page_num} does not exist in PDF with {len(doc)} pages")
            
            # Get the page
            page = doc[page_num]
            
            # Create transformation matrix for desired DPI
            # PyMuPDF uses 72 DPI by default, so scale factor = desired_dpi / 72
            scale_factor = dpi / 72.0
            matrix = fitz.Matrix(scale_factor, scale_factor)
            
            # Render page to image (pixmap)
            pix = page.get_pixmap(matrix=matrix)
            
            # Convert to PNG bytes
            img_data = pix.tobytes("png")
            
            # Clean up
            doc.close()
            
            return img_data
            
        except Exception as e:
            raise Exception(f"Failed to convert PDF to image: {str(e)}")
    
    def encode_image_to_base64(self, image_data: bytes) -> str:
        """Convert image bytes to base64 string for API"""
        return base64.b64encode(image_data).decode('utf-8')
    
    def extract_structure_with_vision(self, pdf_path: str, page_num: int = 0) -> Dict[str, Any]:
        """
        Step 1: Use vision to classify document structure
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to analyze
            
        Returns:
            Structure classification result
        """
        try:
            # Convert PDF to image
            image_data = self.convert_pdf_to_image(pdf_path, page_num)
            image_base64 = self.encode_image_to_base64(image_data)
            
            prompt = """
            Analyze this document image and classify its structure. Look at the visual layout and organization.

            Classify this page as one of:
            1. "form" - Contains form fields with labels and values (like applications, invoices)
            2. "table" - Contains tabular data with rows and columns  
            3. "mixed" - Contains both form elements and tables

            Also identify the main regions and provide confidence score.

            You MUST respond with valid JSON only. No additional text or explanation.

            {
                "classification": "form|table|mixed",
                "confidence": 0.85,
                "reasoning": "Brief explanation of classification",
                "regions": [
                    {
                        "type": "form|table", 
                        "description": "Description of this region",
                        "estimated_bounds": "top|middle|bottom"
                    }
                ]
            }
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.0
            )
            
            content = response.choices[0].message.content.strip()
            
            # Save debug information first
            self._save_debug_response(content, "vision_classification", page_num)
            
            # Try to extract JSON from the response using multiple strategies
            result = self._extract_json_from_vision_response(content)
            
            return {
                "success": True,
                "data": result,
                "method": "vision",
                "model": self.model
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Vision structure analysis failed: {str(e)}",
                "method": "vision"
            }
    
    def extract_fields_with_vision(self, pdf_path: str, page_num: int = 0, user_feedback: str = "") -> Dict[str, Any]:
        """
        Step 2: Use vision to identify form fields and table headers
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number to analyze
            user_feedback: User corrections and feedback
            
        Returns:
            Field identification result
        """
        try:
            # Convert PDF to image
            image_data = self.convert_pdf_to_image(pdf_path, page_num)
            image_base64 = self.encode_image_to_base64(image_data)
            
            # Include user feedback in prompt if provided
            feedback_instruction = ""
            if user_feedback.strip():
                feedback_instruction = f"""
                
                USER FEEDBACK AND CORRECTIONS:
                {user_feedback}
                
                IMPORTANT: Apply the user's feedback and corrections. This is a refinement based on their input.
                """
            
            prompt = f"""
            CRITICAL INSTRUCTION: You are analyzing this document image to identify STRUCTURE ONLY.

            **VISUAL ANALYSIS GUIDELINES:**
            1. Look for labels followed by colons (:) or values - these are FORM FIELDS
            2. Look for organized columnar data with headers above rows - these are TABLES
            3. Focus on visual layout, alignment, and spacing to distinguish structure

            **FORM FIELDS (Individual data points):**
            - Labels like "Employee Name:", "SSN:", "DOB:" followed by individual values
            - Usually arranged vertically or in a grid pattern
            - Each field appears once with its specific value
            
            **TABLE HEADERS (Column headers above tabular data):**
            - Headers that appear above multiple rows of aligned data
            - Look for clear column boundaries and repeated data patterns below headers
            - Headers are typically in a different style (bold, centered, etc.)

            **IMPORTANT DISTINCTIONS:**
            - Section titles like "Rate Information" are NOT field names
            - Page headers/footers are NOT form fields
            - Individual values in table cells are NOT headers

            {feedback_instruction}

            **EXTRACTION RULES:**
            - Only extract the LABEL/HEADER text, never the values
            - For form fields: extract just the field label (e.g., "Employee Name", not "John Doe")
            - For tables: extract just column headers (e.g., "Rate", not "19.00")
            - Look carefully at visual alignment to group headers correctly

            Respond with valid JSON in this EXACT format:
            {{
                "form_fields": [
                    {{
                        "field_name": "Employee Name"
                    }},
                    {{
                        "field_name": "Birth Date"  
                    }}
                ],
                "tables": [
                    {{
                        "table_name": "Rate/Salary Information",
                        "headers": ["RateCode", "Description", "Rate", "Effective Dates"]
                    }}
                ],
                "extraction_summary": {{
                    "total_form_fields": 2,
                    "total_tables": 1,
                    "refinement_iteration": 1
                }},
                "feedback_response": "Initial extraction based on visual layout analysis"
            }}
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.0
            )
            
            content = response.choices[0].message.content.strip()
            
            # Save debug information first
            self._save_debug_response(content, "vision_field_identification", page_num)
            
            # Try to extract JSON from the response using multiple strategies
            result = self._extract_json_from_vision_response(content)
            
            return {
                "success": True,
                "data": result,
                "method": "vision",
                "model": self.model
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Vision field identification failed: {str(e)}",
                "method": "vision"
            }
    
    def extract_data_with_vision(self, pdf_path: str, field_structure: Dict[str, Any], page_num: int = 0, user_feedback: str = "") -> Dict[str, Any]:
        """
        Step 3: Use vision to extract actual data values based on validated structure
        
        Args:
            pdf_path: Path to PDF file
            field_structure: Validated field and table structure from Step 2
            page_num: Page number to analyze
            
        Returns:
            Data extraction result
        """
        try:
            # Convert PDF to image
            image_data = self.convert_pdf_to_image(pdf_path, page_num)
            image_base64 = self.encode_image_to_base64(image_data)
            
            # Build extraction context from validated structure
            extraction_context = self._build_vision_extraction_context(field_structure)
            
            # Include user feedback if provided
            feedback_section = ""
            if user_feedback.strip():
                feedback_section = f"""

            ## USER FEEDBACK AND CORRECTIONS:
            {user_feedback}
            
            IMPORTANT: Apply the user's feedback and corrections carefully. This is a refinement based on their input to improve extraction accuracy.
            """
            
            prompt = f"""
            You are a data extraction specialist. Extract actual data values from this document image using the VALIDATED field and table structure below.

            {extraction_context}{feedback_section}

            ## Extraction Instructions:

            **For Form Fields:**
            - Extract the exact actual values for each field listed above
            - If a field exists but is empty, use null
            - If a field is not found in the document, use null
            - Preserve the exact formatting of values as they appear

            **For Tables:**
            - Extract ALL rows of data for each table
            - Follow the exact column structure specified above
            - Preserve formatting of values (dates, numbers, currency, etc.)
            - If a cell is empty, use null
            - Include the column headers in the output

            **Quality Standards:**
            - Be precise - extract only what is actually visible in the document
            - Maintain original formatting and spacing
            - Do not make assumptions or add data that isn't there
            - Look carefully at the visual layout to ensure accurate extraction

            Respond with valid JSON only:
            {{
                "extracted_data": {{
                    "field_name": "actual_value_from_document"
                }},
                "table_data": [
                    {{
                        "table_name": "Table Name",
                        "headers": ["Column1", "Column2", "Column3"],
                        "rows": [
                            {{
                                "Column1": "value1",
                                "Column2": "value2", 
                                "Column3": "value3"
                            }},
                            {{
                                "Column1": "value4",
                                "Column2": "value5",
                                "Column3": "value6"
                            }}
                        ]
                    }}
                ],
                "extraction_summary": {{
                    "total_extracted_fields": 0,
                    "total_extracted_tables": 0,
                    "extraction_success": true
                }}
            }}
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0.0
            )
            
            content = response.choices[0].message.content.strip()
            
            # Save debug information first
            self._save_debug_response(content, "vision_data_extraction", page_num)
            
            # Try to extract JSON from the response using multiple strategies
            result = self._extract_json_from_vision_response(content)
            
            return {
                "success": True,
                "data": result,
                "method": "vision",
                "model": self.model
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Vision data extraction failed: {str(e)}",
                "method": "vision"
            }
    
    def _build_vision_extraction_context(self, field_structure: Dict[str, Any]) -> str:
        """Build extraction context for vision-based data extraction"""
        context = "VALIDATED FIELD STRUCTURE FROM STEP 2:\n\n"
        
        # Add form fields if present
        if field_structure.get("form_fields"):
            context += "FORM FIELDS TO EXTRACT:\n"
            if isinstance(field_structure["form_fields"], list):
                # Check if it's the new format (array of strings) or legacy format (array of objects)
                if field_structure["form_fields"] and isinstance(field_structure["form_fields"][0], str):
                    # New format: ["Employee Name", "Birth Date", "Phone Number"]
                    for field_name in field_structure["form_fields"]:
                        context += f"- {field_name}\n"
                else:
                    # Legacy format: [{"field_name": "name"}]
                    for field in field_structure["form_fields"]:
                        if isinstance(field, dict):
                            field_name = field.get("field_name", field.get("label", "Unknown"))
                            context += f"- {field_name}\n"
            elif isinstance(field_structure["form_fields"], dict):
                # Very old format: {"field_name": "expected_value"}
                for field_name in field_structure["form_fields"].keys():
                    context += f"- {field_name}\n"
            context += "\n"
        
        # Add table structures if present
        if field_structure.get("tables"):
            context += "TABLE STRUCTURES TO EXTRACT:\n"
            for i, table in enumerate(field_structure["tables"], 1):
                if isinstance(table, dict):
                    table_name = table.get("table_name", table.get("title", f"Table {i}"))
                    headers = table.get("headers", [])
                    
                    context += f"Table: {table_name}\n"
                    context += f"Columns: {', '.join(headers)}\n"
                    context += f"Extract all rows of data for these columns.\n\n"
        
        return context
    
    def _extract_json_from_vision_response(self, content: str) -> dict:
        """Extract JSON from vision response using multiple fallback strategies"""
        import re
        
        # Strategy 1: Try direct JSON parsing
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
        if json_match:
            try:
                json_str = json_match.group(1).strip()
                cleaned_json = self._clean_json_string(json_str)
                return json.loads(cleaned_json)
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Extract from response without code blocks
        json_match = re.search(r'(\{[\s\S]*\})', content)
        if json_match:
            try:
                json_str = json_match.group(1).strip()
                cleaned_json = self._clean_json_string(json_str)
                return json.loads(cleaned_json)
            except json.JSONDecodeError:
                pass
        
        # If all strategies fail, raise an error
        raise json.JSONDecodeError(f"Could not extract valid JSON from vision response: {content[:200]}...", content, 0)
    
    def _clean_json_string(self, json_str: str) -> str:
        """Clean common JSON formatting issues"""
        import re
        
        # Remove any trailing commas before closing brackets/braces
        cleaned = re.sub(r',\s*([}\]])', r'\1', json_str)
        
        # Handle truncated JSON by trying to close open structures
        open_braces = cleaned.count('{') - cleaned.count('}')
        open_brackets = cleaned.count('[') - cleaned.count(']')
        
        if open_braces > 0:
            cleaned += '}' * open_braces
        if open_brackets > 0:
            cleaned += ']' * open_brackets
            
        return cleaned.strip()
    
    def _save_debug_response(self, content: str, task_type: str, page_num: int):
        """Save debug response to file"""
        try:
            debug_dir = "debug_responses"
            os.makedirs(debug_dir, exist_ok=True)
            debug_file = os.path.join(debug_dir, f"vision_response_{task_type}_page{page_num}_{int(time.time())}.txt")
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"Task Type: {task_type} (Vision)\n")
                f.write(f"Model: {self.model}\n")
                f.write(f"Page: {page_num}\n")
                f.write(f"Timestamp: {time.time()}\n")
                f.write("=" * 50 + "\n")
                f.write("VISION RESPONSE:\n")
                f.write(content)
                
            print(f"DEBUG - Vision response saved to: {debug_file}")
            
        except Exception as e:
            print(f"DEBUG - Failed to save vision response: {e}")
    
    def get_image_info(self, pdf_path: str, page_num: int = 0) -> Dict[str, Any]:
        """Get information about the generated image for debugging"""
        try:
            image_data = self.convert_pdf_to_image(pdf_path, page_num)
            
            # Load image to get dimensions
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
            
            return {
                "success": True,
                "image_size_bytes": len(image_data),
                "image_dimensions": {
                    "width": width,
                    "height": height
                },
                "format": "PNG",
                "dpi_equivalent": 200  # Our conversion DPI
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get image info: {str(e)}"
            }

    def extract_with_enhanced_prompt(self, pdf_path: str, enhanced_prompt: str, page_num: int = 0) -> Dict[str, Any]:
        """
        Extract data using enhanced prompt with user feedback improvements

        Args:
            pdf_path: Path to PDF file
            enhanced_prompt: Enhanced extraction prompt with user feedback
            page_num: Page number to extract (0-indexed)

        Returns:
            Dict with extraction results and metadata
        """
        try:
            # Convert PDF page to image
            image_data = self.convert_pdf_to_image(pdf_path, page_num)
            base64_image = base64.b64encode(image_data).decode('utf-8')

            # Build vision request with enhanced prompt
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": enhanced_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                        }
                    ]
                }
            ]

            # Make API request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4000,  # Sufficient for complex extractions
                temperature=0.0,  # Deterministic for data extraction
                timeout=120
            )

            # Extract and parse response
            content = response.choices[0].message.content.strip()

            # Try to parse JSON response
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                result = self._extract_json_from_response(content)
                if not result.get('success'):
                    return result
                result = result['data']

            # Add metadata about enhanced extraction
            if isinstance(result, dict):
                result['vision_metadata'] = {
                    'page_number': page_num + 1,
                    'extraction_method': 'enhanced_vision',
                    'model_used': self.model,
                    'enhanced_prompt_used': True,
                    'image_quality_dpi': 300
                }

                # Calculate extraction statistics
                extracted_fields = len(result.get('extracted_data', {}))
                extracted_tables = len(result.get('table_data', []))

                result['extraction_summary'] = {
                    'total_extracted_fields': extracted_fields,
                    'total_extracted_tables': extracted_tables,
                    'extraction_success': True,
                    'extraction_method': 'enhanced_vision'
                }

            return {
                'success': True,
                'data': result
            }

        except Exception as e:
            return {
                'success': False,
                'error': f"Enhanced vision extraction failed: {str(e)}"
            }

    def _extract_json_from_response(self, content: str) -> Dict[str, Any]:
        """
        Extract JSON from potentially malformed response content
        """
        # Try to find JSON blocks in the response
        import re

        # Look for JSON blocks between ```json and ``` or { and }
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'(\{[^}]*"extracted_data"[^}]*\})',
            r'(\{.*\})'
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    result = json.loads(match)
                    return {'success': True, 'data': result}
                except json.JSONDecodeError:
                    continue

        # If no JSON found, return error with original content
        return {
            'success': False,
            'error': 'Could not extract valid JSON from response',
            'raw_content': content
        }