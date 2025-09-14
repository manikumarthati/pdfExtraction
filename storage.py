"""
Simple file-based storage system to replace SQLAlchemy
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

class Document:
    def __init__(self, id: str = None, filename: str = "", filepath: str = ""):
        self.id = id or str(uuid.uuid4())
        self.filename = filename
        self.filepath = filepath
        self.upload_time = datetime.now()
        self.current_step = 1
        self.is_completed = False
        self.step1_result = None
        self.step2_result = None
        self.step2_validated_json = None  # Store user-validated JSON from Step 2
        self.step3_result = None
        self.feedback_history = []  # Track user feedback iterations

        # Multi-page processing fields
        self.validation_page_result = None
        self.validation_page_num = None
        self.enhanced_template = None
        self.multipage_processing_status = None
    
    def set_step_result(self, step: int, result: dict):
        if step == 1:
            self.step1_result = result
        elif step == 2:
            self.step2_result = result
        elif step == 3:
            self.step3_result = result
    
    def get_step_result(self, step: int) -> Optional[dict]:
        if step == 1:
            return self.step1_result
        elif step == 2:
            return self.step2_result
        elif step == 3:
            return self.step3_result
        return None
    
    def add_feedback(self, step: int, user_feedback: str, result_before: dict = None, result_after: dict = None):
        """Add feedback entry to history"""
        feedback_entry = {
            'step': step,
            'timestamp': datetime.now().isoformat(),
            'user_feedback': user_feedback,
            'result_before': result_before,
            'result_after': result_after,
            'iteration': len([f for f in self.feedback_history if f.get('step') == step]) + 1
        }
        self.feedback_history.append(feedback_entry)
    
    def get_feedback_history(self, step: int = None) -> List[dict]:
        """Get feedback history, optionally filtered by step"""
        if step is None:
            return self.feedback_history
        return [f for f in self.feedback_history if f.get('step') == step]
    
    def get_latest_feedback(self, step: int) -> Optional[dict]:
        """Get the most recent feedback for a specific step"""
        step_feedback = self.get_feedback_history(step)
        return step_feedback[-1] if step_feedback else None
    
    def set_step2_validated_json(self, validated_json: dict):
        """Save the user-validated JSON from Step 2"""
        self.step2_validated_json = validated_json
    
    def get_step2_validated_json(self) -> Optional[dict]:
        """Get the user-validated JSON from Step 2"""
        return self.step2_validated_json
    
    def has_validated_step2(self) -> bool:
        """Check if Step 2 has been validated by user"""
        return self.step2_validated_json is not None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'filename': self.filename,
            'filepath': self.filepath,
            'upload_time': self.upload_time.isoformat(),
            'current_step': self.current_step,
            'is_completed': self.is_completed,
            'step1_result': self.step1_result,
            'step2_result': self.step2_result,
            'step2_validated_json': self.step2_validated_json,
            'step3_result': self.step3_result,
            'feedback_history': self.feedback_history,
            'validation_page_result': self.validation_page_result,
            'validation_page_num': self.validation_page_num,
            'enhanced_template': self.enhanced_template,
            'multipage_processing_status': self.multipage_processing_status
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Document':
        doc = cls(
            id=data['id'],
            filename=data['filename'],
            filepath=data['filepath']
        )
        doc.upload_time = datetime.fromisoformat(data['upload_time'])
        doc.current_step = data['current_step']
        doc.is_completed = data['is_completed']
        doc.step1_result = data.get('step1_result')
        doc.step2_result = data.get('step2_result')
        doc.step2_validated_json = data.get('step2_validated_json')
        doc.step3_result = data.get('step3_result')
        doc.feedback_history = data.get('feedback_history', [])

        # Multi-page processing fields
        doc.validation_page_result = data.get('validation_page_result')
        doc.validation_page_num = data.get('validation_page_num')
        doc.enhanced_template = data.get('enhanced_template')
        doc.multipage_processing_status = data.get('multipage_processing_status')
        return doc

class FileStorage:
    def __init__(self, storage_file: str = 'documents.json'):
        self.storage_file = storage_file
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w') as f:
                json.dump([], f)
    
    def _load_documents(self) -> List[Document]:
        try:
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
                return [Document.from_dict(doc_data) for doc_data in data]
        except (json.JSONDecodeError, KeyError):
            return []
    
    def _save_documents(self, documents: List[Document]):
        with open(self.storage_file, 'w') as f:
            data = [doc.to_dict() for doc in documents]
            json.dump(data, f, indent=2)
    
    def add_document(self, document: Document) -> Document:
        documents = self._load_documents()
        documents.append(document)
        self._save_documents(documents)
        return document
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        documents = self._load_documents()
        for doc in documents:
            if doc.id == doc_id:
                return doc
        return None
    
    def update_document(self, document: Document) -> Document:
        documents = self._load_documents()
        for i, doc in enumerate(documents):
            if doc.id == document.id:
                documents[i] = document
                break
        self._save_documents(documents)
        return document
    
    def get_recent_documents(self, limit: int = 10) -> List[Document]:
        documents = self._load_documents()
        # Sort by upload_time descending
        documents.sort(key=lambda x: x.upload_time, reverse=True)
        return documents[:limit]
    
    def delete_document(self, doc_id: str) -> bool:
        documents = self._load_documents()
        original_len = len(documents)
        documents = [doc for doc in documents if doc.id != doc_id]
        if len(documents) < original_len:
            self._save_documents(documents)
            return True
        return False

# Global storage instance
storage = FileStorage()