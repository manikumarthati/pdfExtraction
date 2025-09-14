from openai import OpenAI
import json,os
from typing import Dict, Any, List
import time
from config import GPTConfig
from .prompts import PromptTemplates
from .spatial_preprocessor import SpatialPreprocessor
from .coordinate_table_extractor import CoordinateTableExtractor
from .vision_extractor import VisionBasedExtractor
from .feedback_analyzer import FeedbackAnalyzer

class OpenAIService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.config = GPTConfig()
        self.prompts = PromptTemplates()
        self.spatial_preprocessor = SpatialPreprocessor()
        self.vision_extractor = VisionBasedExtractor(api_key)
        self.feedback_analyzer = FeedbackAnalyzer(self)
    
    def _make_gpt_request(self, prompt: str, task_type: str) -> Dict[str, Any]:
        """Make a GPT request with task-specific model selection and cost tracking"""
        
        # Get optimized config for this task
        task_config = self.config.get_model_config(task_type)
        
        request_start = time.time()
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=task_config['model'],
                    messages=[{"role": "user", "content": prompt}],
                    temperature=task_config['temperature'],
                    max_tokens=task_config['max_tokens'],
                    timeout=self.config.TIMEOUT
                )
                
                # Track usage and cost if enabled
                usage_info = {}
                if self.config.ENABLE_COST_TRACKING:
                    usage_info = self._track_usage(response, task_type, task_config['model'])
                
                content = response.choices[0].message.content.strip()
                
                # Save prompt and response for debugging
                import os
                debug_dir = "debug_responses"
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = os.path.join(debug_dir, f"debug_{task_type}_{int(time.time())}.txt")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(f"=== CLAUDE ENHANCED DEBUG SESSION ===\n")
                    f.write(f"UPDATED CODE VERSION: 2025-09-13 NEW FORMAT\n")
                    f.write(f"Task Type: {task_type}\n")
                    f.write(f"Model: {task_config['model']}\n")
                    f.write(f"Temperature: {task_config['temperature']}\n")
                    f.write(f"Max Tokens: {task_config['max_tokens']}\n")
                    f.write(f"Timestamp: {time.time()}\n")
                    f.write(f"Request Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n")
                    f.write("PROMPT SENT TO LLM:\n")
                    f.write("-" * 80 + "\n")
                    f.write(prompt)
                    f.write("\n" + "=" * 80 + "\n")
                    f.write("RAW RESPONSE FROM LLM:\n")
                    f.write("-" * 80 + "\n")
                    f.write(content)
                    f.write("\n" + "=" * 80 + "\n")
                print(f"DEBUG - Prompt & response saved to: {debug_file}")
                
                # Try to parse JSON, with fallback handling
                try:
                    result = json.loads(content)
                except json.JSONDecodeError:
                    # Try multiple JSON extraction strategies
                    result = self._extract_json_from_response(content, task_config['model'], task_type)
                    if not result["success"]:
                        return result
                    result = result["data"]
                
                return {
                    "success": True, 
                    "data": result,
                    "usage": usage_info,
                    "model_used": task_config['model'],
                    "task_type": task_type,
                    "response_time": time.time() - request_start
                }
                
            except json.JSONDecodeError as e:
                # Try to extract JSON from the response
                content = response.choices[0].message.content
                return {
                    "success": False, 
                    "error": f"JSON parsing error: {str(e)}", 
                    "raw_content": content,
                    "model_used": task_config['model'],
                    "task_type": task_type
                }
                
            except Exception as e:
                if attempt == self.config.MAX_RETRIES - 1:
                    return {
                        "success": False, 
                        "error": f"Request failed after {self.config.MAX_RETRIES} attempts: {str(e)}",
                        "model_used": task_config['model'],
                        "task_type": task_type
                    }
                
                # Wait before retry
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return {"success": False, "error": "Maximum retries exceeded"}

    def _make_gpt_request_with_system_user(self, system_prompt: str, user_prompt: str, task_type: str) -> Dict[str, Any]:
        """Make a GPT request with separate system and user messages (like simple_pdf_parser.py)"""

        # Get optimized config for this task
        task_config = self.config.get_model_config(task_type)

        request_start = time.time()

        for attempt in range(self.config.MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=task_config['model'],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=task_config['temperature'],
                    max_tokens=task_config['max_tokens'],
                    timeout=self.config.TIMEOUT
                )

                # Track usage and cost if enabled
                usage_info = {}
                if self.config.ENABLE_COST_TRACKING:
                    usage_info = self._track_usage(response, task_type, task_config['model'])

                content = response.choices[0].message.content.strip()

                # Save prompt and response for debugging
                import os
                debug_dir = "debug_responses"
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = os.path.join(debug_dir, f"debug_system_user_{task_type}_{int(time.time())}.txt")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(f"=== SYSTEM/USER PROMPT DEBUG SESSION ===\n")
                    f.write(f"Task Type: {task_type}\n")
                    f.write(f"Model: {task_config['model']}\n")
                    f.write(f"Temperature: {task_config['temperature']}\n")
                    f.write(f"Max Tokens: {task_config['max_tokens']}\n")
                    f.write(f"Timestamp: {time.time()}\n")
                    f.write(f"Request Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n")
                    f.write("SYSTEM PROMPT:\n")
                    f.write("-" * 80 + "\n")
                    f.write(system_prompt)
                    f.write("\n" + "=" * 80 + "\n")
                    f.write("USER PROMPT:\n")
                    f.write("-" * 80 + "\n")
                    f.write(user_prompt)
                    f.write("\n" + "=" * 80 + "\n")
                    f.write("RAW RESPONSE FROM LLM:\n")
                    f.write("-" * 80 + "\n")
                    f.write(content)
                    f.write("\n" + "=" * 80 + "\n")
                print(f"DEBUG - System/User prompt & response saved to: {debug_file}")

                # Try to parse JSON, with fallback handling
                try:
                    # Handle JSON in code blocks like simple_pdf_parser.py
                    if '```json' in content:
                        json_start = content.find('```json') + 7
                        json_end = content.find('```', json_start)
                        content = content[json_start:json_end].strip()
                    elif '```' in content:
                        json_start = content.find('```') + 3
                        json_end = content.rfind('```')
                        content = content[json_start:json_end].strip()

                    result = json.loads(content)
                except json.JSONDecodeError:
                    # Try multiple JSON extraction strategies
                    result = self._extract_json_from_response(content, task_config['model'], task_type)
                    if not result["success"]:
                        return result
                    result = result["data"]

                return {
                    "success": True,
                    "data": result,
                    "usage": usage_info,
                    "model_used": task_config['model'],
                    "task_type": task_type,
                    "response_time": time.time() - request_start
                }

            except Exception as e:
                if attempt == self.config.MAX_RETRIES - 1:
                    return {
                        "success": False,
                        "error": f"System/User request failed after {self.config.MAX_RETRIES} attempts: {str(e)}",
                        "model_used": task_config['model'],
                        "task_type": task_type
                    }

                # Wait before retry
                time.sleep(2 ** attempt)  # Exponential backoff

        return {"success": False, "error": "Maximum retries exceeded"}
    
    def _extract_json_from_response(self, content: str, model: str, task_type: str) -> Dict[str, Any]:
        """Extract JSON from response using multiple fallback strategies"""
        import re
        
        # Strategy 1: Extract from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
        if json_match:
            try:
                json_str = json_match.group(1).strip()
                cleaned_json = self._clean_json_string(json_str)
                result = json.loads(cleaned_json)
                return {"success": True, "data": result}
            except json.JSONDecodeError as e:
                print(f"DEBUG - JSON in code block failed: {e}")
        
        # Strategy 2: Extract from response without code blocks
        json_match = re.search(r'(\{[\s\S]*\})', content)
        if json_match:
            try:
                json_str = json_match.group(1).strip()
                print(f"DEBUG - Attempting to parse JSON (length: {len(json_str)})")
                
                # Try to clean up common JSON issues
                cleaned_json = self._clean_json_string(json_str)
                result = json.loads(cleaned_json)
                return {"success": True, "data": result}
            except json.JSONDecodeError as e:
                print(f"DEBUG - JSON Parse Error: {e}")
                print(f"DEBUG - Error at position: {e.pos if hasattr(e, 'pos') else 'unknown'}")
        
        # Strategy 3: Try to create a minimal valid response for the task
        fallback_result = self._create_fallback_response(task_type, content)
        if fallback_result:
            return {"success": True, "data": fallback_result}
        
        # All strategies failed
        return {
            "success": False,
            "error": f"Failed to extract valid JSON from response",
            "raw_content": content,
            "model_used": model,
            "task_type": task_type
        }
    
    def _create_fallback_response(self, task_type: str, content: str) -> Dict[str, Any]:
        """Create minimal valid response when JSON parsing fails completely"""
        if task_type == 'field_identification':
            # Try to extract some basic info from the raw content
            if 'form' in content.lower():
                return {
                    "field_type": "form",
                    "fields": [],
                    "parsing_error": "Failed to parse AI response, using fallback"
                }
            elif 'table' in content.lower():
                return {
                    "field_type": "table", 
                    "tables": [],
                    "headers": [],
                    "parsing_error": "Failed to parse AI response, using fallback"
                }
            else:
                return {
                    "field_type": "mixed",
                    "form_fields": [],
                    "table_headers": [],
                    "parsing_error": "Failed to parse AI response, using fallback"
                }
        elif task_type == 'classification':
            return {
                "classification": "unknown",
                "confidence": 0.0,
                "reasoning": "Failed to parse AI response",
                "regions": []
            }
        elif task_type == 'data_extraction':
            return {
                "extracted_data": {},
                "table_data": [],
                "parsing_error": "Failed to parse AI response, using fallback"
            }
        
        return None
    
    def _clean_json_string(self, json_str: str) -> str:
        """Clean common JSON formatting issues"""
        # Remove any trailing commas before closing brackets/braces
        import re
        cleaned = re.sub(r',\s*([}\]])', r'\1', json_str)
        
        # Fix any unescaped quotes in strings (basic attempt)
        # This is a simple fix - for more complex cases, might need more sophisticated parsing
        
        # Remove any non-JSON prefix/suffix
        cleaned = cleaned.strip()
        
        # Handle truncated JSON by trying to close open structures
        open_braces = cleaned.count('{') - cleaned.count('}')
        open_brackets = cleaned.count('[') - cleaned.count(']')
        
        if open_braces > 0:
            cleaned += '}' * open_braces
        if open_brackets > 0:
            cleaned += ']' * open_brackets
            
        return cleaned
    
    def _track_usage(self, response, task_type: str, model: str) -> Dict[str, Any]:
        """Track token usage and estimated costs"""
        
        # OpenAI pricing (as of 2024 - should be updated regularly)
        pricing = {
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},  # per 1K tokens
            'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
            'gpt-4o': {'input': 0.0025, 'output': 0.01},
            'gpt-4': {'input': 0.03, 'output': 0.06}
        }
        
        if hasattr(response, 'usage'):
            usage = response.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            
            # Calculate cost
            model_pricing = pricing.get(model, {'input': 0.01, 'output': 0.01})  # fallback
            input_cost = (input_tokens / 1000) * model_pricing['input']
            output_cost = (output_tokens / 1000) * model_pricing['output']
            total_cost = input_cost + output_cost
            
            return {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'estimated_cost': round(total_cost, 6),
                'model': model,
                'task_type': task_type
            }
        
        return {'error': 'Usage information not available'}
    
    def classify_structure(self, text: str, text_blocks: list) -> Dict[str, Any]:
        """Step 1: Classify PDF structure as Form, Table, or Mixed"""
        
        # Create a simplified representation of the document
        doc_info = {
            "text_length": len(text),
            "total_blocks": len(text_blocks),
            "sample_text":  text
        }
        
        prompt = self.prompts.STRUCTURE_CLASSIFICATION.format(
            text_length=doc_info['text_length'],
            total_blocks=doc_info['total_blocks'],
            sample_text=doc_info['sample_text']
        )
        
        result = self._make_gpt_request(prompt, 'classification')
        
        if result["success"]:
            return result["data"]
        else:
            return {
                "classification": "unknown",
                "confidence": 0.0,
                "reasoning": f"Error in classification: {result['error']}",
                "regions": [],
                "error": result["error"]
            }
    
    def identify_fields(self, text: str, classification_result: Dict[str, Any], user_feedback: str = "", feedback_history: list = None, word_coordinates: list = None) -> Dict[str, Any]:
        """Step 2: Comprehensive field and table extraction with spatial preprocessing support"""
        
        print(f"DEBUG - Starting comprehensive field extraction, text length: {len(text)}")
        print(f"DEBUG - User feedback provided: {bool(user_feedback.strip()) if user_feedback else False}")
        print(f"DEBUG - Feedback history entries: {len(feedback_history) if feedback_history else 0}")
        print(f"DEBUG - Word coordinates available: {bool(word_coordinates)}")
        
        # Use spatial preprocessing if word coordinates are available
        if word_coordinates:
            print(f"DEBUG - Processing {len(word_coordinates)} words with spatial analysis")
            spatially_formatted_text = self.spatial_preprocessor.preprocess_document(word_coordinates)
            print(f"DEBUG - Spatially formatted text length: {len(spatially_formatted_text)}")
            
            # Use the spatially formatted text instead of raw text
            processed_text = spatially_formatted_text
        else:
            print("DEBUG - No word coordinates available, using raw text")
            processed_text = text
        
        # Prepare feedback context including all historical feedback
        feedback_context = self._prepare_feedback_context(user_feedback, feedback_history)
        
        # Use focused comprehensive extraction with system/user prompt format like simple_pdf_parser.py
        system_prompt = self.prompts.FOCUSED_COMPREHENSIVE_FIELD_EXTRACTION_SYSTEM

        user_prompt = f"""CRITICAL DOCUMENT EXTRACTION - 100% ACCURACY REQUIRED

You must extract ALL fields from this document with PERFECT precision. This is a critical document where missing or incorrect data is unacceptable.

MANDATORY REQUIREMENTS:
1. Extract the FULL NAME if present (check carefully - names must not be missed)
2. Break down ALL addresses into Street, City, State, Zip components
3. Preserve EXACT numbers with correct decimal places
4. Align table columns EXACTLY - no shifting due to empty cells
5. Extract ALL phone numbers, emails, dates with exact formatting
6. Capture section headers exactly as written

## User Feedback Integration
{feedback_context}

DOCUMENT TEXT TO ANALYZE:
{processed_text}

Return ONLY valid JSON in the exact format specified in the system prompt. Pay special attention to names and ensure no prominent data is missed."""

        print(f"DEBUG - System prompt length: {len(system_prompt)}")
        print(f"DEBUG - User prompt length: {len(user_prompt)}")

        result = self._make_gpt_request_with_system_user(system_prompt, user_prompt, 'field_identification')
        print(f"DEBUG - Comprehensive extraction result: {result.get('success', False)}")
        
        if result["success"]:
            # Return focused format as-is without conversion to see full LLM output
            data = result["data"]
            print(f"DEBUG - Raw focused prompt output: {data}")
            # data = self._convert_focused_to_flask_format(data)
            if user_feedback.strip():
                data = self._enhance_result_with_feedback_metadata(data, user_feedback)

            # Skip field_type detection and simplified view creation for raw focused output
            # Set a default field_type based on document metadata if available
            if not data.get("field_type"):
                doc_metadata = data.get("document_metadata", {})
                data["field_type"] = doc_metadata.get("document_type", "unknown")

            # Skip simplified view creation to show raw focused output
            # data = self._create_simplified_view(data)

            return data
        else:
            return {
                "form_fields": [],
                "tables": [],
                "extraction_summary": {
                    "total_fields": 0,
                    "total_tables": 0,
                    "empty_fields": 0,
                    "confidence_score": 0.0,
                    "feedback_applied": bool(user_feedback.strip()) if user_feedback else False,
                    "refinement_iteration": 1
                },
                "error": result["error"]
            }
    
    def _convert_focused_to_flask_format(self, focused_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert focused prompt output format to Flask app expected format"""

        print(f"DEBUG - Converting focused format, main keys: {list(focused_data.keys())}")

        # Initialize Flask format structure
        flask_data = {
            "form_fields": [],
            "tables": [],
            "extraction_summary": {
                "total_fields": 0,
                "total_tables": 0,
                "empty_fields": 0,
                "confidence_score": 0.0,
                "refinement_iteration": 1
            }
        }

        # Extract document metadata if available
        doc_metadata = focused_data.get("document_metadata", {})
        extraction_summary = focused_data.get("extraction_summary", {})

        # Handle main content structure
        main_content = focused_data.get("main_content", {})

        # Process single record format
        single_record = main_content.get("single_record", {})
        if single_record and "sections" in single_record:
            sections = single_record["sections"]

            for section_name, section_data in sections.items():
                print(f"DEBUG - Processing section: {section_name}")

                # Extract individual fields
                individual_fields = section_data.get("individual_fields", {})
                for field_name, field_value in individual_fields.items():
                    flask_data["form_fields"].append({
                        "field_name": field_name
                    })

                # Extract tables
                section_tables = section_data.get("tables", [])
                for table in section_tables:
                    flask_data["tables"].append({
                        "table_name": table.get("table_name", "Unknown Table"),
                        "headers": table.get("headers", [])
                    })

        # Process multiple records format
        multiple_records = main_content.get("multiple_records", [])
        for record in multiple_records:
            record_data = record.get("record_data", {})

            # Add record-level fields as form fields
            for field_name, field_value in record_data.items():
                if field_name != "tables":  # Skip tables key
                    flask_data["form_fields"].append({
                        "field_name": field_name
                    })

            # Add record-level tables
            record_tables = record_data.get("tables", [])
            for table in record_tables:
                flask_data["tables"].append({
                    "table_name": table.get("table_name", "Unknown Table"),
                    "headers": table.get("headers", [])
                })

        # Update extraction summary
        flask_data["extraction_summary"].update({
            "total_fields": len(flask_data["form_fields"]),
            "total_tables": len(flask_data["tables"]),
            "confidence_score": extraction_summary.get("fields_extracted_high_confidence", 0) / max(extraction_summary.get("total_fields_attempted", 1), 1),
            "document_type": doc_metadata.get("document_type", "unknown"),
            "extraction_notes": f"Converted from focused format. Original confidence: {doc_metadata.get('confidence', 'unknown')}"
        })

        print(f"DEBUG - Conversion complete: {len(flask_data['form_fields'])} fields, {len(flask_data['tables'])} tables")

        return flask_data

    def _prepare_feedback_context(self, user_feedback: str, feedback_history: list = None) -> str:
        """Prepare user feedback with proper context and instructions including all historical feedback"""
        
        # Handle case with no feedback
        if not user_feedback or not user_feedback.strip():
            if not feedback_history or len(feedback_history) == 0:
                return "No specific user feedback provided. Perform initial extraction with high accuracy."
        
        structured_feedback = "IMPORTANT: This is a refinement request. The user has provided feedback to improve extraction accuracy.\n\n"
        
        # Include all previous feedback in chronological order
        if feedback_history and len(feedback_history) > 0:
            structured_feedback += "PREVIOUS FEEDBACK HISTORY (apply all of these cumulatively):\n"
            for i, history_entry in enumerate(feedback_history, 1):
                if isinstance(history_entry, dict) and history_entry.get('user_feedback'):
                    timestamp = history_entry.get('timestamp', 'Unknown time')
                    iteration = history_entry.get('iteration', i)
                    feedback_text = history_entry['user_feedback'].strip()
                    
                    structured_feedback += f"\n--- Iteration {iteration} Feedback ---\n"
                    structured_feedback += f"{feedback_text}\n"
            
            structured_feedback += "\n" + "="*50 + "\n"
        
        # Add current feedback
        if user_feedback and user_feedback.strip():
            structured_feedback += f"\nCURRENT FEEDBACK (latest correction):\n{user_feedback.strip()}\n\n"
        
        # Add processing instructions with the missing key instruction
        structured_feedback += """
EXTRACTION INSTRUCTIONS:
- Pay close attention to field names the user mentions
- Apply ALL feedback from the entire history - don't ignore previous corrections
- Each iteration builds on the previous one - maintain all previous improvements
- Add any missing fields mentioned in ANY feedback iteration
- Remove any incorrectly identified items mentioned in ANY feedback iteration
- Adjust table structures based on ALL feedback provided
- Follow their guidance on data types and field groupings
- If feedback contradicts, prioritize the most recent feedback but try to reconcile if possible

Remember: This is an iterative refinement process. Each feedback builds on the previous ones.
"""
        
        return structured_feedback
    
    def _enhance_result_with_feedback_metadata(self, data: Dict[str, Any], user_feedback: str) -> Dict[str, Any]:
        """Enhance extraction result with feedback tracking metadata"""
        if not isinstance(data, dict):
            return data
        
        # Update extraction summary with feedback info
        if "extraction_summary" not in data:
            data["extraction_summary"] = {}
        
        summary = data["extraction_summary"]
        summary["feedback_applied"] = True
        summary["refinement_iteration"] = summary.get("refinement_iteration", 1) + 1
        
        # Mark fields and tables as user-corrected if they appear to be corrections
        if "form_fields" in data and isinstance(data["form_fields"], list):
            for field in data["form_fields"]:
                if isinstance(field, dict):
                    field["user_corrected"] = True
        
        if "tables" in data and isinstance(data["tables"], list):
            for table in data["tables"]:
                if isinstance(table, dict):
                    table["user_corrected"] = True
        
        return data
    
    def _create_simplified_view(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a simplified view with field names only (no values)"""
        simplified = {}
        
        # Process form fields - just field names (no values at all)
        if data.get("form_fields"):
            simplified["form_fields"] = []  # Array of field names only
            for field in data["form_fields"]:
                if isinstance(field, dict):
                    # Handle new format with field_name key (correct format)
                    if "field_name" in field:
                        field_name = field["field_name"]
                        simplified["form_fields"].append(field_name)
                    # Handle legacy format with label key (wrong format - extract field name only)
                    elif "label" in field:
                        field_name = field["label"]
                        simplified["form_fields"].append(field_name)
                        print(f"WARNING: LLM returned old format with label/value - extracting field name only: {field_name}")
                    else:
                        print(f"WARNING: Unrecognized field format: {field}")
        
        # Process tables - just headers (no row data)
        if data.get("tables"):
            simplified["tables"] = []
            for table in data["tables"]:
                if isinstance(table, dict):
                    simple_table = {
                        "table_name": table.get("table_name", table.get("title", table.get("description", f"Table {table.get('table_id', '')}"))),
                        "headers": []
                    }
                    
                    # Handle new format with headers as array of strings
                    if table.get("headers"):
                        if isinstance(table["headers"], list):
                            # New format: headers are array of strings
                            simple_table["headers"] = [header for header in table["headers"] if isinstance(header, str)]
                        else:
                            # Legacy format: headers are array of objects
                            simple_table["headers"] = [header.get("name", "") for header in table["headers"] if isinstance(header, dict)]
                    
                    simplified["tables"].append(simple_table)
        
        # Keep essential metadata but clean it up
        if data.get("extraction_summary"):
            summary = data["extraction_summary"]
            simplified["summary"] = {
                "total_form_fields": summary.get("total_fields", len(simplified.get("form_fields", []))),
                "total_tables": summary.get("total_tables", len(simplified.get("tables", []))),
                "iteration": summary.get("refinement_iteration", 1)
            }
        
        # Keep field_type for template logic
        simplified["field_type"] = data.get("field_type", "unknown")
        
        # Keep any error messages
        if data.get("error"):
            simplified["error"] = data["error"]
            
        return simplified
    
    def _identify_form_fields(self, text: str) -> Dict[str, Any]:
        """Identify form field labels and values"""
        
        print(f"DEBUG - Starting form field identification, text length: {len(text)}")
        prompt = self.prompts.FORM_FIELD_IDENTIFICATION.format(text=text)
        print(f"DEBUG - Form prompt length: {len(prompt)}")
        
        result = self._make_gpt_request(prompt, 'field_identification')
        print(f"DEBUG - Form field result: {result.get('success', False)}")
        
        if result["success"]:
            return result["data"]
        else:
            return {"field_type": "form", "fields": [], "error": result["error"]}
    
    def _identify_table_headers(self, text: str) -> Dict[str, Any]:
        """Identify table headers and structure"""
        
        print(f"DEBUG - Starting table header identification, text length: {len(text)}")
        prompt = self.prompts.TABLE_HEADER_IDENTIFICATION.format(text=text)
        print(f"DEBUG - Table prompt length: {len(prompt)}")
        
        result = self._make_gpt_request(prompt, 'field_identification')
        print(f"DEBUG - Table header result: {result.get('success', False)}")
        
        if result["success"]:
            data = result["data"]
            # Handle both old and new format
            if "tables" in data:
                return data  # New format with grouped tables
            elif "headers" in data:
                # Convert old format to new format
                return {
                    "field_type": "table",
                    "tables": [{
                        "table_id": 1,
                        "description": "Identified Table",
                        "headers": data["headers"],
                        "estimated_rows": data.get("estimated_rows", 0)
                    }]
                }
            else:
                return data
        else:
            return {"field_type": "table", "tables": [], "headers": [], "error": result["error"]}
    
    def _identify_mixed_elements(self, text: str) -> Dict[str, Any]:
        """Identify both form fields and table headers in mixed content"""
        
        # Try to identify both and combine results
        form_result = self._identify_form_fields(text)
        table_result = self._identify_table_headers(text)
        
        # Handle table headers - could be new format with tables array or old format
        table_headers = []
        tables = []
        
        if "tables" in table_result:
            tables = table_result.get("tables", [])
            # Extract all headers from all tables for backward compatibility
            for table in tables:
                table_headers.extend(table.get("headers", []))
        else:
            table_headers = table_result.get("headers", [])
        
        result = {
            "field_type": "mixed",
            "form_fields": form_result.get("fields", []),
            "table_headers": table_headers,  # Keep backward compatibility
            "errors": {
                "form_error": form_result.get("error"),
                "table_error": table_result.get("error")
            }
        }
        
        # Add new tables format if available
        if tables:
            result["tables"] = tables
            
        return result
    
    def extract_data(self, text: str, field_mapping: Dict[str, Any], word_coordinates: List[Dict] = None, user_feedback: str = "", previous_result: Dict[str, Any] = None, feedback_history: List[Dict] = None) -> Dict[str, Any]:
        """Step 3: Extract actual data using validated Step 2 structure with UNIFIED SCHEMA-BASED extraction"""

        print(f"DEBUG Step3 - Starting UNIFIED SCHEMA-BASED data extraction")
        print(f"DEBUG Step3 - Field mapping keys: {list(field_mapping.keys())}")
        print(f"DEBUG Step3 - Field mapping type: {field_mapping.get('field_type', 'unknown')}")
        print(f"DEBUG Step3 - Form fields type: {type(field_mapping.get('form_fields'))}")
        print(f"DEBUG Step3 - Tables count: {len(field_mapping.get('tables', []))}")
        print(f"DEBUG Step3 - Word coordinates available (IGNORED in unified approach): {bool(word_coordinates)}")
        print(f"DEBUG Step3 - User feedback length: {len(user_feedback) if user_feedback else 0}")

        # Validate Step2 structure has required data
        if not field_mapping.get('form_fields') and not field_mapping.get('tables'):
            print(f"WARNING Step3 - Step2 structure appears empty or invalid")
            print(f"WARNING Step3 - Available keys: {list(field_mapping.keys())}")

        # Use unified schema-based approach (no coordinate dependency)
        return self._extract_comprehensive_data(text, field_mapping, word_coordinates, user_feedback, previous_result, feedback_history)
    
    def _extract_comprehensive_data(self, text: str, field_mapping: Dict[str, Any], word_coordinates: List[Dict] = None, user_feedback: str = "", previous_result: Dict[str, Any] = None, feedback_history: List[Dict] = None) -> Dict[str, Any]:
        """Extract actual data using the validated Step 2 field and table structure with unified LLM approach"""

        print(f"DEBUG Step3 - Using UNIFIED SCHEMA-BASED extraction approach")
        print(f"DEBUG Step3 - Schema contains {len(field_mapping.get('form_fields', {}))} form fields")
        print(f"DEBUG Step3 - Schema contains {len(field_mapping.get('tables', []))} tables")

        # Create detailed debug log
        debug_log_path = os.path.join("debug_responses", f"step3_unified_extraction_{int(time.time())}.txt")
        with open(debug_log_path, 'w', encoding='utf-8') as debug_file:
            debug_file.write("=== STEP 3 UNIFIED SCHEMA-BASED EXTRACTION ===\n")
            debug_file.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            debug_file.write(f"Field mapping keys: {list(field_mapping.keys())}\n")
            debug_file.write(f"Form fields count: {len(field_mapping.get('form_fields', {}))}\n")
            debug_file.write(f"Tables count: {len(field_mapping.get('tables', []))}\n")
            debug_file.write(f"User feedback provided: {bool(user_feedback.strip())}\n")
            debug_file.write("=" * 50 + "\n")
            debug_file.write("COMPLETE SCHEMA:\n")
            debug_file.write(f"Form Fields: {field_mapping.get('form_fields', {})}\n")
            debug_file.write(f"Tables: {field_mapping.get('tables', [])}\n")
            debug_file.write("=" * 50 + "\n")

        # Use unified schema-based extraction
        result = self._extract_unified_schema_data(text, field_mapping, user_feedback, previous_result, feedback_history)

        return result

    def _extract_unified_schema_data(self, text: str, field_mapping: Dict[str, Any], user_feedback: str = "", previous_result: Dict[str, Any] = None, feedback_history: List[Dict] = None) -> Dict[str, Any]:
        """Extract all data using unified schema-based approach with enhanced feedback analysis"""

        # Handle different Step2 schema formats
        form_fields_schema = self._normalize_form_fields_schema(field_mapping.get('form_fields', {}))
        tables_schema = field_mapping.get('tables', [])

        # Create schema strings for prompt
        form_fields_str = json.dumps(form_fields_schema, indent=2) if form_fields_schema else "No form fields"
        tables_str = json.dumps(tables_schema, indent=2) if tables_schema else "No tables"

        print(f"DEBUG Step3 - Building unified extraction prompt")
        print(f"DEBUG Step3 - Normalized form fields: {type(form_fields_schema)} with {len(form_fields_schema) if isinstance(form_fields_schema, (dict, list)) else 0} items")
        print(f"DEBUG Step3 - Tables schema: {len(tables_schema)} tables")

        # Use enhanced feedback analysis if user feedback is provided
        if user_feedback.strip():
            print(f"DEBUG Step3 - Using enhanced feedback analysis for prompt generation")
            prompt = self._build_enhanced_unified_prompt(
                form_fields_str, tables_str, text, user_feedback, field_mapping, previous_result, feedback_history
            )
        else:
            # Use standard unified schema extraction
            print(f"DEBUG Step3 - Using standard unified schema extraction")
            prompt = self.prompts.UNIFIED_SCHEMA_EXTRACTION_BACKUP.format(
                form_fields_schema=form_fields_str,
                tables_schema=tables_str,
                text=text
            )

        print(f"DEBUG Step3 - Unified prompt length: {len(prompt)}")

        # Make single LLM request for everything
        result = self._make_gpt_request(prompt, 'data_extraction')

        if result["success"]:
            extracted_result = result["data"]

            print(f"DEBUG Step3 - Unified extraction successful")
            print(f"DEBUG Step3 - Form data keys: {list(extracted_result.get('form_data', {}).keys())}")
            print(f"DEBUG Step3 - Table data count: {len(extracted_result.get('table_data', []))}")

            # Reformat to match expected structure
            final_result = {
                "extracted_data": extracted_result.get("form_data", {}),
                "table_data": extracted_result.get("table_data", []),
                "extraction_summary": {
                    "total_extracted_fields": len(extracted_result.get("form_data", {})),
                    "total_extracted_tables": len(extracted_result.get("table_data", [])),
                    "total_table_rows_extracted": sum(len(table.get("rows", [])) for table in extracted_result.get("table_data", [])),
                    "extraction_success": True,
                    "extraction_method": "unified_schema_based",
                    "extraction_confidence": extracted_result.get("extraction_summary", {}).get("extraction_confidence", 0.9)
                }
            }

            return final_result

        else:
            print(f"DEBUG Step3 - Unified extraction failed: {result.get('error')}")
            return {
                "extracted_data": {},
                "table_data": [],
                "extraction_summary": {
                    "total_extracted_fields": 0,
                    "total_extracted_tables": 0,
                    "total_table_rows_extracted": 0,
                    "extraction_success": False,
                    "extraction_method": "unified_schema_based",
                    "error": result.get("error")
                }
            }

    def _normalize_form_fields_schema(self, form_fields) -> Dict[str, Any]:
        """Normalize different Step2 form field formats to consistent schema"""

        if isinstance(form_fields, dict):
            # Format: {"Employee Name": "value", "Emp Id": "value"} - already correct
            print(f"DEBUG - Form fields already in dict format with {len(form_fields)} fields")
            return form_fields

        elif isinstance(form_fields, list):
            if not form_fields:
                print(f"DEBUG - Empty form fields list")
                return {}

            # Check if it's array of field names: ["Employee Name", "Emp Id", ...]
            if isinstance(form_fields[0], str):
                print(f"DEBUG - Converting array of {len(form_fields)} field names to dict format")
                # Convert to dict with null values for extraction
                return {field_name: None for field_name in form_fields}

            # Check if it's array of objects: [{"field_name": "Employee Name"}, ...]
            elif isinstance(form_fields[0], dict) and "field_name" in form_fields[0]:
                print(f"DEBUG - Converting array of {len(form_fields)} field objects to dict format")
                return {field.get("field_name", f"Field_{i}"): None for i, field in enumerate(form_fields)}

            # Legacy format: [{"label": "name", "value": "value"}]
            elif isinstance(form_fields[0], dict) and "label" in form_fields[0]:
                print(f"DEBUG - Converting legacy array of {len(form_fields)} label objects to dict format")
                return {field.get("label", f"Field_{i}"): field.get("estimated_value") for i, field in enumerate(form_fields)}

        print(f"DEBUG - Unknown form fields format: {type(form_fields)}")
        return {}

    def _build_extraction_context(self, field_mapping: Dict[str, Any]) -> str:
        """Build extraction context from Step 2's validated structure"""
        
        context = "VALIDATED FIELD STRUCTURE FROM STEP 2:\n\n"
        
        # Add form fields if present
        if field_mapping.get("form_fields"):
            context += "FORM FIELDS TO EXTRACT:\n"
            if isinstance(field_mapping["form_fields"], list):
                # Check if it's the new format (array of strings) or legacy format (array of objects)
                if field_mapping["form_fields"] and isinstance(field_mapping["form_fields"][0], str):
                    # New format: ["Employee Name", "Birth Date", "Phone Number"]
                    for field_name in field_mapping["form_fields"]:
                        context += f"- {field_name}\n"
                else:
                    # Legacy format: [{"label": "name", "value": "value"}]
                    for field in field_mapping["form_fields"]:
                        if isinstance(field, dict):
                            field_name = field.get("label", "Unknown")
                            context += f"- {field_name}\n"
            elif isinstance(field_mapping["form_fields"], dict):
                # Very old format: {"field_name": "expected_value"}
                for field_name in field_mapping["form_fields"].keys():
                    context += f"- {field_name}\n"
            context += "\n"
        
        # Add table structures if present
        if field_mapping.get("tables"):
            context += "TABLE STRUCTURES TO EXTRACT:\n"
            for i, table in enumerate(field_mapping["tables"], 1):
                if isinstance(table, dict):
                    table_name = table.get("table_name", table.get("title", f"Table {i}"))
                    headers = table.get("headers", [])
                    
                    context += f"Table: {table_name}\n"
                    context += f"Columns: {', '.join(headers)}\n"
                    context += f"Extract all rows of data for these columns.\n\n"
        
        return context
    
    def _extract_form_data(self, text: str, fields: List[Dict]) -> Dict[str, Any]:
        """Extract form data using enhanced employee profile extraction"""
        
        field_names = [field["label"] for field in fields]
        
        # Use enhanced employee profile extraction prompt
        prompt = self.prompts.EMPLOYEE_PROFILE_EXTRACTION.format(
            field_names=field_names,
            text=text
        )
        
        print("=== CLAUDE DEBUG: About to call _make_gpt_request for data_extraction ===")
        result = self._make_gpt_request(prompt, 'data_extraction')
        print(f"=== CLAUDE DEBUG: _make_gpt_request returned: success={result.get('success')} ===")
        
        if result["success"]:
            return result["data"]
        else:
            return {"extracted_data": {}, "error": result["error"]}
    
    def _extract_table_data(self, text: str, headers: List[Dict]) -> Dict[str, Any]:
        """Extract table data using enhanced employee profile table extraction"""
        
        header_names = [header["name"] for header in headers]
        
        # Use enhanced employee profile table extraction prompt
        prompt = self.prompts.EMPLOYEE_PROFILE_TABLE_EXTRACTION.format(
            header_names=header_names,
            text=text
        )
        
        print("=== CLAUDE DEBUG: About to call _make_gpt_request for data_extraction ===")
        result = self._make_gpt_request(prompt, 'data_extraction')
        print(f"=== CLAUDE DEBUG: _make_gpt_request returned: success={result.get('success')} ===")
        
        if result["success"]:
            return result["data"]
        else:
            return {"table_data": [], "error": result["error"]}
    
    def _extract_form_fields_llm(self, text: str, form_fields: List[str], user_feedback: str = "") -> Dict[str, Any]:
        """Extract form field data using LLM with optional user feedback"""

        # Debug: Save extraction context
        print(f"DEBUG Step3 - Form field extraction starting")
        print(f"DEBUG Step3 - Fields to extract: {form_fields}")
        print(f"DEBUG Step3 - Text length: {len(text)} characters")
        print(f"DEBUG Step3 - Has user feedback: {bool(user_feedback.strip())}")

        # Build prompt for form field extraction
        # Handle both list of strings and list of dicts with field_name
        if form_fields and isinstance(form_fields[0], dict):
            field_names = [field.get('field_name', str(field)) for field in form_fields]
        else:
            field_names = form_fields
        field_names_str = ', '.join(field_names)

        if user_feedback.strip():
            # Use feedback-enhanced prompt
            prompt = self.prompts.FORM_DATA_EXTRACTION_WITH_FEEDBACK.format(
                field_names=field_names_str,
                text=text[:4000],  # Limit text to prevent context overflow
                user_feedback=user_feedback
            )
            print(f"DEBUG Step3 - Using feedback-enhanced prompt for form field extraction")
        else:
            # Use standard prompt
            prompt = self.prompts.FORM_DATA_EXTRACTION.format(
                field_names=field_names_str,
                text=text[:4000]  # Limit text to prevent context overflow
            )
            print(f"DEBUG Step3 - Using standard prompt for form field extraction")

        # Save additional context to debug file
        try:
            import os
            import time
            debug_dir = "debug_responses"
            os.makedirs(debug_dir, exist_ok=True)
            context_file = os.path.join(debug_dir, f"step3_form_extraction_context_{int(time.time())}.txt")
            with open(context_file, 'w', encoding='utf-8') as f:
                f.write("=== STEP 3 FORM FIELD EXTRACTION CONTEXT ===\n")
                f.write(f"Fields to extract: {form_fields}\n")
                f.write(f"Number of fields: {len(form_fields)}\n")
                f.write(f"Text length: {len(text)} characters\n")
                f.write(f"User feedback provided: {bool(user_feedback.strip())}\n")
                f.write(f"User feedback: {user_feedback}\n")
                f.write("=" * 80 + "\n")
                f.write("FULL TEXT CONTENT:\n")
                f.write(text)
                f.write("\n" + "=" * 80 + "\n")
        except Exception as debug_error:
            print(f"DEBUG - Failed to save context file: {debug_error}")
            # Continue execution even if debug file creation fails

        print("=== CLAUDE DEBUG: About to call _make_gpt_request for data_extraction ===")
        result = self._make_gpt_request(prompt, 'data_extraction')
        print(f"=== CLAUDE DEBUG: _make_gpt_request returned: success={result.get('success')} ===")

        if result["success"]:
            extracted = result["data"].get("extracted_data", {})
            print(f"DEBUG Step3 - Successfully extracted {len(extracted)} fields")
            print(f"DEBUG Step3 - Extracted fields: {list(extracted.keys())}")

            return {
                "success": True,
                "extracted_data": extracted,
                "feedback_applied": result["data"].get("feedback_applied", "")
            }
        else:
            print(f"DEBUG Step3 - Form field extraction failed: {result.get('error')}")
            return {
                "success": False,
                "error": result["error"],
                "extracted_data": {}
            }
    
    def _extract_table_data_llm(self, text: str, headers: List[str]) -> Dict[str, Any]:
        """Extract table data using LLM as fallback"""

        # Log to file for debugging
        debug_log_path = os.path.join("debug_responses", f"table_llm_extraction_{int(time.time())}.txt")
        with open(debug_log_path, 'w', encoding='utf-8') as debug_file:
            debug_file.write("=== LLM TABLE EXTRACTION CALLED ===\n")
            debug_file.write(f"Headers: {headers}\n")
            debug_file.write(f"Using prompt: TABLE_DATA_EXTRACTION\n")
            debug_file.write(f"Text length: {len(text)} characters\n")
            debug_file.write("=" * 50 + "\n")
            debug_file.write("TEXT TO EXTRACT FROM:\n")
            debug_file.write(text[:2000])  # First 2000 chars for debugging
            debug_file.write("\n" + "=" * 50 + "\n")

        print(f"DEBUG - _extract_table_data_llm called with headers: {headers}")
        print(f"DEBUG - Using TABLE_DATA_EXTRACTION prompt")

        headers_str = ', '.join(headers)
        prompt = self.prompts.TABLE_DATA_EXTRACTION.format(
            header_names=headers_str,
            text=text[:3000]  # Limit text to avoid context issues
        )

        # Save the actual prompt to debug file
        with open(debug_log_path, 'a', encoding='utf-8') as debug_file:
            debug_file.write("ACTUAL PROMPT SENT TO LLM:\n")
            debug_file.write(prompt)
            debug_file.write("\n" + "=" * 50 + "\n")

        print(f"DEBUG - Table extraction prompt length: {len(prompt)}")

        print("=== CLAUDE DEBUG: About to call _make_gpt_request for data_extraction ===")
        result = self._make_gpt_request(prompt, 'data_extraction')
        print(f"=== CLAUDE DEBUG: _make_gpt_request returned: success={result.get('success')} ===")
        
        if result["success"]:
            table_data = result["data"].get("table_data", [])
            return {
                "success": True,
                "rows": table_data
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "rows": []
            }
    
    def _extract_mixed_data(self, text: str, field_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Extract both form and table data from mixed content"""
        
        form_data = self._extract_form_data(text, field_mapping.get("form_fields", []))
        table_data = self._extract_table_data(text, field_mapping.get("table_headers", []))
        
        return {
            "form_data": form_data,
            "table_data": table_data
        }
    
    # Vision-based extraction methods
    
    def classify_structure_with_vision(self, pdf_path: str, page_num: int = 0) -> Dict[str, Any]:
        """Step 1: Classify PDF structure using vision (wrapper method)"""
        return self.vision_extractor.extract_structure_with_vision(pdf_path, page_num)
    
    def identify_fields_with_vision(self, pdf_path: str, page_num: int = 0, user_feedback: str = "") -> Dict[str, Any]:
        """Step 2: Identify fields using vision (wrapper method)"""
        result = self.vision_extractor.extract_fields_with_vision(pdf_path, page_num, user_feedback)
        
        if result["success"]:
            data = result["data"]
            
            # Ensure field_type is set based on what we found
            if not data.get("field_type"):
                has_form_fields = data.get("form_fields") and len(data["form_fields"]) > 0
                has_tables = data.get("tables") and len(data["tables"]) > 0
                
                if has_form_fields and has_tables:
                    data["field_type"] = "mixed"
                elif has_form_fields:
                    data["field_type"] = "form"
                elif has_tables:
                    data["field_type"] = "table"
                else:
                    data["field_type"] = "unknown"
            
            # Create simplified view for UI display
            data = self._create_simplified_view(data)
            data["extraction_method"] = "vision"
            
            return data
        else:
            return {
                "form_fields": [],
                "tables": [],
                "extraction_summary": {
                    "total_fields": 0,
                    "total_tables": 0,
                    "empty_fields": 0,
                    "confidence_score": 0.0,
                    "extraction_method": "vision"
                },
                "error": result["error"]
            }
    
    def extract_data_with_vision(self, pdf_path: str, field_mapping: Dict[str, Any], page_num: int = 0, user_feedback: str = "") -> Dict[str, Any]:
        """Step 3: Extract data using vision (wrapper method)"""
        result = self.vision_extractor.extract_data_with_vision(pdf_path, field_mapping, page_num, user_feedback)
        
        if result["success"]:
            data = result["data"]
            data["extraction_method"] = "vision"
            return data
        else:
            return {
                "extracted_data": {},
                "table_data": [],
                "extraction_summary": {
                    "total_extracted_fields": 0,
                    "total_extracted_tables": 0,
                    "success": False,
                    "extraction_method": "vision"
                },
                "error": result["error"]
            }

    # ======= ENHANCED EXTRACTION METHODS FOR MULTI-PAGE PROCESSING =======

    def extract_data_enhanced(self, text: str, enhanced_template: Dict[str, Any],
                            word_coordinates: List[Dict] = None) -> Dict[str, Any]:
        """Extract data using enhanced template with user feedback improvements"""

        # Get the base structure and enhancements
        base_structure = enhanced_template.get('base_structure', {})
        enhancements = enhanced_template.get('extraction_enhancements', {})

        # Build enhanced extraction prompt
        enhanced_prompt = self._build_enhanced_extraction_prompt(
            text, base_structure, enhancements, word_coordinates
        )

        # Make the extraction request
        result = self._make_gpt_request(enhanced_prompt, 'data_extraction')

        if result["success"]:
            extracted_data = result["data"]

            # Add enhancement metadata
            extracted_data['enhancement_metadata'] = {
                'template_version': enhanced_template['template_metadata']['template_version'],
                'enhancements_applied': True,
                'extraction_method': 'enhanced_text_extraction'
            }

            return extracted_data
        else:
            # Fallback to basic extraction if enhanced fails
            print(f"Enhanced extraction failed, falling back to basic: {result.get('error')}")
            return self.extract_data(text, base_structure, word_coordinates)

    def extract_data_with_vision_enhanced(self, pdf_path: str, enhanced_template: Dict[str, Any],
                                        page_num: int = 0) -> Dict[str, Any]:
        """Extract data using enhanced template with vision-based processing"""

        base_structure = enhanced_template.get('base_structure', {})
        enhancements = enhanced_template.get('extraction_enhancements', {})

        # Build enhanced vision prompt
        enhanced_prompt = self._build_enhanced_vision_prompt(base_structure, enhancements)

        # Use vision extractor with enhanced prompt
        result = self.vision_extractor.extract_with_enhanced_prompt(
            pdf_path, enhanced_prompt, page_num
        )

        if result.get('success'):
            extracted_data = result['data']

            # Add enhancement metadata
            extracted_data['enhancement_metadata'] = {
                'template_version': enhanced_template['template_metadata']['template_version'],
                'enhancements_applied': True,
                'extraction_method': 'enhanced_vision_extraction'
            }

            return extracted_data
        else:
            # Fallback to basic vision extraction
            print(f"Enhanced vision extraction failed, falling back to basic: {result.get('error')}")
            return self.extract_data_with_vision(pdf_path, base_structure, page_num)

    def _build_enhanced_extraction_prompt(self, text: str, base_structure: Dict[str, Any],
                                        enhancements: Dict[str, Any],
                                        word_coordinates: List[Dict] = None) -> str:
        """Build enhanced extraction prompt with feedback-derived improvements"""

        # Start with base extraction instructions
        base_prompt = self.prompts.COMPREHENSIVE_DATA_EXTRACTION.format(
            text=text,
            field_structure=self._format_field_structure(base_structure)
        )

        # Add enhancement instructions
        enhancement_sections = []

        if enhancements.get('detection_improvements'):
            enhancement_sections.append("### ENHANCED FIELD DETECTION")
            for improvement in enhancements['detection_improvements']:
                enhancement_sections.append(f"- {improvement}")

        if enhancements.get('extraction_refinements'):
            enhancement_sections.append("### EXTRACTION REFINEMENTS")
            for refinement in enhancements['extraction_refinements']:
                enhancement_sections.append(f"- {refinement}")

        if enhancements.get('spatial_adjustments') and word_coordinates:
            enhancement_sections.append("### SPATIAL ANALYSIS IMPROVEMENTS")
            for adjustment in enhancements['spatial_adjustments']:
                enhancement_sections.append(f"- {adjustment}")

        if enhancements.get('format_standardizations'):
            enhancement_sections.append("### FORMAT STANDARDIZATION")
            for standard in enhancements['format_standardizations']:
                enhancement_sections.append(f"- {standard}")

        # Combine base prompt with enhancements
        if enhancement_sections:
            enhanced_prompt = f"""
            {base_prompt}

            ## USER-FEEDBACK-DRIVEN ENHANCEMENTS
            Apply these learned improvements from user feedback:

            {chr(10).join(enhancement_sections)}

            ### CRITICAL INSTRUCTION
            These enhancements are based on actual user corrections. Apply them carefully to avoid the same mistakes.
            Prioritize accuracy over speed. When in doubt, apply the most specific enhancement rule that matches the situation.
            """
        else:
            enhanced_prompt = base_prompt

        return enhanced_prompt

    def _build_enhanced_vision_prompt(self, base_structure: Dict[str, Any],
                                    enhancements: Dict[str, Any]) -> str:
        """Build enhanced vision extraction prompt"""

        base_instructions = """
        Extract data from this PDF page image using the field structure provided.
        Focus on accuracy and precision in field identification and value extraction.
        """

        # Add enhancement instructions for vision
        enhancement_instructions = []

        if enhancements.get('detection_improvements'):
            enhancement_instructions.extend(enhancements['detection_improvements'])

        if enhancements.get('extraction_refinements'):
            enhancement_instructions.extend(enhancements['extraction_refinements'])

        if enhancements.get('format_standardizations'):
            enhancement_instructions.extend(enhancements['format_standardizations'])

        if enhancement_instructions:
            enhanced_prompt = f"""
            {base_instructions}

            ## ENHANCED INSTRUCTIONS (Based on User Feedback):
            {chr(10).join(f"- {instruction}" for instruction in enhancement_instructions)}

            Field Structure to Extract:
            {json.dumps(base_structure, indent=2)}

            Apply the enhanced instructions carefully to improve extraction accuracy.
            """
        else:
            enhanced_prompt = f"""
            {base_instructions}

            Field Structure to Extract:
            {json.dumps(base_structure, indent=2)}
            """

        return enhanced_prompt

    def _format_field_structure(self, structure: Dict[str, Any]) -> str:
        """Format field structure for prompt inclusion"""

        formatted_parts = []

        if 'form_fields' in structure:
            formatted_parts.append("**Form Fields to Extract:**")
            for field in structure['form_fields']:
                field_name = field.get('field_name', 'Unknown Field')
                formatted_parts.append(f"- {field_name}")

        if 'tables' in structure:
            formatted_parts.append("**Table Headers to Extract:**")
            for table in structure['tables']:
                table_name = table.get('table_name', 'Unknown Table')
                headers = table.get('headers', [])
                formatted_parts.append(f"- {table_name}: {', '.join(headers)}")

        return "\n".join(formatted_parts)

    def _build_enhanced_unified_prompt(self, form_fields_str: str, tables_str: str, text: str,
                                     user_feedback: str, field_mapping: Dict[str, Any],
                                     previous_result: Dict[str, Any] = None,
                                     feedback_history: List[Dict] = None) -> str:
        """Build enhanced extraction prompt using LLM-based feedback analysis for unified schema"""

        print(f"DEBUG Step3 - Starting LLM-based feedback analysis")
        print(f"DEBUG Step3 - Feedback history entries: {len(feedback_history) if feedback_history else 0}")
        if feedback_history:
            step3_history = [f for f in feedback_history if f.get('step') == 3]
            print(f"DEBUG Step3 - Step 3 feedback history entries: {len(step3_history)}")

        try:
            # Use provided previous result or empty dict
            if previous_result is None:
                previous_result = {}

            # Analyze user feedback with LLM including feedback history
            feedback_analysis = self.feedback_analyzer.analyze_user_feedback(
                user_feedback=user_feedback,
                original_result=previous_result,
                document_structure=field_mapping,
                feedback_history=feedback_history
            )

            print(f"DEBUG Step3 - Feedback analysis completed with confidence: {feedback_analysis.get('confidence_score', 0)}")

            # Extract enhancement components
            enhancements = feedback_analysis.get('extraction_enhancements', {})
            validation_rules = feedback_analysis.get('validation_rules', [])
            enhanced_instructions = feedback_analysis.get('enhanced_instructions', [])

            # Format enhancement sections
            detection_improvements = "\n".join([f"- {imp}" for imp in enhancements.get('detection_improvements', [])])
            format_handling = "\n".join([f"- {fmt}" for fmt in enhancements.get('format_standardizations', [])])
            validation_rules_str = "\n".join([f"- {rule}" for rule in validation_rules])
            enhanced_instructions_str = "\n".join([f"- {inst}" for inst in enhanced_instructions])

            # Build enhanced prompt using the new template
            enhanced_prompt = self.prompts.UNIFIED_SCHEMA_EXTRACTION.format(
                form_fields_schema=form_fields_str,
                tables_schema=tables_str,
                text=text,
                enhanced_instructions=enhanced_instructions_str or "No specific enhancements available",
                validation_rules=validation_rules_str or "Standard validation applies",
                detection_improvements=detection_improvements or "Standard detection methods apply",
                format_handling=format_handling or "Standard format handling applies"
            )

            print(f"DEBUG Step3 - Enhanced prompt generated with feedback analysis")
            return enhanced_prompt

        except Exception as e:
            print(f"ERROR Step3 - Feedback analysis failed: {e}")
            print(f"DEBUG Step3 - Falling back to direct feedback injection")

            # Fallback to simple feedback injection if analysis fails
            fallback_prompt = self.prompts.UNIFIED_SCHEMA_EXTRACTION_BACKUP.format(
                form_fields_schema=form_fields_str,
                tables_schema=tables_str,
                text=text
            )
            fallback_prompt += f"\n\n**USER FEEDBACK:** {user_feedback}\nApply this feedback to improve extraction accuracy.\n"

            return fallback_prompt