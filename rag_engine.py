import os
import shutil
from typing import List, Dict, Any, Tuple
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Supported document extensions and their loaders
LOADERS: Dict[str, Any] = {
    ".pdf": PyPDFLoader,
    ".txt": lambda path: TextLoader(path, encoding="utf-8"),
    ".docx": Docx2txtLoader
}

def load_documents_from_dir(directory: str) -> List[Any]:
    """Loads all supported documents from the specified directory."""
    documents = []
    if not os.path.exists(directory):
        return []

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isdir(filepath):
            continue

        ext = os.path.splitext(filename)[1].lower()
        if ext in LOADERS:
            try:
                loader_class = LOADERS[ext]
                loader = loader_class(filepath)
                loaded_docs = loader.load()
                # Store original filename in metadata for UI sourcing
                for doc in loaded_docs:
                    doc.metadata["source_file"] = filename
                documents.extend(loaded_docs)
                print(f"Loaded {filename} successfully.")
            except Exception as e:
                print(f"Error loading file {filename}: {str(e)}")
    return documents

def ingest_documents(docs_dir: str, vector_db_dir: str, gemini_api_key: str) -> Dict[str, Any]:
    """
    Loads, splits documents from docs_dir and creates/replaces Chroma vector store.
    """
    if not gemini_api_key:
        raise ValueError("Se requiere una Gemini API Key para generar los embeddings.")

    # 1. Load documents
    documents = load_documents_from_dir(docs_dir)
    if not documents:
        return {"status": "error", "message": "No se encontraron documentos válidos para procesar."}

    # 2. Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Documents split into {len(chunks)} chunks.")

    # 3. Re-create Vector Database (Clean existing first)
    if os.path.exists(vector_db_dir):
        try:
            # Chroma keeps open handles sometimes; we force database cleanup
            shutil.rmtree(vector_db_dir)
            print("Cleaned existing vector database.")
        except Exception as e:
            print(f"Warning cleaning vector_db directory: {e}")

    # 4. Generate embeddings and populate vector db
    embeddings = GoogleGenerativeAIEmbeddings(  # type: ignore
        model="models/text-embedding-004",
        google_api_key=gemini_api_key  # type: ignore
    )
    
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=vector_db_dir
    )
    
    # Chroma auto-persists in newer versions; persist() is deprecated/removed
    try:
        vector_store.persist()
    except AttributeError:
        pass

    return {
        "status": "success",
        "chunks_count": len(chunks),
        "documents_count": len(set(doc.metadata.get("source_file", "") for doc in documents))
    }

def query_rag(
    user_query: str,
    vector_db_dir: str,
    gemini_api_key: str,
    model_name: str = "gemini-1.5-flash"
) -> Dict[str, Any]:
    """
    Loads Vector DB, retrieves context, sends context and query to Gemini, and returns response with sources.
    """
    if not gemini_api_key:
        return {
            "answer": "Error: Se requiere una Gemini API Key para contestar consultas.",
            "sources": []
        }

    if not os.path.exists(vector_db_dir) or not os.listdir(vector_db_dir):
        return {
            "answer": "La base de conocimientos está vacía. Por favor, sube archivos primero para responder con propiedad.",
            "sources": []
        }

    try:
        # Load Vector Store
        embeddings = GoogleGenerativeAIEmbeddings(  # type: ignore
            model="models/text-embedding-004",
            google_api_key=gemini_api_key  # type: ignore
        )
        vector_store = Chroma(
            persist_directory=vector_db_dir,
            embedding_function=embeddings
        )

        # Set up LLM & QA Chain
        llm = ChatGoogleGenerativeAI(  # type: ignore
            model=model_name,
            google_api_key=gemini_api_key,  # type: ignore
            temperature=0.2
        )

        # Create Retriever
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4} # Retrieve top 4 relevant chunks
        )

        # RAG Prompt Template in Spanish to match user requirements
        system_prompt = (
            "Eres un asistente virtual de soporte inteligente especializado. "
            "Responde a la pregunta del usuario utilizando únicamente el contexto proporcionado a continuación. "
            "Si en el contexto no se encuentra la información para responder la pregunta de forma precisa y veraz, "
            "responde exactamente: 'No tengo información suficiente en los documentos cargados para responder a esa pregunta.' "
            "No asumas, no extrapoles y no uses información externa que no esté respaldada en el contexto.\n\n"
            "Contexto de los documentos:\n"
            "{context}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])

        # Combine docs chain & retrieval chain
        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)

        # Run pipeline
        response = rag_chain.invoke({"input": user_query})
        
        # Format sources
        sources = []
        context_docs = response.get("context", [])
        seen_chunks = set()
        
        for doc in context_docs:
            src_file = doc.metadata.get("source_file", "Desconocido")
            # Create a unique key for the chunk/source to avoid listing duplicates
            snippet = doc.page_content[:150].strip() + "..."
            chunk_key = (src_file, snippet)
            
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                sources.append({
                    "file": src_file,
                    "snippet": doc.page_content,
                    "page": doc.metadata.get("page", 1)
                })

        return {
            "answer": response["answer"],
            "sources": sources
        }

    except Exception as e:
        print(f"Error querying RAG: {e}")
        return {
            "answer": f"Error al procesar la respuesta con LangChain: {str(e)}",
            "sources": []
        }
