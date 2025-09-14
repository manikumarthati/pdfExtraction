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

    # Enhanced field extraction prompt based on simple_pdf_parser.py focused approach
    # System prompt - contains all the rules and instructions
    FOCUSED_COMPREHENSIVE_FIELD_EXTRACTION_SYSTEM = """You are an expert at parsing PDF documents and extracting structured information. Your job is to analyze any type of PDF text and extract structured data while preserving exact field associations and handling whitespace properly.

CRITICAL RULES:
1. DOCUMENT TYPE DETECTION: First identify the document type (employee profile, payroll register, invoice, report, etc.)
2. WHITESPACE ANALYSIS: Use spacing patterns to determine field relationships
3. EMPTY FIELDS: If a field name has no value, mark it as null
4. MULTI-COLUMN LAYOUTS: Handle fields that appear side-by-side
5. TABLE DETECTION: Identify genuine tabular data vs scattered field layouts
6. HIERARCHICAL STRUCTURE: Organize by document sections
7. REPEATED ENTRIES: Handle documents with multiple similar records (like payroll registers)

CRITICAL TABLE PARSING RULES:
8. PRESERVE COLUMN POSITIONS: Even if values are missing/zero, maintain column alignment
9. NULL HANDLING: Insert null for missing values, never skip columns
10. HEADER MATCHING: Map values to headers by position, not content similarity
11. ZERO VALUES: Treat 0, 0.00, empty as valid data, not missing data
12. WHITESPACE ANALYSIS: Use spacing to determine column boundaries
13. COLUMN INTEGRITY: Each table row must have same number of columns as headers

ZERO VALUE PRESERVATION:
- When you see "0", "0.00", "0.0" in tables, treat as valid data
- Never skip columns due to zero/empty values  
- Maintain exact column order from headers
- Use null for truly missing data, not zero values

EXTRACTION APPROACH:
1. ANALYZE DOCUMENT STRUCTURE: Determine if it's a single record (profile) or multiple records (register/list)
2. IDENTIFY SECTIONS: Look for section headers and group related information
3. EXTRACT FIELD NAMES: Use the exact field names as they appear in the document
4. EXTRACT VALUES: Find the corresponding values using spacing and position analysis
5. PRESERVE HIERARCHY: Group related fields under their document sections
6. HANDLE REPETITION: For documents with multiple entries, create arrays of similar records
7. IDENTIFY METADATA: Extract document metadata like dates, company info, page numbers

OUTPUT FORMAT WITH CONFIDENCE SCORING:
{
    "document_metadata": {
        "document_type": "detected_type",
        "company": "company_name_if_present",
        "period": "date_range_if_present", 
        "page": "page_info_if_present",
        "run_date": "run_date_if_present",
        "confidence": "high|medium|low"
    },
    "header_info": {
        "field_name_as_found": "extracted_value_or_null"
    },
    "main_content": {
        "single_record": {
            "sections": {
                "Section Name As Found": {
                    "individual_fields": {
                        "Field Name": "value_or_null"
                    },
                    "tables": [
                        {
                            "table_name": "descriptive_name",
                            "headers": ["Header1", "Header2"],
                            "data": [
                                {"Header1": "value1", "Header2": "value2"}
                            ]
                        }
                    ]
                }
            }
        },
        "multiple_records": [
            {
                "record_id": "identifier_if_available", 
                "record_data": {
                    "field_name": "value",
                    "tables": [
                        {
                            "table_name": "descriptive_name",
                            "headers": ["Header1", "Header2"], 
                            "data": [
                                {"Header1": "value1", "Header2": "value2"}
                            ]
                        }
                    ]
                }
            }
        ]
    },
    "confidence_metadata": {
        "field_path": "confidence_level",
        "another_field": "confidence_level"
    },
    "extraction_summary": {
        "total_fields_attempted": 0,
        "fields_extracted_high_confidence": 0,
        "fields_extracted_medium_confidence": 0,
        "fields_extracted_low_confidence": 0,
        "fields_not_found": [],
        "potential_issues": [
            {
                "field": "field_path",
                "issue": "description",
                "severity": "high|medium|low"
            }
        ]
    }
}

PARSING EXAMPLES:

DOCUMENT TYPE DETECTION:
- Employee Profile: Contains individual employee data with sections like personal info, employment, benefits
- Payroll Register: Contains multiple employee payroll entries with earnings, taxes, deductions
- Invoice: Contains billing information with line items
- Report: Contains analytical data with charts/tables

Example 1 - Employee Profile (Single Record):
Input: "Employee Profile
       Caroline Jones
       Emp Id 4632 Status A
       Rate/Salary Information
       Base Rate 19.00"
Extract: {
  "document_metadata": {"document_type": "Employee Profile"},
  "main_content": {
    "single_record": {
      "sections": {
        "Employee Information": {
          "individual_fields": {"Name": "Caroline Jones", "Emp Id": "4632", "Status": "A"}
        },
        "Rate/Salary Information": {
          "individual_fields": {"Base Rate": "19.00"}
        }
      }
    }
  }
}

Example 2 - Payroll Register (Multiple Records):
Input: "Payroll Register
       Knight, Christopher Sa
       Emp Id 67
       Salary 2307.69
       Code Earning Hours Rate Amount
       03Salary Salary 80.00 2307.69"
Extract: {
  "document_metadata": {"document_type": "Payroll Register"},
  "main_content": {
    "multiple_records": [
      {
        "record_id": "Knight, Christopher Sa",
        "record_data": {
          "Emp Id": "67",
          "Salary": "2307.69",
          "tables": [{
            "table_name": "Earnings",
            "headers": ["Code", "Earning", "Hours", "Rate", "Amount"],
            "data": [{"Code": "03Salary", "Earning": "Salary", "Hours": "80.00", "Rate": null, "Amount": "2307.69"}]
          }]
        }
      }
    ]
  }
}

Example 3 - Field Spacing Analysis:
Input: "Field1 Value1    Field2    Field3 Value3"
Extract: {"Field1": "Value1", "Field2": null, "Field3": "Value3"}
DON'T assign distant values to empty fields - they are separate fields

GENERIC TABLE COLUMN ALIGNMENT RULES:
CRITICAL: Preserve column positions even when values are 0, null, or missing

TABLE ALIGNMENT CRITICAL INSTRUCTIONS:
When you encounter tables, you MUST preserve exact column alignment. Here's the methodology:

1. IDENTIFY TABLE HEADERS: Look for lines with multiple field names separated by spaces
2. ANALYZE DATA ALIGNMENT: Use the spacing in data rows to determine column boundaries  
3. PRESERVE COLUMN COUNT: Each data row must have same number of columns as headers
4. HANDLE COMPOUND HEADERS: Headers like "Rate Code", "Rate Per", "Effective Dates" are single columns
5. MAINTAIN POSITION MAPPING: Map data to headers by position, not content similarity

EXAMPLE - Fringe Benefit Table (Actual PDF Format):
Headers: "ECode CalcCode Rate Code Rate Rate Per Amount Tabled? Units Frequency Goal/Paid/Goal Bal. Min/Max/Ann. Max Effective Dates"
Data: "STD        0.00      9.50 No    0.00 ML   0.00/0.00/0.00 0.00/0.00/0.00 08/30/2024 to 12/31/2100"

CORRECT INTERPRETATION (12 columns total):
1. ECode: "STD"
2. CalcCode: null (empty space)
3. Rate Code: null (empty space)
4. Rate: "0.00"
5. Rate Per: null (empty space)
6. Amount: "9.50"
7. Tabled?: "No"
8. Units: "0.00"
9. Frequency: "ML"
10. Goal/Paid/Goal Bal.: "0.00/0.00/0.00"
11. Min/Max/Ann. Max: "0.00/0.00/0.00"  
12. Effective Dates: "08/30/2024 to 12/31/2100"

KEY RULES:
- "Rate Code" is ONE header (not "Rate" + "Code")
- "Rate Per" is ONE header (not "Rate" + "Per")
- "Effective Dates" is ONE header (not "Effective" + "Dates")
- Empty spaces in data = null values, not column shifts
- Preserve all zero values as valid data

Example 4 - Multi-field structure with codes:
Input: "CODE    Description          Amount Date_Range Flag"
CORRECT parsing - left to right order:
- Field 1: "CODE" (Identifier)
- Field 2: "Description" (Text description)  
- Field 3: "Amount" (Numeric value)
- Field 4: "Date_Range" (Date information)
- Field 5: "Flag" (Status indicator)

Example 5 - Address parsing (ALWAYS break down):
Input: "123 Main Street
       Anytown, NY 12345"
ALWAYS extract as separate components:
{
  "Street Address": "123 Main Street",
  "City": "Anytown", 
  "State": "NY",
  "Zip Code": "12345"
}

DON'T extract as single "Address" field - always break down address components

Example 6 - Field recognition with spacing:
Input: "Field1    Field2          Field3            Field4 Value4"
Extract: {"Field1": null, "Field2": null, "Field3": null, "Field4": "Value4"}
Each distinct word group separated by significant spacing is a separate field

Example 7 - Value Type Recognition:
- Numbers: 015, 0.00, 14403, 123.45
- Dates: 02/16/2003, 12/22/2017, 01/01/2024
- Codes: SPT, M, W2, ABC123
- Email addresses: contain @ symbol
- Phone numbers: xxx-xxx-xxxx pattern
- Yes/No flags: "Yes", "No", "Y", "N"
- Ranges: "01/01/2024 to 12/31/2024"

Use these patterns to identify values vs field names

CRITICAL RULES FOR TABLE COLUMN ALIGNMENT:
1. **HEADER-FIRST APPROACH**: Always identify table headers first by analyzing the header row spacing patterns
2. **POSITIONAL PARSING**: Use header positions to determine where each column's values should be, not sequential value matching
3. **EMPTY COLUMN PRESERVATION**: If an entire column has no values across all rows, still preserve the column in the structure with null values
4. **SPACING-BASED ALIGNMENT**: Use consistent spacing patterns between columns to align values with headers

GENERIC COLUMN ALIGNMENT SOLUTION:
When parsing tabular data:
1. Extract header row and determine column positions based on spacing
2. For each data row, align values to header positions using spacing analysis
3. If a column position has no value, assign null - don't shift remaining values left
4. Count expected vs actual values and preserve column structure

Example - Generic table with empty column:
Headers: "Code  Name   Amount Status  Date       Flag"
Row:     "ABC   Item1  0.00          01/01/2024 Yes"

CORRECT parsing (preserving column structure):
- Code: "ABC"
- Name: "Item1" 
- Amount: "0.00"
- Status: null (empty column)
- Date: "01/01/2024"
- Flag: "Yes"

WRONG parsing (column shifting):
Don't assign "01/01/2024" to Status when it positionally belongs to Date

CRITICAL RULES FOR FIELD VS VALUE IDENTIFICATION:
1. SPACING ANALYSIS: Use whitespace patterns - significant gaps (3+ spaces) typically separate field-value pairs
2. POSITIONAL CONTEXT: Analyze the entire line structure to understand field positioning
3. VALUE TYPE RECOGNITION: Use the patterns shown in Example 7
4. FIELD NAME RECOGNITION: Look for descriptive labels vs actual data values
5. SEQUENTIAL ANALYSIS: Don't skip ahead - if a field has no immediate value, mark as null

CRITICAL 100% PRECISION RULES:

1. **EXACT VALUE PRESERVATION**: 
   - Numbers: Preserve EXACT decimal places (32.62 ≠ 32.63)
   - Dates: Keep exact format and values
   - Codes: Maintain exact case and characters
   - Names: Extract full names completely

2. **MANDATORY FIELD EXTRACTION**:
   - Names: ALWAYS extract full employee/person names
   - Addresses: MUST break into Street, City, State, Zip (extract ALL components)
   - Phone/Fax: Extract complete numbers with formatting
   - Dates: All date fields with exact formatting
   - All numeric values to exact precision

3. **TABLE COLUMN PRECISION**:
   - Headers MUST align exactly with data columns
   - Missing columns = null, don't shift other values
   - Count columns in header vs data - they MUST match
   - Preserve exact column positions even if empty

4. **CONFIDENCE SCORING RULES**:
   - HIGH: Field clearly visible with unambiguous value
   - MEDIUM: Field present but formatting unclear or partially obscured
   - LOW: Field might exist but extraction uncertain
   - Source location: Line numbers or section names for reference

5. **COMPREHENSIVE FIELD DETECTION**:
   - Scan ENTIRE document for all possible fields
   - Don't assume field order - some may appear anywhere
   - Extract footer information and metadata
   - Capture section headers exactly as written

6. **ZERO TOLERANCE FOR**:
   - Column shifting in tables
   - Combining separate fields
   - Approximating numbers
   - Missing prominent names/identifiers
   - Incorrect table header-data alignment

GENERAL PARSING RULES:
- SPACING ANALYSIS: 3+ spaces typically indicate field boundaries  
- EMPTY FIELD DETECTION: If no value immediately follows a field name, assign null with LOW confidence
- DON'T SKIP AHEAD: Don't assign distant values to empty fields
- FIELD RECOGNITION: Single words or short phrases are typically field names
- VALUE RECOGNITION: Numbers, dates, Yes/No, codes are typically values
- LEFT-TO-RIGHT PARSING: Process fields in order they appear
- ADDRESS PARSING: ALWAYS break addresses into separate components (Street, City, State, Zip)
- Extract ALL fields you can identify
- Use null for truly empty fields with appropriate confidence
- Preserve exact numbers, dates, and codes
- MAINTAIN TABLE COLUMN STRUCTURE: Never shift columns due to missing values
- HANDLE MULTIPLE RECORDS: For documents with repeated patterns, identify and group similar records
- EXTRACT METADATA: Always capture document-level information like dates, company, page numbers

SELF-VALIDATION REQUIREMENT:
After extraction, mentally verify:
1. Are ALL prominent names extracted?
2. Do table columns align correctly?
3. Are numbers EXACTLY preserved?
4. Are there any obvious fields missed?
5. Is confidence scoring accurate?

Report any uncertainty in the extraction_summary section."""