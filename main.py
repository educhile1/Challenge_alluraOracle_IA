import os
import shutil
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from rag_engine import ingest_documents, query_rag

# Load environment variables (.env file)
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando servidor y verificando documentos...")
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            print("Ejecutando ingesta automática de documentos...")
            result = ingest_documents(DATA_DIR, VECTOR_DB_DIR, api_key)
            print(f"Ingesta finalizada: {result}")
        except Exception as e:
            print(f"Error durante la ingesta automática: {e}")
    else:
        print("No se encontró GEMINI_API_KEY en las variables de entorno. Omitiendo ingesta automática.")
    yield

app = FastAPI(
    title="DocuMind Chat RAG API",
    description="Backend API for document-based RAG application",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local testing and development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
DATA_DIR = os.path.abspath("./data")
VECTOR_DB_DIR = os.path.abspath("./vector_db")
STATIC_DIR = os.path.abspath("./static")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(VECTOR_DB_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

class QueryPayload(BaseModel):
    message: str
    model_name: Optional[str] = "gemini-2.5-flash"

def get_api_key(x_gemini_key: Optional[str] = Header(None)) -> str:
    """Helper to resolve Gemini API Key from header or environment variables."""
    api_key = x_gemini_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Falta la clave API de Gemini. Proporciónala en la interfaz o configúrala en el servidor."
        )
    return api_key

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Uploads files to the data directory."""
    uploaded_files = []
    failed_files = []

    for file in files:
        # Validate file extension
        filename = file.filename or "unknown"
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".txt", ".docx"]:
            failed_files.append({"name": filename, "reason": "Extensión de archivo no soportada."})
            continue

        try:
            file_path = os.path.join(DATA_DIR, filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_files.append(filename)
        except Exception as e:
            failed_files.append({"name": filename, "reason": str(e)})

    return {
        "uploaded": uploaded_files,
        "failed": failed_files,
        "total_uploaded": len(uploaded_files)
    }

@app.post("/api/ingest")
async def ingest_database(api_key: str = Header(None, alias="x-gemini-key")):
    """Triggers the LangChain pipeline to read, split, embed, and store uploaded documents."""
    # Resolve API Key
    resolved_key = api_key or os.getenv("GEMINI_API_KEY")
    if not resolved_key:
        raise HTTPException(status_code=401, detail="Clave de API de Gemini requerida para la ingesta.")

    try:
        result = ingest_documents(DATA_DIR, VECTOR_DB_DIR, resolved_key)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la ingesta: {str(e)}")

@app.post("/api/chat")
async def chat_query(
    payload: QueryPayload,
    api_key: str = Header(None, alias="x-gemini-key")
):
    """Answers user query by performing semantic retrieval against the document database."""
    resolved_key = api_key or os.getenv("GEMINI_API_KEY")
    if not resolved_key:
        raise HTTPException(status_code=401, detail="Clave de API de Gemini requerida para chatear.")

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    model_name = payload.model_name or "gemini-2.5-flash"
    result = query_rag(
        user_query=payload.message,
        vector_db_dir=VECTOR_DB_DIR,
        gemini_api_key=resolved_key,
        model_name=model_name
    )
    return result

@app.get("/api/config")
async def get_config():
    """Returns application configuration, such as APP_ENV."""
    return {
        "app_env": os.getenv("APP_ENV", "production").lower().strip()
    }

@app.get("/api/files")
async def list_files():
    """Lists all files uploaded in the data directory."""
    try:
        files = []
        for filename in os.listdir(DATA_DIR):
            filepath = os.path.join(DATA_DIR, filename)
            if os.path.isfile(filepath):
                stat_info = os.stat(filepath)
                files.append({
                    "name": filename,
                    "size": stat_info.st_size,
                    "ext": os.path.splitext(filename)[1].lower()
                })
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar archivos: {str(e)}")

@app.post("/api/clear")
async def clear_database():
    """Erases all files in upload directory and destroys vector index."""
    try:
        # Clear uploads folder
        for filename in os.listdir(DATA_DIR):
            filepath = os.path.join(DATA_DIR, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
            elif os.path.isdir(filepath):
                shutil.rmtree(filepath)
        
        # Clear vector database folder
        if os.path.exists(VECTOR_DB_DIR):
            shutil.rmtree(VECTOR_DB_DIR)
            os.makedirs(VECTOR_DB_DIR, exist_ok=True)

        return {"status": "success", "message": "Base de conocimientos y archivos eliminados."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al limpiar la base: {str(e)}")

# Mount static files directory (for stylesheet & app.js)
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="static")

# Serve index.html at root
@app.get("/")
async def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        status_code=404,
        content={"error": "Falta index.html en el directorio static."}
    )

if __name__ == "__main__":
    import uvicorn
    # Start server locally on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
