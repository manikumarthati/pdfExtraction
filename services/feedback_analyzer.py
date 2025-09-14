"""
Intelligent feedback analysis to create enhanced extraction templates
"""
import json
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .openai_service import OpenAIService

class FeedbackAnalyzer:
    def __init__(self, openai_service: "OpenAIService"):
        self.openai_service = openai_service

    def analyze_user_feedback(self, user_feedback: str, original_result: Dict[str, Any],
                            document_structure: Dict[str, Any], feedback_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Analyze user feedback and generate enhanced extraction logic
        """

        analysis_prompt = self._build_feedback_analysis_prompt(
            user_feedback, original_result, document_structure, feedback_history
        )

        try:
            # Use GPT-4o for feedback analysis (high accuracy needed)
            response = self.openai_service._make_gpt_request(
                prompt=analysis_prompt,
                task_type='feedback_analysis'
            )

            # Check if request was successful
            if not response.get('success'):
                raise Exception(f"LLM request failed: {response.get('error', 'Unknown error')}")

            # Parse the analysis result
            analysis_result = response['data']

            # Generate enhanced extraction instructions
            enhanced_instructions = self._generate_enhanced_instructions(
                analysis_result, document_structure
            )

            return {
                'feedback_analysis': analysis_result,
                'extraction_enhancements': enhanced_instructions['enhancements'],
                'validation_rules': enhanced_instructions['validation_rules'],
                'enhanced_instructions': enhanced_instructions['prompt_additions'],
                'confidence_score': analysis_result.get('confidence', 0.8)
            }


        except Exception as e:
            print(f"ERROR: Feedback analysis failed: {e}")
            return self._fallback_analysis(user_feedback)

    def _build_feedback_analysis_prompt(self, user_feedback: str,
                                      original_result: Dict[str, Any],
                                      document_structure: Dict[str, Any],
                                      feedback_history: List[Dict] = None) -> str:
        """Build intelligent prompt for feedback analysis"""

        return f"""
        You are an expert in document extraction feedback analysis. Your job is to understand user corrections and derive intelligent extraction rules.

        ## CONTEXT

        **Original Extraction Result:**
        {json.dumps(original_result.get('extracted_data', {}), indent=2)}

        **Document Structure (Fields and Tables):**
        {json.dumps(document_structure, indent=2)}

        **Current User Feedback:**
        "{user_feedback}"

        **Previous Feedback History:**
        {self._format_feedback_history(feedback_history)}

        ## ANALYSIS TASK

        Analyze BOTH the current feedback AND the previous feedback history to understand:
        1. What specific extraction errors occurred in this iteration?
        2. What patterns emerge from the previous feedback history?
        3. What recurring issues need to be addressed?
        4. What general principles can prevent similar errors across all extractions?
        5. How should the extraction logic be enhanced to incorporate ALL learned improvements?

        CRITICAL: Consider feedback history to build cumulative learning. Don't just fix this issue - apply all previous learnings too.
        Focus on creating rules that will work for ALL pages and ALL previously encountered scenarios.

        ## REQUIRED JSON RESPONSE

        {{
            "error_analysis": {{
                "identified_errors": [
                    {{
                        "error_type": "field_misassignment|missing_field|wrong_format|spatial_error|validation_failure",
                        "affected_field": "field_name",
                        "description": "What went wrong",
                        "root_cause": "Why it happened"
                    }}
                ],
                "error_patterns": ["generalized pattern description"]
            }},
            "enhancement_rules": {{
                "field_detection": {{
                    "improved_patterns": ["new detection patterns to add"],
                    "validation_checks": ["validation rules to add"],
                    "spatial_refinements": ["spatial analysis improvements"]
                }},
                "data_extraction": {{
                    "format_standardization": ["format rules to apply"],
                    "value_validation": ["value validation rules"],
                    "error_prevention": ["prevention strategies"]
                }}
            }},
            "generalized_principles": [
                "Universal principles that apply to all similar documents"
            ],
            "confidence": 0.85,
            "complexity_assessment": "simple|moderate|complex"
        }}
        """

    def _generate_enhanced_instructions(self, analysis_result: Dict[str, Any],
                                      document_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enhanced extraction instructions from analysis"""

        enhancement_prompt = f"""
        Based on this feedback analysis, generate specific extraction enhancements:

        **Analysis Result:**
        {json.dumps(analysis_result, indent=2)}

        **Document Structure:**
        {json.dumps(document_structure, indent=2)}

        Generate practical extraction instructions that can be added to prompts.

        Response format:
        {{
            "enhancements": {{
                "detection_improvements": ["specific instructions for better field detection"],
                "extraction_refinements": ["specific instructions for better data extraction"],
                "spatial_adjustments": ["spatial analysis improvements"],
                "format_standardizations": ["format handling improvements"]
            }},
            "validation_rules": [
                "Rule 1: Validation check to perform",
                "Rule 2: Another validation check"
            ],
            "prompt_additions": [
                "Specific instruction to add to extraction prompt",
                "Another specific instruction"
            ]
        }}
        """

        try:
            response = self.openai_service._make_gpt_request(
                prompt=enhancement_prompt,
                task_type='enhancement_generation'
            )

            # Check if request was successful
            if not response.get('success'):
                raise Exception(f"Enhancement generation failed: {response.get('error', 'Unknown error')}")

            return response['data']

        except Exception as e:
            print(f"ERROR generating enhancements: {e}")
            return self._fallback_enhancements()

    def _fallback_analysis(self, user_feedback: str) -> Dict[str, Any]:
        """Fallback analysis when main analysis fails"""
        return {
            'feedback_analysis': {
                'error_analysis': {
                    'identified_errors': [{'description': 'Analysis failed, using fallback'}],
                    'error_patterns': []
                },
                'confidence': 0.3
            },
            'extraction_enhancements': self._fallback_enhancements(),
            'validation_rules': [f"Review extraction carefully based on: {user_feedback}"],
            'enhanced_instructions': [f"Apply user guidance: {user_feedback}"],
            'confidence_score': 0.3
        }

    def _fallback_enhancements(self) -> Dict[str, Any]:
        """Fallback enhancements when analysis fails"""
        return {
            'enhancements': {
                'detection_improvements': ["Use more careful field boundary detection"],
                'extraction_refinements': ["Extract exact values as they appear"],
                'spatial_adjustments': ["Verify spatial alignment before extraction"],
                'format_standardizations': ["Maintain consistent data formatting"]
            },
            'validation_rules': ["Validate extracted data types match expected patterns"],
            'prompt_additions': ["Be more precise with field boundary detection and value extraction"]
        }

    def create_enhanced_extraction_prompt(self, base_prompt: str,
                                        enhancements: Dict[str, Any]) -> str:
        """Create enhanced prompt with feedback-derived improvements"""

        enhancement_sections = []

        # Add detection improvements
        if enhancements.get('extraction_enhancements', {}).get('detection_improvements'):
            enhancement_sections.append("### IMPROVED FIELD DETECTION")
            for improvement in enhancements['extraction_enhancements']['detection_improvements']:
                enhancement_sections.append(f"- {improvement}")

        # Add validation rules
        if enhancements.get('validation_rules'):
            enhancement_sections.append("### VALIDATION REQUIREMENTS")
            for rule in enhancements['validation_rules']:
                enhancement_sections.append(f"- {rule}")

        # Add enhanced instructions
        if enhancements.get('enhanced_instructions'):
            enhancement_sections.append("### ENHANCED EXTRACTION RULES")
            for instruction in enhancements['enhanced_instructions']:
                enhancement_sections.append(f"- {instruction}")

        # Combine base prompt with enhancements
        if enhancement_sections:
            enhanced_prompt = f"""
            {base_prompt}

            ## LEARNED EXTRACTION INTELLIGENCE
            Apply these user-feedback-derived improvements:

            {chr(10).join(enhancement_sections)}

            ### META-INSTRUCTION
            These enhancements are based on actual user corrections. Apply them carefully to achieve higher accuracy.
            """
        else:
            enhanced_prompt = base_prompt

        return enhanced_prompt

    def _format_feedback_history(self, feedback_history: List[Dict] = None) -> str:
        """Format feedback history for prompt inclusion"""

        if not feedback_history:
            return "No previous feedback history available."

        # Filter for step 3 feedback only
        step3_history = [f for f in feedback_history if f.get('step') == 3]

        if not step3_history:
            return "No previous Step 3 feedback history available."

        formatted_history = []
        for i, entry in enumerate(step3_history, 1):
            formatted_entry = f"""
        Feedback #{i} (Iteration {entry.get('iteration', i)}):
        - Date: {entry.get('timestamp', 'Unknown')}
        - User Feedback: "{entry.get('user_feedback', 'No feedback provided')}"
        - Result Before: {json.dumps(entry.get('result_before', {}), indent=2) if entry.get('result_before') else 'No previous result'}
        - Result After: {json.dumps(entry.get('result_after', {}), indent=2) if entry.get('result_after') else 'No updated result'}
            """
            formatted_history.append(formatted_entry)

        return f"""
        Total Step 3 feedback entries: {len(step3_history)}

        {''.join(formatted_history)}

        IMPORTANT: Use this history to identify patterns, recurring issues, and previously learned corrections.
        Build upon all previous learnings rather than treating each feedback in isolation.
        """