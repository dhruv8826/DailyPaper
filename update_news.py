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
    default_structure = {
        "last_updated": {},
        "page8_timeline": [],
        "page8_topic": "Security Incident at White House Correspondents Dinner",
        "sections": {}
    }
    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r') as f:
                data = json.load(f)
                return data
        except: 
            return default_structure
    return default_structure

def get_gemini_news(prompt, max_retries=5):
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
            # Robust JSON extraction
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print(f"Retry {attempt+1}: {e}")
            time.sleep(2 ** attempt)
    return None

def generate_pages(data):
    pages = {
        "index": "Front Page", "markets": "Share Market", "business": "Trade & Tech",
        "gems": "Undervalued Gems", "world": "World News", "india": "Indian News",
        "misc": "Miscellaneous", "live": "Live Tracker"
    }
    key_map = {
        "markets": "MARKETS", "business": "TRADE_TECH", "world": "WORLD", 
        "india": "INDIA", "misc": "MISC", "gems": "GEMS"
    }

    nav = "<nav>" + " | ".join([f'<a href="{s}.html">{t}</a>' for s, t in pages.items()]) + "</nav>"
    sections = data.get("sections", {})

    for slug, title in pages.items():
        html_body = ""
        
        if slug == "index":
            headlines = []
            for k in ["MARKETS", "WORLD", "INDIA", "TRADE_TECH"]:
                cat_list = sections.get(k, [])
                if cat_list and isinstance(cat_list, list):
                    headlines.append(cat_list[0])
            html_body = "<ul>" + "".join([f"<li>{h}</li>" for h in headlines]) + "</ul>"

        elif slug == "live":
            html_body = f"<h2>Topic: {data.get('page8_topic')}</h2>"
            for item in data.get('page8_timeline', []):
                html_body += f"<div class='update'><strong>{item['time']}</strong>: {item['text']}</div><hr>"

        else:
            items = sections.get(key_map.get(slug), [])
            if not items:
                html_body = "<p>Updating research... check back in a moment.</p>"
            else:
                for item in items:
                    search_url = f"https://www.google.com/search?q={urllib.parse.quote(item[:80])}"
                    html_body += f"<div class='news-block'><p>{item}</p><a href='{search_url}' target='_blank'>Verify ↗</a></div><hr>"

        full_html = f"""<!DOCTYPE html><html><head><link rel="stylesheet" href="style.css">
            <meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
            <body><div class="paper"><header><h1>THE HOURLY JOURNAL</h1>{nav}</header><hr>
            <main><h2>{title}</h2>{html_body}</main>
            <footer>Updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</footer>
            </div></body></html>"""
        
        with open(f"{slug}.html", "w", encoding="utf-8") as f:
            f.write(full_html)

def main():
    data = load_data()
    now = datetime.datetime.now()

    if should_upd(data, "global_sync", 1):
        # DETAILED GEMS LOGIC: Check for 24h update or empty section
        has_no_gems = not data.get("sections", {}).get("GEMS")
        include_gems_instruction = ""
        if (should_upd(data, "daily_gems", 24) or has_no_gems):
            include_gems_instruction = """
            [[GEMS]]: Perform deep qualitative research for 5 Indian stocks. 
            CRITERIA: Focus on hidden companies or companies that are in news or have something great happening suddenly. 
            Prioritize low P/E stocks benefiting from the recent policies of the government
            and 'Make in India' PLI schemes. Provide 1-sentence logic per stock. No disclaimers.
            """

        mega_prompt = f"""
        Return a JSON dictionary for these categories. Search for latest 2026 data.
        
        [[MARKETS]]: Top 10 World/India market shifts (Sensex, Nifty, US Tech earnings).
        [[TRADE_TECH]]: Top 10 Tech news (AI regulation, Nvidia/Microsoft shifts, global supply chains).
        [[WORLD]]: Top 10 Geopolitics (Middle East, US Elections, Energy transit).
        [[INDIA]]: Top 10 domestic policy or infrastructure updates.
        [[MISC]]: Top 10 Sports (IPL/T20) or Entertainment stories.
        [[LIVE_UPDATE]]: 1-sentence summary of: {data['page8_topic']}.
        [[NEW_TOPIC]]: Only provide if a new massive topic has emerged.
        {include_gems_instruction}

        JSON OUTPUT FORMAT:
        {{
            "MARKETS": ["story1", "story2", ...],
            "TRADE_TECH": ["story1", "story2", ...],
            "WORLD": ["story1", "story2", ...],
            "INDIA": ["story1", "story2", ...],
            "MISC": ["story1", "story2", ...],
            "LIVE_UPDATE": "text",
            "NEW_TOPIC": "text or null",
            "GEMS": ["stock1", "stock2", ...]
        }}
        """

        news_json = get_gemini_news(mega_prompt)
        if news_json:
            # We preserve the old GEMS if the new response doesn't include them
            if not news_json.get("GEMS"):
                news_json["GEMS"] = data.get("sections", {}).get("GEMS", [])
            else:
                data["last_updated"]["daily_gems"] = now.isoformat()

            data["sections"] = news_json
            
            # Handle Live Tracker Timeline
            live_text = news_json.get("LIVE_UPDATE", "")
            if news_json.get("NEW_TOPIC"):
                data["page8_topic"] = news_json["NEW_TOPIC"]
                data["page8_timeline"] = [{"time": now.strftime("%H:%M"), "text": live_text}]
            else:
                data["page8_timeline"].insert(0, {"time": now.strftime("%H:%M"), "text": live_text})
            
            data["page8_timeline"] = data["page8_timeline"][:24]
            data["last_updated"]["global_sync"] = now.isoformat()
            
            with open('data.json', 'w') as f:
                json.dump(data, f, indent=4)
    
    generate_pages(data)

def should_upd(data, key, hrs):
    last = data.get("last_updated", {}).get(key)
    if not last: return True
    return (datetime.datetime.now() - datetime.datetime.fromisoformat(last)).total_seconds() >= hrs * 3600

if __name__ == "__main__":
    main()
