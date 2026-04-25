import os, json, time, datetime, urllib.parse
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def load_data():
    if os.path.exists('data.json'):
        with open('data.json', 'r') as f:
            content = f.read()
            return json.loads(content) if content else {}
    return {"last_updated": {}, "page8_timeline": [], "sections": {}}

def get_gemini_news(prompt):
    """Safety-wrapped Gemini call with Search Grounding."""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        )
        time.sleep(20) # Respecting the 2026 RPM limits
        return response.text
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    data = load_data()
    now = datetime.datetime.now()
    updated = False

    # Logic for Scheduling
    def needs_update(key, hours):
        last = data.get("last_updated", {}).get(key)
        return not last or (now - datetime.datetime.fromisoformat(last)).total_seconds() >= hours*3600

    # 1. Page 2, 3, 8 (Hourly)
    if needs_update("hourly_core", 1):
        data["sections"]["markets"] = get_gemini_news("Top 10 Indian & World Market news with 1-para summaries.")
        # ... fetch other hourly sections ...
        data["last_updated"]["hourly_core"] = now.isoformat()
        updated = True

    # 2. Page 4 (Daily - Undervalued Gems)
    if needs_update("daily_gems", 24):
        data["sections"]["gems"] = get_gemini_news("Identify 5 undervalued Indian stocks based on P/E and recent filings. 1-para each.")
        data["last_updated"]["daily_gems"] = now.isoformat()
        updated = True

    # 3. Hybrid Pages (Top 5 Hourly / Bottom 10 every 4h)
    if needs_update("news_top", 1):
        data["sections"]["news_top"] = get_gemini_news("Top 5 World, Indian, and Misc news. Summarize.")
        data["last_updated"]["news_top"] = now.isoformat()
        updated = True

    if updated:
        with open('data.json', 'w') as f: json.dump(data, f)
        generate_html_pages(data)

def generate_html_pages(data):
    # This function will iterate 8 times to create index.html, gems.html, etc.
    # Use: f"https://www.google.com/search?q={urllib.parse.quote(headline)}" for search links.
    pass

if __name__ == "__main__":
    main()
