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
            "finance_tech": "", 
            "general_news": "", 
            "gems": "",
            "all_news": ""
        }
    }
    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r') as f:
                data = json.load(f)
                # Ensure all keys exist to prevent KeyErrors
                for key, val in default_structure.items():
                    if key not in data: 
                        data[key] = val
                return data
        except: 
            return default_structure
    return default_structure

def get_gemini_news(prompt, max_retries=5):
    """
    Fetch with exponential backoff (capped at 5 retries).
    Falls back to a non-search request as a final attempt.
    """
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
            
            # If it's a 503 (Server Busy) or 429 (Rate Limit), we wait and retry
            if "503" in err_msg or "UNAVAILABLE" in err_msg or "429" in err_msg:
                # Exponential backoff: 2, 4, 8, 16, 32 seconds + jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Server busy/Throttled. Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                # If it's a different error (like a 400 Bad Request), stop immediately
                print(f"Permanent Error encountered: {e}")
                break

    # --- FINAL FALLBACK ---
    # If we are here, it means all 5 attempts with Search failed.
    # We try ONE last time without the search tool to keep the site populated.
    print("All retries with Search failed. Attempting final non-grounded fallback...")
    try:
        fallback_res = client.models.generate_content(
            model=model_id,
            contents=prompt + " (Search is unavailable, use internal knowledge to provide latest possible info)"
        )
        return fallback_res.text
    except Exception as final_e:
        print(f"Total system failure: {final_e}")
        return None

def clean_text(text):
    """Strips Markdown artifacts and system prompts from the text."""
    if not text: return ""
    # Remove bold markers and headers
    text = re.sub(r'[*#]', '', text)
    # Remove potential AI block markers
    text = text.replace("```html", "").replace("```", "")
    return text.strip()

def extract_section(full_text, tag):
    """Extracts content between [[TAG]] markers using string slicing."""
    if not full_text: return ""
    start_marker = f"[[{tag}]]"
    try:
        if start_marker not in full_text:
            return ""
        start_idx = full_text.find(start_marker) + len(start_marker)
        end_idx = full_text.find("[[", start_idx)
        
        if end_idx == -1:
            content = full_text[start_idx:]
        else:
            content = full_text[start_idx:end_idx]
        return clean_text(content)
    except:
        return ""

def should_upd(current_data, key, hrs):
    """Checks timestamp in data to see if update is needed."""
    last = current_data.get("last_updated", {}).get(key)
    if not last: return True
    try:
        last_time = datetime.datetime.fromisoformat(last)
        return (datetime.datetime.now() - last_time).total_seconds() >= hrs * 3600
    except: return True

