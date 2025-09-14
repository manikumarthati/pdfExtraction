# PDF Data Extraction Application

A Flask-based web application that intelligently extracts structured data from PDF documents using AI-powered analysis. The application processes PDFs through a three-step pipeline to classify document structure, identify fields, and extract data with high accuracy.

## Features

### 🎯 Three-Step Processing Pipeline
- **Step 1: Structure Classification** - Analyzes document layout and identifies structural patterns
- **Step 2: Field Identification** - Detects form fields, headers, and data regions with multiple extraction modes
- **Step 3: Data Extraction** - Extracts structured data based on identified fields and structure

### 🤖 AI-Powered Extraction
- Multiple OpenAI model integration with task-specific optimization
- Vision-based extraction for complex layouts
- Spatial preprocessing for coordinate-aware field detection
- Feedback-driven iterative improvement

### 📊 Advanced Processing Modes
- **Text-based extraction** - Traditional text parsing
- **Spatial preprocessing** - Coordinate-aware field boundary detection
- **Vision extraction** - Image-based AI analysis for complex documents
- **Hybrid mode** - Combines multiple approaches for optimal results

### 💰 Cost Management
- Task-specific model selection for cost optimization
- Real-time usage tracking and cost analysis
- Configurable model settings per processing step
- Cost optimization suggestions

### 🔧 Interactive Features
- Real-time feedback and refinement
- Field boundary correction interface
- JSON editor for manual corrections
- Preprocessing preview and analysis
- Download results in JSON format

## Installation

### Prerequisites
- Python 3.8 or higher
- OpenAI API key

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/manikumarthati/pdfExtraction.git
   cd pdfExtraction
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv

   # On Windows:
   .venv\Scripts\activate

   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration:**
   ```bash
   # Copy the example environment file
   cp .env.example .env

   # Edit .env file with your settings:
   # - Add your OpenAI API key
   # - Configure model preferences
   # - Set upload/results directories
   ```

5. **Create required directories:**
   ```bash
   mkdir -p uploads results
   ```

6. **Run the application:**
   ```bash
   python app.py
   ```

7. **Access the application:**
   Open your browser and navigate to `http://localhost:5000`

## Configuration

### Environment Variables

The application can be configured through environment variables in the `.env` file:

#### Required Settings
```env
OPENAI_API_KEY=your_openai_api_key_here
FLASK_SECRET_KEY=your_secret_key_here
```

#### Model Configuration (Cost Optimization)
```env
# Structure Classification: Simple task, use cheaper model
CLASSIFICATION_MODEL=gpt-3.5-turbo
CLASSIFICATION_TEMPERATURE=0.0
CLASSIFICATION_MAX_TOKENS=800

# Field Identification: Medium complexity, balance cost and accuracy
FIELD_IDENTIFICATION_MODEL=gpt-4o-mini
FIELD_IDENTIFICATION_TEMPERATURE=0.1
FIELD_IDENTIFICATION_MAX_TOKENS=1200

# Data Extraction: Most critical, use best model for accuracy
DATA_EXTRACTION_MODEL=gpt-4o
DATA_EXTRACTION_TEMPERATURE=0.0
DATA_EXTRACTION_MAX_TOKENS=2000
```

#### Optional Settings
```env
UPLOAD_FOLDER=uploads
RESULTS_FOLDER=results
ENABLE_COST_TRACKING=true
GPT_TIMEOUT=30
GPT_MAX_RETRIES=3
```

## Usage

### Basic Workflow

1. **Upload PDF**: Upload a PDF document through the web interface
2. **Step 1 - Classify Structure**: Analyze document layout and structure type
3. **Step 2 - Identify Fields**: Detect form fields and data regions with multiple extraction modes
4. **Step 3 - Extract Data**: Extract structured data in JSON format
5. **Download Results**: Get the extracted data as a JSON file

### Processing Modes

#### Text-Based Extraction
- Standard text parsing approach
- Good for simple, well-structured documents
- Fastest processing time

#### Spatial Preprocessing
- Uses coordinate information for field boundary detection
- Better for forms with complex layouts
- Analyzes word positioning and clustering

#### Vision-Based Extraction
- AI analyzes the document as an image
- Best for complex layouts, handwritten text, or unusual formats
- Higher accuracy but increased processing cost

### Interactive Features

- **Real-time Feedback**: Provide feedback to improve extraction results
- **Field Boundary Editor**: Visually correct detected field boundaries
- **JSON Editor**: Manually edit extracted data
- **Preprocessing Preview**: See how the document will be processed before extraction

## Project Structure

```
pdfExtraction/
├── app.py                          # Main Flask application
├── config.py                       # Configuration settings
├── storage.py                      # Document storage and management
├── requirements.txt                # Python dependencies
├── .env.example                    # Example environment configuration
├── services/                       # Core processing services
│   ├── pdf_processor.py           # PDF text and structure extraction
│   ├── openai_service.py          # AI/OpenAI integration
│   ├── cost_tracker.py            # Usage and cost tracking
│   ├── spatial_preprocessor.py    # Coordinate-based preprocessing
│   ├── vision_extractor.py        # Vision-based extraction
│   ├── prompts.py                 # AI prompts and templates
│   └── ...
├── templates/                      # HTML templates
│   ├── index.html                 # Main upload interface
│   ├── process.html               # Processing workflow interface
│   ├── costs.html                 # Cost tracking dashboard
│   └── ...
├── uploads/                       # PDF file uploads (created automatically)
└── results/                       # Extracted JSON results (created automatically)
```

## API Endpoints

The application provides REST API endpoints for each processing step:

- `POST /api/step1/<doc_id>` - Structure classification
- `POST /api/step2/<doc_id>` - Field identification
- `POST /api/step3/<doc_id>` - Data extraction
- `POST /api/step2/<doc_id>/refine` - Refine with feedback
- `GET /api/step2/<doc_id>/field-boundaries` - Get field boundaries
- `GET /costs` - Cost tracking dashboard

## Cost Optimization

The application uses different OpenAI models optimized for each task:

- **Classification**: GPT-3.5-turbo (cost-effective for simple tasks)
- **Field Identification**: GPT-4o-mini (balanced accuracy and cost)
- **Data Extraction**: GPT-4o (highest accuracy for critical extraction)

Cost tracking features include:
- Real-time usage monitoring
- Session-based cost analysis
- Optimization recommendations
- Model performance comparisons

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## License

This project is open source and available under the MIT License.

## Support

For questions, issues, or contributions, please:
- Open an issue on GitHub
- Review the documentation and configuration options
- Check the cost tracking dashboard for optimization insights

## Requirements

- Python 3.8+
- OpenAI API access
- Modern web browser for the interface
- Sufficient API credits for document processing

---

**Note**: This application processes documents using OpenAI's API services. Ensure you have sufficient API credits and review OpenAI's pricing for cost planning.