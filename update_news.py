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
    updated = False

    def should_upd(key, hrs):
        last = data["last_updated"].get(key)
        return not last or (now - datetime.datetime.fromisoformat(last)).total_seconds() >= hrs*3600

    # BATCH 1: Finance & Tech (Pages 2, 3) - Every Hour
    if should_upd("finance_tech", 1):
        prompt = "Provide news for [[MARKETS]] and [[TRADE_TECH]]. 10 news each, 1-para summaries. No markdown."
        data["sections"]["finance_tech"] = get_gemini_news(prompt)
        data["last_updated"]["finance_tech"] = now.isoformat()
        updated = True

    # BATCH 2: General News (Pages 5, 6, 7) - Every Hour (Hybrid logic can be added here)
    if should_upd("general_news", 1):
        prompt = "Provide news for [[WORLD]], [[INDIA]], and [[MISC]]. 10 news each, 1-para summaries. No markdown."
        data["sections"]["general_news"] = get_gemini_news(prompt)
        data["last_updated"]["general_news"] = now.isoformat()
        updated = True

    # BATCH 3: Undervalued Gems (Page 4) - Every 24 Hours
    if should_upd("gems", 24):
        prompt = "List 5 undervalued Indian stocks based on P/E and sector tailwinds. 1-para each. No markdown."
        data["sections"]["gems"] = get_gemini_news(prompt)
        data["last_updated"]["gems"] = now.isoformat()
        updated = True

    # BATCH 4: Live Tracker (Page 8) - Every Hour
    if should_upd("live", 1):
        prompt = f"Provide a 1-sentence update on {data['page8_topic']}. If a bigger story exists, start with 'NEW_TOPIC: [Name]'."
        res = get_gemini_news(prompt)
        if res:
            if "NEW_TOPIC:" in res:
                parts = res.split("NEW_TOPIC:")
                data["page8_topic"] = parts[1].split('\n')[0].strip()
                data["page8_timeline"] = [{"time": now.strftime("%H:%M"), "text": clean_text(res)}]
            else:
                data["page8_timeline"].insert(0, {"time": now.strftime("%H:%M"), "text": clean_text(res)})
            data["page8_timeline"] = data["page8_timeline"][:24]
            data["last_updated"]["live"] = now.isoformat()
            updated = True

    if updated:
        with open('data.json', 'w') as f: json.dump(data, f)
        generate_pages(data)

if __name__ == "__main__":
    main()
