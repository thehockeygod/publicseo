# pip install -U google-genai
import sys
import argparse
from google import genai
from google.genai import types

# --- CONFIGURATION ---
GEMINI_API_KEY = "YOUR KEY HERE"
MODEL_ID = "gemini-flash-latest" # or "gemini-pro-latest" but more $$

def get_grounded_queries(keyword):
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Define the search tool
    google_search_tool = types.Tool(
        google_search=types.GoogleSearch()
    )

    print(f"[*] Fanning out queries for: '{keyword}'...")

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=f"Research the following and give me a brief summary: {keyword}",
        config=types.GenerateContentConfig(
            tools=[google_search_tool]
        )
    )

    metadata = response.candidates[0].grounding_metadata

    # 1. Spitting out the "Fanout" Queries
    print("\n## GOOGLE SEARCH FANOUT QUERIES")
    if metadata.web_search_queries:
        for i, q in enumerate(metadata.web_search_queries, 1):
            print(f"{i}. {q}")
    else:
        print("No search queries were generated.")

    # 2. Spitting out the Citations/Sources
    print("\n## CITED SOURCES")
    if metadata.grounding_chunks:
        for i, chunk in enumerate(metadata.grounding_chunks, 1):
            title = chunk.web.title if chunk.web else "Unknown Title"
            uri = chunk.web.uri if chunk.web else "No URI"
            print(f"[{i}] {title}")
            #print(f"    URL: {uri}")
    else:
        print("No citations returned.")

    #uncomment below if you want to see the actual model response
    #print("\n## MODEL RESPONSE SUMMARY")
    #print(response.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Gemini Search Grounding Metadata")
    parser.add_argument("keyword", help="The topic or keyword to research")
    
    args = parser.parse_args()
    
    try:
        get_grounded_queries(args.keyword)
    except Exception as e:
        print(f"Error: {e}")