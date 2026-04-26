import os
from google import genai

# Use the same key your action uses
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("--- AVAILABLE MODELS AND QUOTAS ---")
try:
    for m in client.models.list():
        # We only care about models that can generate news
        if "generateContent" in m.supported_actions:
            # Check for the 3.1 Lite model specifically
            is_lite = "lite" in m.name.lower()
            star = " ⭐ (TARGET)" if is_lite else ""
            print(f"ID: {m.name} | Display: {m.display_name}{star}")
except Exception as e:
    print(f"Error listing models: {e}")
