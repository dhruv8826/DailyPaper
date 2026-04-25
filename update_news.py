import os, json, time, datetime, urllib.parse
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
def load_data():
    default_structure = {
        "last_updated": {},
        "page8_timeline": [],
        "page8_topic": "Global Geopolitics",
        "sections": {
            "markets": "", "business": "", "gems": "", 
            "news_top": "", "news_bottom": "", "misc": ""
        }
    }
    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r') as f:
                content = f.read()
                if not content: return default_structure
                data = json.loads(content)
                # Merge with default to ensure 'sections' key exists
                for key in default_structure:
                    if key not in data: data[key] = default_structure[key]
                return data
        except Exception:
            return default_structure
    return default_structure

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
    # Mapping for your 8 pages
    pages = {
        "index": "Front Page", "markets": "Share Market", "business": "Trade & Tech",
        "gems": "Undervalued Gems", "world": "World News", "india": "Indian News",
        "misc": "Miscellaneous", "live": "Live Tracker"
    }

    nav_html = "<nav>" + " | ".join([f'<a href="{s}.html">{t}</a>' for s, t in pages.items()]) + "</nav>"

    for slug, title in pages.items():
        content = ""
        
        if slug == "index":
            # Page 1: Only Headlines from various sections
            content = "<ul>"
            for section in ["markets", "news_top"]:
                # Simple extraction of headlines (assuming Gemini uses '##' or '1.')
                headlines = [line for line in data["sections"].get(section, "").split('\n') if line.strip() and (line[0].isdigit() or line.startswith('#'))]
                for h in headlines[:5]:
                    clean_h = h.lstrip('0123456789. #').strip()
                    content += f"<li>{clean_h}</li>"
            content += "</ul>"
            
        elif slug == "live":
            # Page 8: Timeline
            content = f"<h2>Topic: {data.get('page8_topic')}</h2>"
            for entry in data.get("page8_timeline", []):
                content += f"<div class='update'><strong>{entry['time']}</strong>: {entry['text']}</div><hr>"
        
        else:
            # Pages 2-7: Paragraphs + Search Links
            raw_text = data["sections"].get(slug, "Fetching updates...")
            # We add the search link logic here
            paragraphs = raw_text.split('\n\n')
            for p in paragraphs:
                if p.strip():
                    headline = p.split('\n')[0].lstrip('0123456789. #')
                    search_url = f"https://www.google.com/search?q={urllib.parse.quote(headline)}"
                    content += f"<div class='news-block'>{p} <br><a href='{search_url}' target='_blank'>Read more on Google ↗</a></div><hr>"

        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head><link rel="stylesheet" href="style.css"><title>{title}</title></head>
        <body>
            <div class="paper">
                <header><h1>THE HOURLY JOURNAL</h1>{nav_html}</header>
                <hr>
                <main><h2>{title}</h2>{content}</main>
            </div>
        </body>
        </html>
        """
        with open(f"{slug}.html", "w", encoding="utf-8") as f:
            f.write(full_html)

if __name__ == "__main__":
    main()
