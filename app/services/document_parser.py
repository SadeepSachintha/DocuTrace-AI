import fitz  # PyMuPDF
import base64
from langdetect import detect
from typing import List, Dict, Any, Tuple
from openai import AsyncOpenAI
from app.config import settings

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

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
    async def extract_text_with_pages(pdf_bytes: bytes) -> Tuple[List[Dict[str, Any]], str, int]:
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
            
            # Vision analysis for pages containing drawings or images (or completely empty of text)
            images = page.get_images()
            drawings = page.get_drawings()
            is_mock_key = not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("mock")
            
            if (images or drawings or not text) and not is_mock_key:
                try:
                    print(f"Rendering visual contents of page {page_num+1} for Vision analysis...")
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    base64_image = base64.b64encode(img_bytes).decode('utf-8')
                    
                    sys_prompt = (
                        "Describe any charts, diagrams, drawings, flowcharts, or visual graphics on this page in detail. "
                        "Focus on corporate details, labels, figures, and relationships so it is searchable. "
                        "If there are no drawings or charts, return an empty string."
                    )
                    
                    response = await openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": sys_prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=500
                    )
                    visual_desc = response.choices[0].message.content.strip()
                    if visual_desc:
                        text = f"{text}\n\n### Extracted Visual Content Description:\n{visual_desc}".strip()
                        print(f"Page {page_num+1} visual analysis completed successfully.")
                except Exception as ve:
                    print(f"Failed vision analysis on page {page_num+1}: {ve}")
            
            # Check for scanned page placeholders if no text is found
            if not text:
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