def generate_pages(data):
    pages = {
        "index": "Front Page", "markets": "Share Market", "business": "Trade & Tech",
        "gems": "Undervalued Gems", "world": "World News", "india": "Indian News",
        "misc": "Miscellaneous", "live": "Live Tracker"
    }
    
    # Map the URL slug to the [[TAG]] used in the Mega-Prompt
    tag_map = {
        "markets": "MARKETS", "business": "TRADE_TECH",
        "world": "WORLD", "india": "INDIA", "misc": "MISC", "gems": "GEMS"
    }

    nav = "<nav>" + " | ".join([f'<a href="{s}.html">{t}</a>' for s, t in pages.items()]) + "</nav>"
    
    all_content = data["sections"].get("all_news", "")

    for slug, title in pages.items():
        html_body = ""
        
        if slug == "index":
            # --- Robust Headline Extraction ---
            html_body = "<ul>"
            all_content = data["sections"].get("all_news", "")
            
            # 1. Clean the text and split into lines
            # We filter out tags, empty lines, and the Gem disclaimers
            lines = [l.strip() for l in all_content.split('\n') if l.strip()]
            
            headlines = []
            for line in lines:
                # Remove prefixes like '1.', '-', '*', or 'Headline:'
                clean_line = re.sub(r'^[\d\.\-\*\s]+|Headline:\s*', '', line, flags=re.IGNORECASE).strip()
                
                # HEADLINE RULES: 
                # - Must be at least 30 characters long
                # - Must NOT be a Tag line (e.g., [[MARKETS]])
                # - Must NOT be longer than 160 characters (to avoid full paragraphs)
                if 30 < len(clean_line) < 160 and "[[" not in line:
                    headlines.append(clean_line)
            
            # 2. Pick the first 15 unique headlines found across all sections
            unique_headlines = list(dict.fromkeys(headlines))
            for h in unique_headlines[:15]:
                html_body += f"<li>{h}</li>"
            
            html_body += "</ul>"

        elif slug == "live":
            html_body = f"<h2>Current Topic: {data.get('page8_topic')}</h2>"
            for item in data.get("page8_timeline", []):
                html_body += f"<div class='update'><strong>{item['time']}</strong>: {item['text']}</div><hr>"

        else:
            # PULL EVERYTHING FROM THE ALL_NEWS BLOCK
            tag = tag_map.get(slug)
            content = extract_section(all_content, tag)
            
            if not content and slug == "gems":
                content = "Researching new gems... check back in 24h."

            # Format the news blocks with Google Search links
            blocks = content.split('\n')
            for b in blocks:
                if len(b.strip()) > 20:
                    search_url = f"https://www.google.com/search?q={urllib.parse.quote(b[:100])}"
                    html_body += f"<div class='news-block'>{b} <br><a href='{search_url}' target='_blank'>Verify on Google ↗</a></div><hr>"

        full_html = f"""<!DOCTYPE html><html><head><link rel="stylesheet" href="style.css"></head><body>
            <div class="paper"><header><h1>THE HOURLY JOURNAL</h1>{nav}</header><hr>
            <main><h2>{title}</h2>{html_body}</main></div></body></html>"""
        
        with open(f"{slug}.html", "w", encoding="utf-8") as f:
            f.write(full_html)

def main():
    data = load_data()
    now = datetime.datetime.now()
    updated = False

    # 1. TRIGGER MEGA PROMPT (Hourly)
    if should_upd(data, "global_sync", 1):
        print("Fetching Mega-Update from Gemini...")
        
        include_gems = "Also include [[GEMS]] section with 5 undervalued Indian stocks (P/E focus)." if should_upd(data, "daily_gems", 24) else ""

        mega_prompt = f"""
        Search and provide news for these sections. Wrap in [[TAGS]]:
        [[MARKETS]] - Top 10 Indian & World Market news.
        [[TRADE_TECH]] - Top 10 Business & Tech news.
        [[WORLD]] - Top 10 World news.
        [[INDIA]] - Top 10 Indian news.
        [[MISC]] - Top 10 Sports/Ent.
        [[LIVE]] - 1-sentence update on {data['page8_topic']}. 
        (If a bigger story exists, start with 'NEW_TOPIC: [Name]').
        {include_gems}
        Rules: 1-para summaries, no markdown (** or #), clean text only.
        For [[GEMS]], provide only the list of 5 stocks and 1-sentence logic. Do NOT include financial advice disclaimers or introductory fluff.
        """

        res = get_gemini_news(mega_prompt)
        
        if res:
            data["sections"]["all_news"] = res
            if "[[GEMS]]" in res:
                data["sections"]["gems"] = extract_section(res, "GEMS")
                data["last_updated"]["daily_gems"] = now.isoformat()
            
            # Live Tracker Logic
            live_update = extract_section(res, "LIVE")
            if "NEW_TOPIC:" in live_update:
                data["page8_topic"] = live_update.split("NEW_TOPIC:")[1].split('\n')[0].strip()
                data["page8_timeline"] = [{"time": now.strftime("%H:%M"), "text": clean_text(live_update)}]
            elif live_update:
                data["page8_timeline"].insert(0, {"time": now.strftime("%H:%M"), "text": clean_text(live_update)})
            
            data["page8_timeline"] = data["page8_timeline"][:24]
            data["last_updated"]["global_sync"] = now.isoformat()
            updated = True
            
            with open('data.json', 'w') as f:
                json.dump(data, f, indent=4)
    
    # 2. ALWAYS regenerate pages from either fresh or cached data
    generate_pages(data)

if __name__ == "__main__":
    main()
