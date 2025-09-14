"""
Externalized prompts for GPT operations
All prompts are stored here for easy modification and version control
"""

class PromptTemplates:
    """Collection of prompt templates for different operations"""
    
    STRUCTURE_CLASSIFICATION = """
    Analyze this PDF page and classify its structure. 

    Document Info:
    - Total text length: {text_length} characters
    - Total text blocks: {total_blocks}
    
    Sample text content:
    {sample_text}
    
    Classify this page as one of:
    1. "form" - Contains form fields with labels and values (like applications, invoices)
    2. "table" - Contains tabular data with rows and columns
    3. "mixed" - Contains both form elements and tables
    
    Also identify the main regions and provide confidence score.
    
    You MUST respond with valid JSON only. No additional text or explanation.
    
    {{
        "classification": "form|table|mixed",
        "confidence": 0.85,
        "reasoning": "Brief explanation of classification",
        "regions": [
            {{
                "type": "form|table", 
                "description": "Description of this region",
                "estimated_bounds": "top|middle|bottom"
            }}
        ]
    }}
    """
    
    FORM_FIELD_IDENTIFICATION = """
    Analyze this content and identify FORM FIELDS ONLY - individual labeled fields with values.
    
    Text content:
    {text}
    
    FORM FIELDS are:
    - Individual labels followed by values (Name: John Doe)  
    - Input field labels (First Name, Last Name, Address)
    - Single data points with descriptive labels
    - Fields that appear once or rarely (not in repeating table rows)
    
    IMPORTANT: 
    - If a field has no value after the label, set "estimated_value": null
    - Look for patterns like "Label:" followed by blank space or "Label: ___" 
    - Include fields even if they appear empty
    - DO NOT include table column headers or repeated row data
    - Focus on document metadata, employee details, form inputs
    
    You MUST respond with valid JSON only. No additional text or explanation.
    
    {{
        "field_type": "form",
        "fields": [
            {{
                "label": "Field Name",
                "estimated_value": "Extracted value or null if empty",
                "data_type": "text|number|date|currency|boolean",
                "confidence": 0.85,
                "is_empty": true
            }}
        ]
    }}
    """
    
    TABLE_HEADER_IDENTIFICATION = """
    Analyze this content and identify TABLE COLUMN HEADERS ONLY - headers that appear above data columns.
    
    Text content:
    {text}
    
    TABLE HEADERS are:
    - Column names that appear above rows of data
    - Headers that repeat across multiple data rows  
    - Labels for tabular data columns (Employee ID, Name, Department)
    - Headers organized in clear columnar structure
    
    IMPORTANT:
    - Focus on identifying true tabular structures with rows and columns
    - Look for alignment patterns and repeated data structures
    - Each table should have clear boundaries and consistent formatting
    - Headers should be followed by actual data rows
    
    DO NOT include:
    - Form field labels that appear once
    - Individual data values
    - Section titles or document headers
    - Standalone label-value pairs
    
    Group headers by logical table if multiple tables exist. Be conservative - only identify clear tabular structures.
    
    You MUST respond with valid JSON only. No additional text or explanation.
    
    {{
        "field_type": "table",
        "tables": [
            {{
                "table_id": 1,
                "description": "Employee Information Table",
                "headers": [
                    {{
                        "name": "Column Name",
                        "data_type": "text|number|date|currency",
                        "position": 0,
                        "has_data": true
                    }}
                ],
                "estimated_rows": 10,
                "table_region": "top|middle|bottom"
            }}
        ]
    }}
    """
    
    EMPLOYEE_PROFILE_EXTRACTION = """
    You are a data extraction specialist. Extract all data from this employee profile PDF following these precise rules:

    ## Core Extraction Principles
    
    ### Field-Value Mapping
    - **Identify all field labels and their corresponding values exactly as they appear**
    - **Mark empty fields as null - do not assume or infer values**
    - **Distinguish between empty fields and zero values (0.00)**
    - **Do not combine separate field labels - treat each as an individual field**
    - **Field proximity does not indicate relationship - verify actual field-value pairing**
    
    ### Date and Numeric Formatting
    - **Parse all dates in MM/DD/YYYY format consistently**
    - **Preserve numeric values with original decimal formatting (19.00, 0.00, etc.)**
    - **Handle percentage values as shown (100.00 for 100%)**
    - **Preserve currency values without adding symbols unless present in original**
    - **Maintain multi-part values exactly as formatted (0.00/14.11/0.00/0.00)**
    
    Text content to extract from:
    {text}
    
    Fields identified to extract: {field_names}
    
    For each field, extract the actual value that appears in the document following the rules above.
    If a field appears to be empty or has no value, set it to null.
    
    You MUST respond with valid JSON only:
    {{
        "extracted_data": {{
            "Field Name 1": "actual value or null if empty",
            "Field Name 2": "actual value or null if empty"
        }},
        "empty_fields_count": 0,
        "extraction_confidence": 0.9,
        "extraction_notes": "Any issues or observations about the extraction"
    }}
    """
    
    FORM_DATA_EXTRACTION = """
    You are a precise data extraction specialist. Extract actual values from this document.

    **EXTRACTION RULES:**
    1. Extract ONLY what is written in the document - no assumptions
    2. If a field label exists but has no value, use null
    3. Preserve exact formatting (dates, numbers, text cases)
    4. Look for patterns like "Label: Value" or "Label Value"
    5. Handle multi-word field names carefully

    **Fields to extract:** {field_names}

    **Document text:**
    {text}

    **Instructions:**
    - For each field name, find the corresponding value in the text
    - Extract the value that comes after the field label
    - If you cannot find a field or its value, use null
    - Maintain original formatting and capitalization

    Respond with valid JSON only:
    {{
        "extracted_data": {{
            "Field Name 1": "exact value from document or null",
            "Field Name 2": "exact value from document or null"
        }},
        "extraction_confidence": 0.9,
        "extraction_notes": "Brief note about any challenges or observations"
    }}
    """
    
    FORM_DATA_EXTRACTION_WITH_FEEDBACK = """
    You are a data extraction specialist. Extract the actual values for these form fields from the text.
    
    *** CRITICAL INSTRUCTIONS ***
    1. Extract ACTUAL values only - what is written in the document
    2. If a field exists but has no value, use null
    3. Do not make assumptions or infer values
    4. Be precise with data formatting (dates, numbers, etc.)
    
    Fields to extract: {field_names}
    
    Text content:
    {text}
    
    User feedback and corrections: {user_feedback}
    
    IMPORTANT: Apply the user's feedback carefully. This is a refinement based on their corrections to improve accuracy.
    
    For each field, extract the actual value that appears in the document following the user's guidance.
    
    Respond with JSON only:
    {{
        "extracted_data": {{
            "Field Name 1": "actual value or null if empty",
            "Field Name 2": "actual value or null if empty"
        }},
        "extraction_confidence": 0.9,
        "feedback_applied": "Brief note on how user feedback was incorporated"
    }}
    """
    
    COMPREHENSIVE_FIELD_EXTRACTION = """
    You are a document structure specialist. Follow these very specific rules to identify and extract FORM FIELDS and TABLE HEADERS from the provided text.
    *** CRITICAL RULES - READ FIRST ***
    1. DO NOT include table headers in form_fields - they go ONLY in the tables section!
    2. DO NOT include actual data values like "John Doe" or "12/26/2001" in field names!
    3. Extract ONLY field labels like "Employee Name", "Birth Date", NOT their values!
    4. Extract ONLY table column headers like "Rate", "Description", NOT table data!
    5. Think Harder while extracting form fields. DO not miss any field though they do not have value.

    You are identifying document STRUCTURE ONLY - field labels and table headers.

    Text to analyze:
    {text}

    User feedback and instructions: {user_feedback}

    ## EXTRACTION GUIDELINES

    **FORM FIELDS (individual labeled data points):**
    - Look for patterns like "Label:" followed by values
    - Extract the LABEL part only (e.g., "Employee Name", "SSN", "DOB")
    - NEVER extract the actual values (e.g., "Caroline Jones", "088-39-6286")
    - These are typically scattered throughout the document as individual items

    **TABLE HEADERS (column names in tabular data):**
    - Look for column headers that appear above rows of data
    - Extract headers like "Rate", "Description", "Effective Dates"
    - These appear in organized tables with multiple rows of data below them
    - DO NOT include these in form_fields - they go in tables section only!

    **WHAT TO IGNORE:**
    - Actual data values (names, numbers, dates)
    - Section titles like "Employee Information" 
    - Page headers/footers
    - Table row data

    ## User Feedback Integration
    If user feedback is provided:
    - Apply their corrections exactly as specified
    - Add missing fields they mention
    - Remove incorrectly identified items they highlight
    - Follow their guidance on field vs table header classification

    **REQUIRED JSON FORMAT:**
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
        "feedback_response": "Brief note on how user feedback was incorporated"
    }}

    *** FINAL REMINDER ***
    - form_fields = individual field LABELS only (not table headers!)
    - tables = table names with their column headers
    - NO actual data values in either section!
    """
    
    COMPREHENSIVE_DATA_EXTRACTION = """
    You are a data extraction specialist. Your job is to extract actual data values from the document text using the VALIDATED field and table structure identified in Step 2.

    Text to extract data from:
    {text}

    {field_structure}

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
    - Be precise - extract only what is actually in the document
    - Maintain original formatting and spacing
    - Do not make assumptions or add data that isn't there
    - Double-check field names match exactly what was validated in Step 2

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
    
    EMPLOYEE_PROFILE_TABLE_EXTRACTION = """
    You are a data extraction specialist for tabular employee data. Follow these precise rules:

    ## Table Extraction Principles
    
    ### Column Header Identification
    - **Read column headers exactly as written in the document**
    - **Map each data value to its precise column position**
    - **Multiple consecutive columns may be empty - mark as null**
    - **Do not assume logical column relationships - follow the actual layout**
    - **Include all visible column headers even if they contain no data**
    
    ### Data Value Extraction
    - **Preserve numeric values with original decimal formatting (19.00, 0.00, etc.)**
    - **Parse all dates in MM/DD/YYYY format consistently**
    - **Handle multi-part values exactly as formatted (0.00/14.11/0.00/0.00)**
    - **Preserve effective date ranges as "start date to end date"**
    - **Mark truly empty cells as null - distinguish from zero values**
    - **Extract tax status codes exactly as shown (S-0, S-1, etc.)**
    
    Column headers to extract: {header_names}
    
    Text content:
    {text}
    
    Extract ALL rows of data for these columns following the rules above.
    
    You MUST respond with valid JSON only:
    {{
        "table_data": [
            {{"Column1": "value1", "Column2": "value2"}},
            {{"Column1": null, "Column2": "value4"}},
            {{"Column1": "0.00", "Column2": null}}
        ],
        "row_count": 3,
        "empty_cells_count": 2,
        "extraction_confidence": 0.9,
        "table_notes": "Any issues with table structure or data extraction"
    }}
    """
    
    # Unified Schema-Based Extraction (Original - Backup)
    UNIFIED_SCHEMA_EXTRACTION_BACKUP = """
    You are a comprehensive data extraction specialist. Extract ALL data from this document using the provided complete schema.

    **SCHEMA PROVIDED:**
    Form Fields: {form_fields_schema}
    Tables: {tables_schema}

    **EXTRACTION RULES:**
    1. **Form Fields**: Extract exact values for each field name. Use null if field exists but has no value.
    2. **Tables**: For each table, extract ALL rows with data for the specified headers.
    3. **Precision**: Preserve original formatting, dates, numbers, and compound values exactly.
    4. **Completeness**: Extract everything in one pass - do not separate forms and tables.

    **Document Text:**
    {text}

    **Required JSON Response:**
    {{
        "form_data": {{
            "Field Name 1": "exact value or null",
            "Field Name 2": "exact value or null"
        }},
        "table_data": [
            {{
                "table_name": "Table Name 1",
                "headers": ["Header1", "Header2", "Header3"],
                "rows": [
                    {{"Header1": "value1", "Header2": "value2", "Header3": null}},
                    {{"Header1": "value3", "Header2": null, "Header3": "value4"}}
                ]
            }}
        ],
        "extraction_summary": {{
            "total_form_fields_extracted": 0,
            "total_tables_extracted": 0,
            "total_table_rows_extracted": 0,
            "extraction_confidence": 0.95
        }}
    }}
    """

    # Enhanced Schema-Based Extraction with LLM Feedback Analysis
    UNIFIED_SCHEMA_EXTRACTION = """
    You are a comprehensive data extraction specialist with enhanced intelligence from user feedback analysis.

    **SCHEMA PROVIDED:**
    Form Fields: {form_fields_schema}
    Tables: {tables_schema}

    **CORE EXTRACTION RULES:**
    1. **Form Fields**: Extract exact values for each field name. Use null if field exists but has no value.
    2. **Tables**: For each table, extract ALL rows with data for the specified headers.
    3. **Precision**: Preserve original formatting, dates, numbers, and compound values exactly.
    4. **Completeness**: Extract everything in one pass - do not separate forms and tables.

    **ENHANCED EXTRACTION INTELLIGENCE:**
    {enhanced_instructions}

    **VALIDATION REQUIREMENTS:**
    {validation_rules}

    **DETECTION IMPROVEMENTS:**
    {detection_improvements}

    **FORMAT HANDLING:**
    {format_handling}

    **Document Text:**
    {text}

    **META-INSTRUCTION:**
    These enhancements are derived from actual user feedback and corrections. Apply them carefully to achieve maximum extraction accuracy while maintaining the core extraction rules above.

    **Required JSON Response:**
    {{
        "form_data": {{
            "Field Name 1": "exact value or null",
            "Field Name 2": "exact value or null"
        }},
        "table_data": [
            {{
                "table_name": "Table Name 1",
                "headers": ["Header1", "Header2", "Header3"],
                "rows": [
                    {{"Header1": "value1", "Header2": "value2", "Header3": null}},
                    {{"Header1": "value3", "Header2": null, "Header3": "value4"}}
                ]
            }}
        ],
        "extraction_summary": {{
            "total_form_fields_extracted": 0,
            "total_tables_extracted": 0,
            "total_table_rows_extracted": 0,
            "extraction_confidence": 0.95,
            "enhancements_applied": true
        }}
    }}
    """

    # Legacy TABLE_DATA_EXTRACTION kept for backward compatibility
    TABLE_DATA_EXTRACTION = """
    Extract tabular data with these column headers:

    Headers: {header_names}

    Text content:
    {text}

    IMPORTANT:
    - Extract ALL rows of data for these columns
    - If a cell is empty or has no value, use null
    - Preserve data types (numbers as numbers, dates as strings)
    - Look for aligned data under each header
    - Include rows even if some cells are empty

    Respond with JSON:
    {{
        "table_data": [
            {{"Column1": "value1", "Column2": "value2"}},
            {{"Column1": null, "Column2": "value4"}}
        ],
        "row_count": 2,
        "empty_cells_count": 1
    }}
    """