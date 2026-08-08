import asyncio
import os
import dotenv

dotenv.load_dotenv()

from backend.src.ai.provider_pool import ai_engine

async def main():
    print("=== Testing Groq AI Key Pool (Llama 3.3 70B) ===")
    groq_key = os.getenv("GROQ_API_KEY_1")
    try:
        res = await ai_engine._call_groq(groq_key, "Hello! Confirm in 1 short sentence that Helios AI Employee engine is ready.", "")
        print(f"Groq AI Response Success:\n{res}\n")
    except Exception as e:
        print(f"Groq Error: {e}\n")

    print("=== Testing Tavily Search Key Pool (4,000 Free Searches) ===")
    try:
        search_res = await ai_engine.search_web("Software Developer jobs Copenhagen Denmark")
        print(f"Tavily Search Success: Found {len(search_res.get('results', []))} search results.")
        if search_res.get("results"):
            print(f"Sample Job Title: {search_res['results'][0].get('title')}")
            print(f"Sample URL: {search_res['results'][0].get('url')}")
    except Exception as e:
        print(f"Tavily Search Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
