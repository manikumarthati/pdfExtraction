from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os,time
import json
from datetime import datetime

from config import Config, GPTConfig
from storage import Document, storage
from services.pdf_processor import PDFProcessor
from services.openai_service import OpenAIService
from services.cost_tracker import CostTracker
from services.spatial_preprocessor import SpatialPreprocessor
# Temporarily commenting out to fix Step 3 error
# from services.multipage_processor import MultiPageProcessor

app = Flask(__name__)
app.config.from_object(Config)

# Initialize services
openai_service = None
cost_tracker = CostTracker()
multipage_processor = None

def init_openai_service():
    global openai_service, multipage_processor
    if not openai_service:
        api_key = app.config['OPENAI_API_KEY']
        if not api_key or api_key == 'your_openai_api_key_here':
            return None
        try:
            openai_service = OpenAIService(api_key)
            # Temporarily commenting out to fix Step 3 error
            # multipage_processor = MultiPageProcessor(openai_service)
            return openai_service
        except Exception as e:
            print(f"Failed to initialize OpenAI service: {e}")
            return None
    return openai_service

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main page - show upload form and recent documents"""
    recent_docs = storage.get_recent_documents(limit=10)
    return render_template('index.html', recent_docs=recent_docs)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle PDF file upload"""
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)
        
        # Create document record
        doc = Document(filename=filename, filepath=filepath)
        storage.add_document(doc)
        
        flash(f'File {file.filename} uploaded successfully!')
        return redirect(url_for('process_document', doc_id=doc.id))
    
    flash('Invalid file type. Please upload a PDF file.')
    return redirect(url_for('index'))

@app.route('/process/<doc_id>')
def process_document(doc_id):
    """Main processing interface for a document"""
    doc = storage.get_document(doc_id)
    if not doc:
        flash('Document not found')
        return redirect(url_for('index'))

    # Store current document in session
    session['current_doc_id'] = doc_id

    # Initialize default values to prevent template errors
    try:
        step_status = {
            'step1_status': 'pending',
            'step2_status': 'pending',
            'step3_status': 'pending'
        }
        step_accessibility = {
            'step1_accessible': True,
            'step2_accessible': False,
            'step3_accessible': False
        }
        step_results = {}
        current_step = doc.current_step or 1

        print(f"DEBUG - Initialized variables for document {doc_id}")
        print(f"DEBUG - Initial step_status: {step_status}")

    except Exception as e:
        print(f"ERROR initializing variables: {e}")
        # Fallback to absolute basics
        step_status = {'step1_status': 'pending', 'step2_status': 'pending', 'step3_status': 'pending'}
        step_accessibility = {'step1_accessible': True, 'step2_accessible': False, 'step3_accessible': False}
        step_results = {}
        current_step = 1
    
    # Check if user wants to go to a specific step
    requested_step = request.args.get('step', type=int)
    if requested_step:
        # Determine if step is accessible
        step1_result = doc.get_step_result(1)
        step2_result = doc.get_step_result(2)
        step3_result = doc.get_step_result(3)

        if requested_step == 1:
            # Step 1 is always accessible
            current_step = 1
        elif requested_step == 2:
            # Step 2 accessible if Step 1 has any result (completed or in progress)
            if step1_result:
                current_step = 2
                # Update current step for navigation, but don't require validation
                doc.current_step = max(doc.current_step, 2)
                storage.update_document(doc)
            else:
                flash('Please complete Step 1 first')
                current_step = 1
        elif requested_step == 3:
            # Step 3 accessible if Step 2 has any result (completed or in progress)
            if step2_result:
                current_step = 3
                # Update current step for navigation
                doc.current_step = max(doc.current_step, 3)
                storage.update_document(doc)
            else:
                flash('Please complete Step 2 first')
                current_step = doc.current_step
        else:
            current_step = doc.current_step
    else:
        current_step = doc.current_step
    
    # Update step results and status (initialize above to prevent template errors)
    # Get individual step results for accessibility check
    step1_result = doc.get_step_result(1)
    step2_result = doc.get_step_result(2)
    step3_result = doc.get_step_result(3)

    for step in [1, 2, 3]:
        result = doc.get_step_result(step)
        if result:
            step_results[f'step{step}'] = result
            # Determine step status
            if result.get('human_validated'):
                step_status[f'step{step}_status'] = 'validated'
            else:
                step_status[f'step{step}_status'] = 'completed'
        else:
            step_status[f'step{step}_status'] = 'pending'

    # Update step accessibility
    step_accessibility.update({
        'step1_accessible': True,  # Step 1 always accessible
        'step2_accessible': bool(step1_result),
        'step3_accessible': bool(step2_result)
    })

    # Debug: Print template variables
    print(f"DEBUG - Template variables for {doc_id}:")
    print(f"  step_status: {step_status}")
    print(f"  step_accessibility: {step_accessibility}")
    print(f"  current_step: {current_step}")

    try:
        return render_template('process.html',
                             document=doc,
                             current_step=current_step,
                             step_results=step_results,
                             step_status=step_status,
                             step_accessibility=step_accessibility)
    except Exception as e:
        print(f"ERROR rendering template: {e}")
        print(f"Variables at render time:")
        print(f"  step_status: {step_status}")
        print(f"  step_accessibility: {step_accessibility}")
        print(f"  current_step: {current_step}")
        # Re-raise the exception to see the full error
        raise

