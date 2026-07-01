import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print("API KEY:", api_key)

try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        google_api_key=api_key
    )
    res = llm.invoke("Hola, cómo estás?")
    print("Response:", res)
except Exception as e:
    print("Error with gemini-3.5-flash-lite:", e)

try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=api_key
    )
    res = llm.invoke("Hola, cómo estás?")
    print("Response with gemini-1.5-flash:", res)
except Exception as e:
    print("Error with gemini-1.5-flash:", e)
