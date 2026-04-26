import os
import json
import time
import datetime
import urllib.parse
import re
import random
from google import genai
from google.genai import types

# 1. SETUP & CLIENT
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def load_data():
    """Initializes or loads the stateful data.json database."""
    default_structure = {
        "last_updated": {},
        "page8_timeline": [],
        "page8_topic": "Global Geopolitics",
        "sections": {
            "all_news": "",
            "gems": ""
        }
    }
    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r') as f:
                data = json.load(f)
                for key, val in default_structure.items():
                    if key not in data: 
                        data[key] = val
                return data
        except: 
            return default_structure
    return default_structure

def get_gemini_news(prompt, max_retries=5):
    """Fetch with exponential backoff and non-grounded fallback."""
    model_id = "gemini-3.1-flash-lite-preview"
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}...")
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            return response.text
        except Exception as e:
            err_msg = str(e).upper()
            if "503" in err_msg or "UNAVAILABLE" in err_msg or "429" in err_msg:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                print(f"Permanent Error: {e}")
                break

    print("Attempting final non-grounded fallback...")
    try:
        fallback = client.models.generate_content(
            model=model_id,
            contents=prompt + " (Search unavailable, use internal knowledge)"
        )
        return fallback.text
    except:
        return None

def clean_text(text):
    """Strips Markdown artifacts."""
    if not text: return ""
    text = re.sub(r'[*#]', '', text)
    return text.replace("```html", "").replace("```", "").strip()

def extract_section(full_text, tag):
    """Regex extraction to handle bolding or spacing in AI tags."""
    if not full_text: return ""
    pattern = rf"(?:\*\*|)\s*\[\[\s*{tag}\s*\]\]\s*(?:\*\*|)"
    match = re.search(pattern, full_text, re.IGNORECASE)
    if not match: return ""
    start_idx = match.end()
    next_tag = full_text.find("[[", start_idx)
    content = full_text[start_idx:] if next_tag == -1 else full_text[start_idx:next_tag]
    return clean_text(content)

def should_upd(current_data, key, hrs):
    """Timestamp checker."""
    last = current_data.get("last_updated", {}).get(key)
    if not last: return True
    try:
        last_time = datetime.datetime.fromisoformat(last)
        return (datetime.datetime.now() - last_time).total_seconds() >= hrs * 3600
    except: return True

def generate_pages(data):
    """Generates 8 static HTML files with robust formatting."""
    pages = {
        "index": "Front Page", "markets": "Share Market", "business": "Trade & Tech",
        "gems": "Undervalued Gems", "world": "World News", "india": "Indian News",
        "misc": "Miscellaneous", "live": "Live Tracker"
    }
    tag_map = {
        "markets": "MARKETS", "business": "TRADE_TECH", "world": "WORLD", 
        "india": "INDIA", "misc": "MISC", "gems": "GEMS"
    }

    nav = "<nav>" + " | ".join([f'<a href="{s}.html">{t}</a>' for s, t in pages.items()]) + "</nav>"
    all_content = data["sections"].get("all_news", "")

    for slug, title in pages.items():
        html_body = ""
        
        if slug == "index":
            # --- INDEX LOGIC: Find lines starting with * ---
            html_body = "<ul>"
            news_block = all_content.split("[[GEMS]]")[0] if "[[GEMS]]" in all_content else all_content
            lines = [l.strip() for l in news_block.split('\n') if l.strip()]
            headlines = []
            for line in lines:
                if line.startswith('*'):
                    clean_h = line.lstrip('*').strip()
                    if 25 < len(clean_h) < 250:
                        headlines.append(clean_h)
            
            for h in list(dict.fromkeys(headlines))[:15]:
                html_body += f"<li>{h}</li>"
            html_body += "</ul>"

        elif slug == "live":
            html_body = f"<h2>Topic: {data.get('page8_topic')}</h2>"
            for item in data.get("page8_timeline", []):
                html_body += f"<div class='update'><strong>{item['time']}</strong>: {item['text']}</div><hr>"

        else:
            # --- SECTION LOGIC: Split by Asterisk (*) ---
            tag = tag_map.get(slug)
            content = extract_section(all_content, tag)
            
            # Split by asterisk to catch every bullet point as a new block
            blocks = content.split('*')
            
            for b in blocks:
                clean_b = b.strip()
                if len(clean_b) > 40:
                    search_query = urllib.parse.quote(clean_b[:60])
                    search_url = f"https://www.google.com/search?q={search_query}"
                    
                    html_body += f"""
                    <div class='news-block'>
                        <p>{clean_b}</p>
                        <a href='{search_url}' target='_blank' style='font-size:0.8em;'>Verify ↗</a>
                    </div><hr>"""

        full_html = f"""<!DOCTYPE html><html><head><link rel="stylesheet" href="style.css">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head><body><div class="paper"><header><h1>THE HOURLY JOURNAL</h1>{nav}</header><hr>
            <main><h2>{title}</h2>{html_body}</main>
            <footer>Updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</footer>
            </div></body></html>"""
        
        with open(f"{slug}.html", "w", encoding="utf-8") as f:
            f.write(full_html)

def main():
    data = load_data()
    now = datetime.datetime.now()

    if should_upd(data, "global_sync", 1):
        print("Starting Global Sync...")
        has_no_gems = not data["sections"].get("gems") or "Researching" in data["sections"].get("gems")
        include_gems = "Also include [[GEMS]] section with 5 undervalued Indian stocks." if (should_upd(data, "daily_gems", 24) or has_no_gems) else ""
        
        prompt = f"""
        Search and provide news for these sections. 
        Wrap each section in [[TAGS]].
        
        [[MARKETS]], [[TRADE_TECH]], [[WORLD]], [[INDIA]], [[MISC]], [[LIVE]] (1-sentence on {data['page8_topic']}).
        {include_gems}
        
        STRICT FORMATTING RULES:
        1. Every news story MUST be its own paragraph.
        2. Use a DOUBLE NEWLINE between every story.
        3. Start every story with a bullet point (*).
        4. NO markdown symbols like **bolding** or # headers.
        5. Use only plain text summaries.
        
        Example format:
        [[INDIA]]
        * First news story summary goes here.
        
        * Second news story summary goes here.
        """

        res = get_gemini_news(prompt)
        if res:
            data["sections"]["all_news"] = res
            if "[[GEMS]]" in res:
                data["sections"]["gems"] = extract_section(res, "GEMS")
                data["last_updated"]["daily_gems"] = now.isoformat()
            
            live_update = extract_section(res, "LIVE")
            if "NEW_TOPIC:" in live_update:
                data["page8_topic"] = live_update.split("NEW_TOPIC:")[1].split('\n')[0].strip()
                data["page8_timeline"] = [{"time": now.strftime("%H:%M"), "text": clean_text(live_update)}]
            elif live_update:
                data["page8_timeline"].insert(0, {"time": now.strftime("%H:%M"), "text": clean_text(live_update)})
            
            data["page8_timeline"] = data["page8_timeline"][:24]
            data["last_updated"]["global_sync"] = now.isoformat()
            with open('data.json', 'w') as f:
                json.dump(data, f, indent=4)
    
    generate_pages(data)

if __name__ == "__main__":
    main()
