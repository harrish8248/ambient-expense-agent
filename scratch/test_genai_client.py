import os
from dotenv import load_dotenv
load_dotenv()

from google.genai import Client

print("Initializing Client...")
client = Client()

for model_name in ["gemini-3.1-flash-lite", "gemini-2.5-flash"]:
    print(f"\nCalling generate_content with model {model_name}...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say hello!",
        )
        print(f"Success for {model_name}! Response text:", response.text)
    except Exception as e:
        print(f"Failed for {model_name}! Error: {type(e)} {e}")
