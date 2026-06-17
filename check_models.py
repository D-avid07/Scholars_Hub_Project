import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("Checking available models for your API key...")
for model in genai.list_models():
    if 'embedContent' in model.supported_generation_methods:
        print(f"✅ Found Embedding Model: {model.name}")
    if 'generateContent' in model.supported_generation_methods:
        print(f"✅ Found Generation Model: {model.name}")