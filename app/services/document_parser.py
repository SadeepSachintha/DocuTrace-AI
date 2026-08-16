import fitz  # PyMuPDF
from langdetect import detect
from typing import List, Dict, Any, Tuple

class DocumentParserService:
    @staticmethod
    def extract_text_with_pages(pdf_bytes: bytes) -> Tuple[List[Dict[str, Any]], str, int]:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_content = []
        full_text_sample = ""

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:
                pages_content.append({"page": page_num + 1, "text": text})
                if len(full_text_sample) < 1000:
                    full_text_sample += " " + text

        try:
            detected_lang = detect(full_text_sample) if full_text_sample.strip() else "en"
        except Exception:
            detected_lang = "en"

        return pages_content, detected_lang, len(doc)

    @staticmethod
    def chunk_text(pages: List[Dict[str, Any]], chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
        chunks = []
        
        for page_data in pages:
            text = page_data["text"]
            words = text.split()
            page_num = page_data["page"]
            
            if len(words) <= chunk_size:
                chunks.append({"content": text, "page": page_num})
                continue
                
            start = 0
            while start < len(words):
                end = start + chunk_size
                chunk_words = words[start:end]
                chunks.append({
                    "content": " ".join(chunk_words),
                    "page": page_num
                })
                start += chunk_size - chunk_overlap
                
        return chunks
