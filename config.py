import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'dev-secret-key'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    RESULTS_FOLDER = os.environ.get('RESULTS_FOLDER') or 'results'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///pdf_processing.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

class GPTConfig:
    """Configuration for GPT models and prompts with cost optimization"""
    
    # Task-specific model selection for cost optimization
    # Structure Classification: Simple task, can use cheaper model
    CLASSIFICATION_MODEL = os.environ.get('CLASSIFICATION_MODEL') or 'gpt-3.5-turbo'
    
    # Field Identification: Medium complexity, may need better model for accuracy
    FIELD_IDENTIFICATION_MODEL = os.environ.get('FIELD_IDENTIFICATION_MODEL') or 'gpt-4o-mini'
    
    # Data Extraction: Most critical for accuracy, use best model
    DATA_EXTRACTION_MODEL = os.environ.get('DATA_EXTRACTION_MODEL') or 'gpt-4o'
    
    # Fallback model for any task
    DEFAULT_MODEL = os.environ.get('GPT_DEFAULT_MODEL') or 'gpt-4o-mini'
    
    # Temperature settings per task
    CLASSIFICATION_TEMPERATURE = float(os.environ.get('CLASSIFICATION_TEMPERATURE', '0.0'))
    FIELD_IDENTIFICATION_TEMPERATURE = float(os.environ.get('FIELD_IDENTIFICATION_TEMPERATURE', '0.0'))
    DATA_EXTRACTION_TEMPERATURE = float(os.environ.get('DATA_EXTRACTION_TEMPERATURE', '0.0'))
    
    # Timeout and retry settings
    TIMEOUT = int(os.environ.get('GPT_TIMEOUT', '90'))
    MAX_RETRIES = int(os.environ.get('GPT_MAX_RETRIES', '3'))
    
    # Token limits for different operations (optimized per model)
    CLASSIFICATION_MAX_TOKENS = int(os.environ.get('CLASSIFICATION_MAX_TOKENS', '800'))
    FIELD_IDENTIFICATION_MAX_TOKENS = int(os.environ.get('FIELD_IDENTIFICATION_MAX_TOKENS', '12000'))
    DATA_EXTRACTION_MAX_TOKENS = int(os.environ.get('DATA_EXTRACTION_MAX_TOKENS', '12000'))
    
    # Cost tracking
    ENABLE_COST_TRACKING = os.environ.get('ENABLE_COST_TRACKING', 'true').lower() == 'true'
    
    @classmethod
    def get_model_config(cls, task_type: str) -> dict:
        """Get optimized model configuration for specific task"""
        configs = {
            'classification': {
                'model': cls.CLASSIFICATION_MODEL,
                'temperature': cls.CLASSIFICATION_TEMPERATURE,
                'max_tokens': cls.CLASSIFICATION_MAX_TOKENS,
                'reasoning': 'Simple classification task - cheaper model sufficient'
            },
            'field_identification': {
                'model': cls.FIELD_IDENTIFICATION_MODEL,
                'temperature': cls.FIELD_IDENTIFICATION_TEMPERATURE,
                'max_tokens': cls.FIELD_IDENTIFICATION_MAX_TOKENS,
                'reasoning': 'Medium complexity - balance cost and accuracy'
            },
            'data_extraction': {
                'model': cls.DATA_EXTRACTION_MODEL,
                'temperature': cls.DATA_EXTRACTION_TEMPERATURE,
                'max_tokens': cls.DATA_EXTRACTION_MAX_TOKENS,
                'reasoning': 'Critical accuracy task - use best model'
            },
            'feedback_analysis': {
                'model': cls.DATA_EXTRACTION_MODEL,  # Use best model for feedback analysis
                'temperature': cls.DATA_EXTRACTION_TEMPERATURE,
                'max_tokens': cls.DATA_EXTRACTION_MAX_TOKENS,
                'reasoning': 'Critical for learning from user feedback'
            },
            'enhancement_generation': {
                'model': cls.DATA_EXTRACTION_MODEL,
                'temperature': cls.DATA_EXTRACTION_TEMPERATURE,
                'max_tokens': cls.DATA_EXTRACTION_MAX_TOKENS,
                'reasoning': 'Important for generating extraction improvements'
            }
        }
        
        return configs.get(task_type, {
            'model': cls.DEFAULT_MODEL,
            'temperature': 0.0,
            'max_tokens': 12000,
            'reasoning': 'Default configuration'
        })