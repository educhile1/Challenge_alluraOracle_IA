import os
from dotenv import load_dotenv
from rag_engine import query_rag

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

vector_db_dir = os.path.abspath("./vector_db")

result = query_rag(
    user_query="¿Cuáles son las políticas de vacaciones de la empresa?",
    vector_db_dir=vector_db_dir,
    gemini_api_key=api_key,
    model_name="gemini-2.5-flash"
)

print(f"Respuesta del modelo:\n{result.get('answer')}")
