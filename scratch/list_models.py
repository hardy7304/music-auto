import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found in .env")
    exit(1)

client = genai.Client(api_key=api_key)

print("Checking available Gemini models...")
try:
    for model in client.models.list():
        print(f" - {model.name} (Methods: {model.supported_methods})")
except Exception as e:
    print(f"Error listing models: {e}")
