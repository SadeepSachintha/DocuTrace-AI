from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import init_db
from app.routes import documents, chat

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
