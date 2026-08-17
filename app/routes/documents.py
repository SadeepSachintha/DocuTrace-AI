from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Document, DocumentChunk, DocumentParentChunk
from app.services.document_parser import DocumentParserService
from app.services.embedding_service import embedding_service
from app.schemas import DocumentUploadResponse

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    department: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are currently supported.")

    file_bytes = await file.read()
    pages_content, detected_lang, total_pages = DocumentParserService.extract_text_with_pages(file_bytes)
    
    if not pages_content:
        raise HTTPException(status_code=400, detail="No extractable text found in PDF.")

    # 1. Create Document Record
    doc_record = Document(
        filename=file.filename,
        content_type=file.content_type or "application/pdf",
        department=department,
        language=detected_lang,
        total_pages=total_pages
    )
    db.add(doc_record)
    await db.flush()

    # 2. Store Parent Chunks (Full Pages)
    parent_chunk_objects = []
    parent_map = {} # Maps page_number to parent_chunk_id
    for idx, page_data in enumerate(pages_content):
        parent_obj = DocumentParentChunk(
            document_id=doc_record.id,
            chunk_index=idx,
            content=page_data["text"],
            page_number=page_data["page"]
        )
        parent_chunk_objects.append(parent_obj)
        db.add(parent_obj)
    
    await db.flush() # Flushes parent chunks to assign auto-generated UUIDs

    # Build mapping from page_number to parent chunk ID
    for parent_obj in parent_chunk_objects:
        parent_map[parent_obj.page_number] = parent_obj.id

    # 3. Chunk Text to Children & Embed
    child_chunks = DocumentParserService.chunk_text(pages_content, chunk_size=150, chunk_overlap=30)
    raw_texts = [c["content"] for c in child_chunks]
    embeddings = embedding_service.generate_passage_embeddings(raw_texts)

    chunk_objects = []
    for idx, (chunk_data, vector) in enumerate(zip(child_chunks, embeddings)):
        page_num = chunk_data["page"]
        parent_id = parent_map.get(page_num)
        
        chunk_obj = DocumentChunk(
            document_id=doc_record.id,
            parent_chunk_id=parent_id,
            chunk_index=idx,
            content=chunk_data["content"],
            page_number=page_num,
            embedding=vector
        )
        chunk_objects.append(chunk_obj)

    db.add_all(chunk_objects)
    await db.commit()

    return DocumentUploadResponse(
        document_id=doc_record.id,
        filename=doc_record.filename,
        chunks_indexed=len(chunk_objects),
        detected_language=detected_lang
    )