@app.route('/api/step1/<doc_id>', methods=['POST'])
def api_step1_classify(doc_id):
    """Step 1: Structure Classification"""
    doc = storage.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    try:
        # Process PDF
        pdf_processor = PDFProcessor(doc.filepath)
        page_data = pdf_processor.extract_text_and_structure(page_num=0)
        
        # Classify structure using OpenAI
        service = init_openai_service()
        if not service:
            return jsonify({'success': False, 'error': 'OpenAI service not available. Please check API key.'}), 500
        
        print(f"DEBUG - Starting structure classification for doc {doc_id}")
        print(f"DEBUG - Text length: {len(page_data['text'])}")
        print(f"DEBUG - Text blocks: {len(page_data['text_blocks'])}")
        
        result = service.classify_structure(
            page_data['text'], 
            page_data['text_blocks']
        )
        
        print(f"DEBUG - Classification result type: {type(result)}")
        print(f"DEBUG - Classification success: {result.get('classification', 'unknown') if isinstance(result, dict) else 'not dict'}")
        
        # Add page info to result
        result['page_data'] = {
            'total_pages': page_data['total_pages'],
            'page_width': page_data['page_width'],
            'page_height': page_data['page_height']
        }
        
        # Save result
        doc.set_step_result(1, result)
        doc.current_step = 2  # Move to next step
        storage.update_document(doc)
        
        # Track costs
        if 'usage' in result:
            cost_tracker.log_usage(result.get('usage'), doc_id)
        
        pdf_processor.close()
        
        return jsonify({
            'success': True, 
            'result': result,
            'usage': result.get('usage', {})
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@app.route('/api/step1/<doc_id>/validate', methods=['POST'])
def api_step1_validate(doc_id):
    """Validate and correct Step 1 results"""
    doc = storage.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    # Handle JSON data
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Request must be JSON'}), 415
    
    corrections = request.get_json()
    if not corrections:
        return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400
    
    current_result = doc.get_step_result(1)
    
    if current_result:
        # Apply human corrections
        current_result.update(corrections)
        current_result['human_validated'] = True
        current_result['validation_timestamp'] = datetime.now().isoformat()
        
        # Save corrected result
        doc.set_step_result(1, current_result)
        storage.update_document(doc)
        
        return jsonify({'success': True, 'result': current_result})
    
    return jsonify({'success': False, 'error': 'No step 1 result found'}), 400

@app.route('/api/step2/<doc_id>', methods=['POST'])
def api_step2_identify_fields(doc_id):
    """Step 2: Field/Header Identification"""
    print(f"DEBUG - Step2 API called for doc_id: {doc_id}")
    
    doc = storage.get_document(doc_id)
    if not doc:
        print(f"DEBUG - Document not found: {doc_id}")
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    print(f"DEBUG - Document found: {doc.filename}")
    
    step1_result = doc.get_step_result(1)
    if not step1_result:
        print(f"DEBUG - Step 1 not completed for doc: {doc_id}")
        return jsonify({'success': False, 'error': 'Step 1 not completed'}), 400
    
    print(f"DEBUG - Step 1 result exists, starting Step 2")
    
    try:
        print(f"DEBUG Step2 - Starting PDF processing for {doc_id}")

        # Get PDF text
        pdf_processor = PDFProcessor(doc.filepath)
        page_data = pdf_processor.extract_text_and_structure(page_num=0)

        print(f"DEBUG Step2 - PDF text extracted, length: {len(page_data['text'])}")
        print(f"DEBUG Step2 - Classification: {step1_result.get('classification', 'unknown')}")

        # Identify fields using OpenAI
        print(f"DEBUG Step2 - Initializing OpenAI service...")
        service = init_openai_service()
        if not service:
            print("DEBUG Step2 - OpenAI service initialization failed")
            return jsonify({'success': False, 'error': 'OpenAI service not available. Please check API key.'}), 500

        print(f"DEBUG Step2 - OpenAI service initialized successfully")
        
        # Get user feedback and preprocessing mode from either form data or JSON
        if request.is_json:
            user_feedback = request.json.get('user_feedback', '')
            preprocessing_mode = request.json.get('preprocessing_mode', 'original')
        else:
            user_feedback = request.form.get('user_feedback', '')
            preprocessing_mode = request.form.get('preprocessing_mode', 'original')
        print(f"DEBUG Step2 - Preprocessing mode: {preprocessing_mode}")
        
        # Handle different extraction modes
        print(f"DEBUG Step2 - Preprocessing mode: {preprocessing_mode}")

        if preprocessing_mode == 'vision':
            print(f"DEBUG Step2 - Using vision-based extraction")
            result = service.identify_fields_with_vision(doc.filepath, page_num=0, user_feedback=user_feedback)
        else:
            print(f"DEBUG Step2 - Using text-based extraction")
            # Use text-based extraction with optional spatial preprocessing
            word_coordinates = page_data.get('word_coordinates') if preprocessing_mode == 'spatial' else None
            print(f"DEBUG Step2 - Word coordinates available: {bool(word_coordinates)}")

            try:
                result = service.identify_fields(page_data['text'], step1_result, user_feedback,
                                               feedback_history=None, word_coordinates=word_coordinates)
                print(f"DEBUG Step2 - identify_fields call completed successfully")
            except Exception as identify_error:
                print(f"ERROR Step2 - identify_fields failed: {identify_error}")
                raise identify_error
        
        print(f"DEBUG Step2 - Result type: {type(result)}")
        print(f"DEBUG Step2 - Result keys: {result.keys() if isinstance(result, dict) else 'not dict'}")
        
        # Debug: Print the result structure
        print("DEBUG - Step 2 Result Structure:")
        print("Type:", type(result))
        print("Keys:", result.keys() if isinstance(result, dict) else "Not a dict")
        if 'raw_content' in result:
            print("Raw AI Response:", result['raw_content'][:500] + "..." if len(result.get('raw_content', '')) > 500 else result.get('raw_content', ''))
        print("Full Result:", result)
        
        # Save result
        doc.set_step_result(2, result)
        doc.current_step = 3  # Move to next step
        storage.update_document(doc)
        
        # Track costs
        if 'usage' in result:
            cost_tracker.log_usage(result.get('usage'), doc_id)
        
        pdf_processor.close()
        
        return jsonify({
            'success': True, 
            'result': result,
            'usage': result.get('usage', {})
        })

    except Exception as e:
        print(f"ERROR Step2 - Exception in api_step2_identify_fields: {e}")
        print(f"ERROR Step2 - Exception type: {type(e)}")
        import traceback
        print(f"ERROR Step2 - Full traceback: {traceback.format_exc()}")

        return jsonify({
            'success': False,
            'error': f"Step 2 processing failed: {str(e)}",
            'error_type': str(type(e).__name__)
        }), 500

@app.route('/api/step2/<doc_id>/validate', methods=['POST'])
def api_step2_validate(doc_id):
    """Validate and correct Step 2 results"""
    doc = storage.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    # Handle JSON data
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Request must be JSON'}), 415
    
    corrections = request.get_json()
    if not corrections:
        return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400
    
    current_result = doc.get_step_result(2)
    
    if current_result:
        # Apply human corrections
        current_result.update(corrections)
        current_result['human_validated'] = True
        current_result['validation_timestamp'] = datetime.now().isoformat()
        
        # Save the validated JSON for future use
        doc.set_step2_validated_json(current_result)
        
        # Save corrected result
        doc.set_step_result(2, current_result)
        storage.update_document(doc)
        
        return jsonify({'success': True, 'result': current_result})
    
    return jsonify({'success': False, 'error': 'No step 2 result found'}), 400

@app.route('/api/step2/<doc_id>/reset-validation', methods=['POST'])
def api_step2_reset_validation(doc_id):
    """Reset Step 2 validation status"""
    doc = storage.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    # Clear the validated JSON
    doc.step2_validated_json = None
    
    # Also remove validation flag from step2_result if present
    step2_result = doc.get_step_result(2)
    if step2_result:
        step2_result['human_validated'] = False
        if 'validation_timestamp' in step2_result:
            del step2_result['validation_timestamp']
        doc.set_step_result(2, step2_result)
    
    storage.update_document(doc)
    
    return jsonify({'success': True, 'message': 'Validation status reset'})

@app.route('/api/step2/<doc_id>/save-edited-fields', methods=['POST'])
def api_step2_save_edited_fields(doc_id):
    """Save user-edited fields from JSON editor"""
    doc = storage.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    try:
        request_data = request.get_json()
        edited_fields = request_data.get('edited_fields')
        
        if not edited_fields:
            return jsonify({'success': False, 'error': 'No edited fields provided'}), 400
        
        # Get the current step2 result
        step2_result = doc.get_step_result(2)
        if not step2_result:
            return jsonify({'success': False, 'error': 'Step 2 not completed'}), 400
        
        # Update the step2 result with edited fields
        step2_result.update(edited_fields)
        step2_result['user_edited'] = True
        step2_result['edit_timestamp'] = datetime.now().isoformat()
        
        # Save the updated result
        doc.set_step_result(2, step2_result)
        storage.update_document(doc)
        
        return jsonify({
            'success': True, 
            'message': 'Field edits saved successfully',
            'updated_result': step2_result
        })
        
    except Exception as e:
        print(f"ERROR - Save edited fields failed: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/step2/<doc_id>/refine', methods=['POST'])
def api_step2_refine(doc_id):
    """Refine Step 2 results with user feedback"""
    doc = storage.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    step1_result = doc.get_step_result(1)
    if not step1_result:
        return jsonify({'success': False, 'error': 'Step 1 not completed'}), 400
    
    # Handle JSON data
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Request must be JSON'}), 415
    
    feedback_data = request.get_json()
    if not feedback_data or 'user_feedback' not in feedback_data:
        return jsonify({'success': False, 'error': 'User feedback is required'}), 400
    
    user_feedback = feedback_data['user_feedback'].strip()
    if not user_feedback:
        return jsonify({'success': False, 'error': 'User feedback cannot be empty'}), 400
    
    try:
        # Store the current result before refinement for history
        current_result = doc.get_step_result(2)
        
        # Get PDF text
        pdf_processor = PDFProcessor(doc.filepath)
        page_data = pdf_processor.extract_text_and_structure(page_num=0)
        
        print(f"DEBUG Step2 Refine - Starting with feedback: {user_feedback[:100]}...")
        print(f"DEBUG Step2 Refine - Current iteration: {len(doc.get_feedback_history(2)) + 1}")
        
        # Get feedback history for this step
        feedback_history = doc.get_feedback_history(2)
        
        # Re-extract with user feedback and full feedback history
        service = init_openai_service()
        if not service:
            return jsonify({'success': False, 'error': 'OpenAI service not available. Please check API key.'}), 500
        
        # Get preprocessing mode from feedback data (default to current behavior for backward compatibility)
        preprocessing_mode = feedback_data.get('preprocessing_mode', 'spatial')  # Default to spatial for refine since it was using coordinates before
        print(f"DEBUG Step2 Refine - Preprocessing mode: {preprocessing_mode}")
        
        # Handle different extraction modes
        if preprocessing_mode == 'vision':
            # Use vision-based extraction
            result = service.identify_fields_with_vision(doc.filepath, page_num=0, user_feedback=user_feedback)
        else:
            # Use text-based extraction with optional spatial preprocessing
            word_coordinates = page_data.get('word_coordinates') if preprocessing_mode == 'spatial' else None
            result = service.identify_fields(page_data['text'], step1_result, user_feedback, feedback_history, 
                                            word_coordinates=word_coordinates)
        
        # Add feedback to history before saving new result
        doc.add_feedback(
            step=2,
            user_feedback=user_feedback,
            result_before=current_result,
            result_after=result
        )
        
        # Save refined result
        doc.set_step_result(2, result)
        storage.update_document(doc)
        
        # Track costs
        if 'usage' in result:
            cost_tracker.log_usage(result.get('usage'), doc_id)
        
        pdf_processor.close()
        
        # Prepare response message
        iteration_num = len(doc.get_feedback_history(2))
        message = f'Extraction refined based on your feedback (Iteration {iteration_num})'
        
        return jsonify({
            'success': True, 
            'result': result,
            'usage': result.get('usage', {}),
            'message': message,
            'iteration': iteration_num,
            'feedback_applied': result.get('feedback_response', 'Feedback processed successfully')
        })
        
    except Exception as e:
        print(f"DEBUG - Exception in step2 refine: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@app.route('/api/step2/<doc_id>/feedback-history', methods=['GET'])
def api_step2_feedback_history(doc_id):
    """Get feedback history for Step 2"""
    doc = storage.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    feedback_history = doc.get_feedback_history(2)
    
    return jsonify({
        'success': True,
        'feedback_history': feedback_history,
        'total_iterations': len(feedback_history)
    })

@app.route('/api/step2/<doc_id>/results', methods=['GET'])
def api_step2_results(doc_id):
    """Get Step 2 extraction results for field boundary editor"""
    doc = storage.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    step2_result = doc.get_step_result(2)
    if not step2_result:
        return jsonify({'success': False, 'error': 'Step 2 not completed'}), 400
    
    return jsonify({
        'success': True,
        'step2_result': step2_result
    })

@app.route('/api/step2/<doc_id>/field-boundaries', methods=['GET'])
def api_step2_field_boundaries(doc_id):
    """Get detected field boundaries for interactive correction"""
    doc = storage.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    try:
        # Get PDF text and coordinates
        pdf_processor = PDFProcessor(doc.filepath)
        page_data = pdf_processor.extract_text_and_structure(page_num=0)
        
        # Get word coordinates
        word_coordinates = page_data.get('word_coordinates', [])
        if not word_coordinates:
            return jsonify({'success': False, 'error': 'No word coordinates available'}), 400
        
        # Detect field boundaries using our spatial preprocessor
        spatial_preprocessor = SpatialPreprocessor()
        
        # Group words into lines
        lines = spatial_preprocessor.group_words_into_lines(word_coordinates)
        
        # Detect field regions for each line
        field_regions = []
        region_id = 0
        
        for line_idx, line in enumerate(lines):
            # Cluster words by proximity within the line
            clusters = spatial_preprocessor.cluster_words_by_proximity(line)
            
            for cluster_idx, cluster in enumerate(clusters):
                region_id += 1
                
                # Determine if this cluster is likely a field name or value
                is_field_candidate = spatial_preprocessor.is_field_pattern(cluster)
                cluster_text = " ".join([w['text'] for w in cluster])
                
                # Calculate bounding box for the cluster
                if not cluster:
                    continue
                    
                min_x = min(word['x0'] for word in cluster)
                max_x = max(word['x1'] for word in cluster)
                min_y = min(word['y0'] for word in cluster)
                max_y = max(word['y1'] for word in cluster)
                
                field_regions.append({
                    'id': region_id,
                    'text': cluster_text,
                    'line_number': line_idx + 1,
                    'cluster_number': cluster_idx + 1,
                    'bounding_box': {
                        'x0': min_x,
                        'y0': min_y,
                        'x1': max_x,
                        'y1': max_y,
                        'width': max_x - min_x,
                        'height': max_y - min_y
                    },
                    'classification': {
                        'is_likely_field': is_field_candidate,
                        'text_type': 'field_name' if is_field_candidate else 'value_or_content',
                        'confidence': 0.8 if is_field_candidate else 0.6
                    },
                    'words': cluster,
                    'suggested_assignment': {
                        'field_name': cluster_text if is_field_candidate else None,
                        'field_value': cluster_text if not is_field_candidate else None,
                        'is_empty_field': is_field_candidate and cluster_idx == len(clusters) - 1
                    }
                })
        
        pdf_processor.close()
        
        return jsonify({
            'success': True,
            'page_dimensions': {
                'width': page_data['page_width'],
                'height': page_data['page_height']
            },
            'field_regions': field_regions,
            'total_regions': len(field_regions),
            'original_text': page_data['text']
        })
        
    except Exception as e:
        print(f"ERROR - Field boundaries detection failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/step2/<doc_id>/preprocessing-preview', methods=['GET'])
def api_step2_preprocessing_preview(doc_id):
    """Get preprocessing preview to see what data will be sent to LLM"""
    doc = storage.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    try:
        # Get PDF text and coordinates
        pdf_processor = PDFProcessor(doc.filepath)
        page_data = pdf_processor.extract_text_and_structure(page_num=0)
        
        # Initialize spatial preprocessor
        preprocessor = SpatialPreprocessor()
        
        # Get original text
        original_text = page_data['text']
        
        # Get word coordinates
        word_coordinates = page_data.get('word_coordinates', [])
        
        # Get spatially processed text
        if word_coordinates:
            processed_text = preprocessor.preprocess_document(word_coordinates)
            
            # Get detailed analysis
            lines = preprocessor.group_words_into_lines(word_coordinates)
            line_analysis = []
            
            for i, line_words in enumerate(lines):
                clusters = preprocessor.cluster_words_by_proximity(line_words)
                cluster_analysis = []
                
                for j, cluster in enumerate(clusters):
                    cluster_text = " ".join([w["text"] for w in cluster])
                    is_field = preprocessor.is_field_pattern(cluster)
                    
                    cluster_analysis.append({
                        'cluster_id': j + 1,
                        'text': cluster_text,
                        'is_field_pattern': is_field,
                        'word_count': len(cluster),
                        'bbox': {
                            'x0': min(w['x0'] for w in cluster),
                            'y0': min(w['y0'] for w in cluster),
                            'x1': max(w['x1'] for w in cluster),
                            'y1': max(w['y1'] for w in cluster)
                        }
                    })
                
                line_text = " ".join([w["text"] for w in line_words])
                processed_line = preprocessor.process_line_for_fields(line_words)
                
                line_analysis.append({
                    'line_id': i + 1,
                    'original_text': line_text,
                    'processed_text': processed_line,
                    'word_count': len(line_words),
                    'cluster_count': len(clusters),
                    'clusters': cluster_analysis
                })
            
            # Get spacing statistics
            spacing_stats = preprocessor.calculate_word_spacing_stats(word_coordinates)
            
            # Get table regions
            table_regions = preprocessor.identify_table_regions(word_coordinates)
            
        else:
            processed_text = original_text
            line_analysis = []
            spacing_stats = {}
            table_regions = []
        
        pdf_processor.close()
        
        return jsonify({
            'success': True,
            'original_text': original_text,
            'processed_text': processed_text,
            'word_count': len(word_coordinates),
            'has_coordinates': bool(word_coordinates),
            'line_analysis': line_analysis,
            'spacing_statistics': spacing_stats,
            'table_regions': table_regions,
            'preprocessing_applied': bool(word_coordinates)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/step3/<doc_id>', methods=['POST'])
def api_step3_extract_data(doc_id):
    """Step 3: Data Extraction"""
    print("=== CLAUDE DEBUG: Step 3 API endpoint called ===")
    print(f"=== CLAUDE DEBUG: Doc ID: {doc_id} ===")
    print(f"=== CLAUDE DEBUG: Request method: {request.method} ===")
    print(f"=== CLAUDE DEBUG: Request is JSON: {request.is_json} ===")
    doc = storage.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    # Use validated JSON if available, otherwise fall back to Step 2 result
    step2_structure = doc.step2_validated_json or doc.get_step_result(2)
    if not step2_structure:
        return jsonify({'success': False, 'error': 'Step 2 not completed'}), 400
    
    # Get user feedback from either form data or JSON
    if request.is_json:
        user_feedback = request.json.get('user_feedback', '')
    else:
        user_feedback = request.form.get('user_feedback', '')
    
    print(f"DEBUG Step3 - User feedback: {user_feedback}")
    
    # Store previous result and get feedback history before applying feedback
    result_before = None
    feedback_history = None
    if user_feedback.strip():
        result_before = doc.get_step_result(3)
        feedback_history = doc.get_feedback_history()  # Get ALL feedback history
        print(f"DEBUG Step3 - Storing previous result for feedback comparison")
        print(f"DEBUG Step3 - Retrieved feedback history with {len(feedback_history)} total entries")
        step3_history = [f for f in feedback_history if f.get('step') == 3]
        print(f"DEBUG Step3 - Step 3 specific feedback history: {len(step3_history)} entries")
    
    try:
        # Get PDF text
        pdf_processor = PDFProcessor(doc.filepath)
        page_data = pdf_processor.extract_text_and_structure(page_num=0)
        
        # Extract data using OpenAI
        service = init_openai_service()
        if not service:
            return jsonify({'success': False, 'error': 'OpenAI service not available. Please check API key.'}), 500
        
        # Determine extraction method based on Step 2 result
        extraction_method = step2_structure.get('extraction_method', 'hybrid_coordinate_text')
        
        if extraction_method == 'vision':
            # Use vision-based data extraction
            result = service.extract_data_with_vision(doc.filepath, step2_structure, page_num=0, user_feedback=user_feedback)
        else:
            # Use hybrid coordinate+text extraction with previous result and feedback history for comprehensive analysis
            result = service.extract_data(page_data['text'], step2_structure, page_data.get('word_coordinates'), user_feedback=user_feedback, previous_result=result_before, feedback_history=feedback_history)
        
        # Log feedback if provided
        if user_feedback.strip() and result_before:
            doc.add_feedback(
                step=3,
                user_feedback=user_feedback,
                result_before=result_before,
                result_after=result
            )
            print(f"DEBUG Step3 - Feedback logged for doc {doc_id}")
        
        # Save result
        doc.set_step_result(3, result)
        doc.is_completed = True
        storage.update_document(doc)
        
        # Save final JSON to file
        result_filename = f"result_{doc_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
        
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Track costs
        if 'usage' in result:
            cost_tracker.log_usage(result.get('usage'), doc_id)
        
        pdf_processor.close()
        
        return jsonify({
            'success': True, 
            'result': result,
            'usage': result.get('usage', {}),
            'download_url': url_for('download_result', doc_id=doc_id)
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@app.route('/api/step3/<doc_id>/validate', methods=['POST'])
def api_step3_validate(doc_id):
    """Final validation and correction of extracted data"""
    doc = storage.get_document(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': 'Document not found'}), 404
    
    # Handle JSON data
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Request must be JSON'}), 415
    
    corrections = request.get_json()
    if not corrections:
        return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400
    
    current_result = doc.get_step_result(3)
    
    if current_result:
        # Apply human corrections
        current_result.update(corrections)
        current_result['human_validated'] = True
        current_result['validation_timestamp'] = datetime.now().isoformat()
        
        # Save corrected result
        doc.set_step_result(3, current_result)
        storage.update_document(doc)
        
        # Update saved JSON file
        result_filename = f"result_{doc_id}_final.json"
        result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
        
        with open(result_path, 'w') as f:
            json.dump(current_result, f, indent=2)
        
        return jsonify({'success': True, 'result': current_result})
    
    return jsonify({'success': False, 'error': 'No step 3 result found'}), 400

@app.route('/download/<doc_id>')
def download_result(doc_id):
    """Download final JSON result"""
    doc = storage.get_document(doc_id)
    if not doc:
        flash('Document not found')
        return redirect(url_for('index'))
    
    if not doc.is_completed:
        flash('Document processing not completed yet')
        return redirect(url_for('process_document', doc_id=doc_id))
    
    result = doc.get_step_result(3)
    if result:
        from flask import Response
        
        json_str = json.dumps(result, indent=2)
        
        return Response(
            json_str,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment;filename=result_{doc_id}.json'}
        )
    
    flash('No result found for this document')
    return redirect(url_for('process_document', doc_id=doc_id))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded PDF files"""
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/costs')
def costs_dashboard():
    """Cost tracking dashboard"""
    session_summary = cost_tracker.get_session_summary()
    cost_analysis = cost_tracker.get_cost_analysis(days=7)
    suggestions = cost_tracker.get_cost_optimization_suggestions()
    
    return render_template('costs.html',
                         session_summary=session_summary,
                         cost_analysis=cost_analysis,
                         suggestions=suggestions)

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.route('/api/test-debug', methods=['GET'])
def test_debug():
    """Test endpoint to verify Flask is running updated code"""
    print("=== CLAUDE DEBUG: Test endpoint called successfully ===")
    return jsonify({"message": "Flask server is running updated code", "timestamp": time.time()})

# ======= NEW MULTI-PAGE PROCESSING ENDPOINTS =======
# Temporarily disabled to fix Step 3 error - will be re-enabled after testing

if __name__ == '__main__':    
    print("Starting PDF Processing Application...")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Results folder: {app.config['RESULTS_FOLDER']}")
    print("Access the application at: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)