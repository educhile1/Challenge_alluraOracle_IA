import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("No se encontró GOOGLE_API_KEY ni GEMINI_API_KEY en .env")
    exit(1)

url = f'https://generativelanguage.googleapis.com/v1beta/models?key={api_key}'
response = requests.get(url)
if response.status_code != 200:
    print(f"Error HTTP {response.status_code}: {response.text}")
    exit(1)

models = response.json().get('models', [])
print("Modelos disponibles:")
for m in models:
    methods = m.get('supportedGenerationMethods', [])
    if 'generateContent' in methods:
        print(f"- Nombre: {m.get('name')}")
        print(f"  Descripción: {m.get('description')}")
        print()
