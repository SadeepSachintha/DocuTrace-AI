import fitz  # PyMuPDF
from langdetect import detect
from typing import List, Dict, Any, Tuple

class DocumentParserService:
    @staticmethod
    def format_as_markdown_table(data: List[List[str]]) -> str:
        if not data or not data[0]:
            return ""
        headers = data[0]
        headers = [str(h).strip() if h is not None else "" for h in headers]
        separator = ["---"] * len(headers)
        rows = []
        for row in data[1:]:
            row_str = [str(cell).strip() if cell is not None else "" for cell in row]
            rows.append("| " + " | ".join(row_str) + " |")
        
        return "| " + " | ".join(headers) + " |\n| " + " | ".join(separator) + " |\n" + "\n".join(rows)

    @staticmethod
    def extract_text_with_pages(pdf_bytes: bytes) -> Tuple[List[Dict[str, Any]], str, int]:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_content = []
        full_text_sample = ""

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            
            # Detect tables on page
            try:
                tables = page.find_tables()
                table_markdowns = []
                if tables:
                    for table in tables:
                        table_data = table.extract()
                        if table_data:
                            markdown_table = DocumentParserService.format_as_markdown_table(table_data)
                            if markdown_table:
                                table_markdowns.append(markdown_table)
                
                if table_markdowns:
                    table_context = "\n\n### Extracted Structured Table Structure:\n" + "\n\n".join(table_markdowns)
                    text = f"{text}\n{table_context}".strip()
            except Exception as te:
                print(f"Failed to extract table on page {page_num+1}: {te}")
            
            # Check for scanned page placeholders if no text is found
            if not text:
                images = page.get_images()
                drawings = page.get_drawings()
                if images or drawings:
                    text = f"[Scanned Visual Page - Containing {len(images)} images and visual drawings]"

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
