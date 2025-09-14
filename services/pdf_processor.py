import fitz  # PyMuPDF
import os
from typing import Dict, List, Any

class PDFProcessor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
    
    def extract_text_and_structure(self, page_num: int = 0) -> Dict[str, Any]:
        """Extract text and basic structure info from a PDF page with word-level coordinates"""
        if page_num >= len(self.doc):
            raise ValueError(f"Page {page_num} does not exist")
        
        page = self.doc[page_num]
        
        # Extract text
        text = page.get_text()
        
        # Extract word-level coordinates
        word_coordinates = self.extract_word_coordinates(page)
        
        # Extract text blocks with positions (for backward compatibility)
        blocks = page.get_text("dict")["blocks"]
        text_blocks = []
        
        for block in blocks:
            if "lines" in block:  # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        text_blocks.append({
                            "text": span["text"],
                            "bbox": span["bbox"],  # [x0, y0, x1, y1]
                            "font": span["font"],
                            "size": span["size"]
                        })
        
        # Get page dimensions
        page_rect = page.rect
        
        return {
            "page_num": page_num,
            "text": text,
            "text_blocks": text_blocks,
            "word_coordinates": word_coordinates,  # New word-level data
            "page_width": page_rect.width,
            "page_height": page_rect.height,
            "total_pages": len(self.doc)
        }
    
    def extract_word_coordinates(self, page) -> List[Dict[str, Any]]:
        """Extract individual word coordinates from PDF page"""
        words = page.get_text("words")  # PyMuPDF's word extraction
        word_list = []
        
        for word_info in words:
            # word_info format: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            x0, y0, x1, y1, word_text, block_no, line_no, word_no = word_info
            
            # Skip empty words or whitespace-only
            if not word_text.strip():
                continue
                
            word_data = {
                "text": word_text,
                "x0": x0,
                "y0": y0, 
                "x1": x1,
                "y1": y1,
                "center_x": (x0 + x1) / 2,
                "center_y": (y0 + y1) / 2,
                "width": x1 - x0,
                "height": y1 - y0,
                "block_no": block_no,
                "line_no": line_no,
                "word_no": word_no
            }
            word_list.append(word_data)
        
        # Sort by reading order (top to bottom, left to right)
        word_list.sort(key=lambda w: (w["y0"], w["x0"]))
        
        return word_list
    
    def get_page_count(self) -> int:
        """Get total number of pages"""
        return len(self.doc)
    
    def close(self):
        """Close the PDF document"""
        self.doc.close()