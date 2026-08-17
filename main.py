from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import init_db
from app.routes import documents, chat

from fastapi.responses import HTMLResponse
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="Multilingual Enterprise RAG Assistant",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(documents.router)
app.include_router(chat.router)

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = os.path.join(os.path.dirname(__file__), "app", "templates", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8008, reload=True)
