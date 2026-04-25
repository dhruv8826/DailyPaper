import os
from google import genai
from google.genai import types
from datetime import datetime

# Initialize Gemini Client
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def generate_newspaper():
    # Prompt optimized for 2026 Grounding
    prompt = """
    Search for the top 10 global and Indian news stories from the last 24 hours.
    Focus on: Geopolitics, Finance (Undervalued stocks/Defense), and Tech.
    Output ONLY valid HTML content inside a <div> with class 'news-grid'.
    Format: <h2>Headline</h2><p>Summary</p><span class='source'>Source Name</span>
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )

    # Simple Template Engine
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="style.css">
        <title>The Hourly Journal</title>
    </head>
    <body>
        <div class="paper">
            <header>
                <h1>THE HOURLY JOURNAL</h1>
                <div class="meta">Edition: {current_time} | Location: Gurugram</div>
            </header>
            <hr>
            {response.text}
        </div>
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

if __name__ == "__main__":
    generate_newspaper()
