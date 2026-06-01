import sys
import os
import asyncio

# Add the parent directory to the path so we can import server modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.services import translate_google_with_api

async def main():

    text = "Hello, world!"
    src_lang = "English"
    tgt_lang = "Czech"
    
    print(f"Translating: '{text}' from {src_lang} to {tgt_lang} using API key...")
    try:
        result = await translate_google_with_api(text, src_lang, tgt_lang)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
