import os, json, time, datetime, urllib.parse, re
from google import genai
from google.genai import types

# 1. SETUP & CLIENT
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def load_data():
    default_structure = {
        "last_updated": {},
        "page8_timeline": [],
        "page8_topic": "Global Geopolitics",
        "sections": {
            "finance_tech": "", "general_news": "", "gems": ""
        }
    }
    if os.path.exists('data.json'):
        try:
            with open('data.json', 'r') as f:
                data = json.load(f)
                # Ensure all keys exist to prevent KeyErrors
                for key, val in default_structure.items():
                    if key not in data: data[key] = val
                return data
        except: return default_structure
    return default_structure

def get_gemini_news(prompt):
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        )
        time.sleep(2) 
        return response.text
    except Exception as e:
        print(f"API Error: {e}")
        return None

def clean_text(text):
    """Strips Markdown artifacts (**, ##, ###) from Gemini's response."""
    if not text: return ""
    text = re.sub(r'[*#]', '', text)
    return text.strip()

def extract_section(full_text, tag):
    """Extracts content between [[TAG]] markers using string slicing."""
    if not full_text: return ""
    
    start_marker = f"[[{tag}]]"
    # We look for the start of the next tag or the end of the string
    try:
        if start_marker not in full_text:
            return ""
        
        start_idx = full_text.find(start_marker) + len(start_marker)
        # Find where the next section starts by looking for '[[' after our start
        end_idx = full_text.find("[[", start_idx)
        
        if end_idx == -1:
            content = full_text[start_idx:]
        else:
            content = full_text[start_idx:end_idx]
            
        return clean_text(content)
    except Exception as e:
        print(f"Error parsing section {tag}: {e}")
        return ""

def generate_pages(data):
    pages = {
        "index": "Front Page", "markets": "Share Market", "business": "Trade & Tech",
        "gems": "Undervalued Gems", "world": "World News", "india": "Indian News",
        "misc": "Miscellaneous", "live": "Live Tracker"
    }
    
    # Tag mapping to separate content within shared Gemini responses
    tag_map = {
        "markets": ("finance_tech", "MARKETS"),
        "business": ("finance_tech", "TRADE_TECH"),
        "world": ("general_news", "WORLD"),
        "india": ("general_news", "INDIA"),
        "misc": ("general_news", "MISC")
    }

    nav = "<nav>" + " | ".join([f'<a href="{s}.html">{t}</a>' for s, t in pages.items()]) + "</nav>"

    for slug, title in pages.items():
        html_body = ""

        if slug == "index":
            # Page 1: Headlines only (extracted from various sections)
            html_body = "<ul>"
            all_text = data["sections"].get("finance_tech", "") + data["sections"].get("general_news", "")
            headlines = [l.strip() for l in all_text.split('\n') if l.strip() and l[0].isdigit()][:15]
            for h in headlines:
                html_body += f"<li>{clean_text(h)}</li>"
            html_body += "</ul>"

        elif slug == "live":
            # Page 8: Timeline
            html_body = f"<h2>Current Topic: {data['page8_topic']}</h2>"
            for item in data.get("page8_timeline", []):
                html_body += f"<div class='update'><strong>{item['time']}</strong>: {item['text']}</div><hr>"

        elif slug == "gems":
            # Page 4: Undervalued Gems (Daily)
            html_body = data["sections"].get("gems", "Updating daily...")

        else:
            # Pages 2, 3, 5, 6, 7 (Parsed via Tags)
            source_key, tag = tag_map.get(slug, (None, None))
            raw_content = extract_section(data["sections"].get(source_key, ""), tag)
            
            # Split into blocks and add Google Search links
            blocks = raw_content.split('\n\n')
            for b in blocks:
                if b.strip():
                    headline = b.split('\n')[0][:100]
                    search_url = f"https://www.google.com/search?q={urllib.parse.quote(headline)}"
                    html_body += f"<div class='news-block'>{b} <br><a href='{search_url}' target='_blank'>Search on Google ↗</a></div><hr>"

        full_html = f"""<!DOCTYPE html><html><head><link rel="stylesheet" href="style.css"></head><body>
            <div class="paper"><header><h1>THE HOURLY JOURNAL</h1>{nav}</header><hr>
            <main><h2>{title}</h2>{html_body}</main></div></body></html>"""
        
        with open(f"{slug}.html", "w", encoding="utf-8") as f:
            f.write(full_html)

def main():
    data = load_data()
    now = datetime.datetime.now()
    
    # Check if at least 1 hour has passed since the LAST successful global update
    if not should_upd("global_sync", 1):
        # Even if we don't call the API, we regenerate pages from existing data.json
        generate_pages(data)
        return

    # THE MEGA PROMPT: Everything in one go to save quota
    mega_prompt = f"""
    Search and provide news for the following sections. Wrap each in [[TAGS]]:
    [[MARKETS]] - Top 10 Indian & World Market news.
    [[TRADE_TECH]] - Top 10 Business & Tech impact news.
    [[WORLD]] - Top 10 World news.
    [[INDIA]] - Top 10 Indian news.
    [[MISC]] - Top 10 Sports/Entertainment.
    [[LIVE]] - A 1-sentence update on {data['page8_topic']}. 
    (If a bigger story exists, start with 'NEW_TOPIC: [Name]').
    
    Rules: 1-para summaries, no markdown (** or #), clean text only.
    """
    
    response_text = get_gemini_news(mega_prompt)
    
    if response_text:
        # Update our "database" with the new mega-response
        data["sections"]["finance_tech"] = response_text 
        data["sections"]["general_news"] = response_text
        
        # Handle the Live Tracker update within the mega-response
        live_update = extract_section(response_text, "LIVE")
        if live_update:
            if "NEW_TOPIC:" in live_update:
                parts = live_update.split("NEW_TOPIC:")
                data["page8_topic"] = parts[1].split('\n')[0].strip()
                data["page8_timeline"] = [{"time": now.strftime("%H:%M"), "text": clean_text(live_update)}]
            else:
                data["page8_timeline"].insert(0, {"time": now.strftime("%H:%M"), "text": live_update})
            data["page8_timeline"] = data["page8_timeline"][:24]

        data["last_updated"]["global_sync"] = now.isoformat()
        
        with open('data.json', 'w') as f:
            json.dump(data, f)
            
    # Always generate pages (either with new data or cached data)
    generate_pages(data)

if __name__ == "__main__":
    main()
