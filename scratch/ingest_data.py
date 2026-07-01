import os
from dotenv import load_dotenv
from rag_engine import ingest_documents

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("API KEY not found")
    exit(1)

data_dir = os.path.abspath("./data")
vector_db_dir = os.path.abspath("./vector_db")

print("Iniciando ingesta de documentos...")
result = ingest_documents(data_dir, vector_db_dir, api_key)
print(f"Resultado de la ingesta: {result}")
