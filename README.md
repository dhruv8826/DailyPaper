# The Hourly Journal 📰
**An autonomous, AI-driven "Living Newspaper" that updates every hour with a stateful persistence system.**

Live Demo: `https://<your-username>.github.io/<your-repo-name>/`

---

## 🚀 Project Overview
The Hourly Journal is a multi-page news ecosystem built to function as a real-time, curated newspaper. Unlike standard RSS aggregators, this project uses the **Gemini 3.1 Flash Lite LLM** with **Google Search Grounding** to perform research, summarize complex events, and categorize findings into 8 distinct sections.

The project runs entirely on a **$0 budget** by leveraging GitHub Actions for compute and GitHub Pages for hosting.

## ✨ Key Features
- **8 Specialized Sections:**
  - **Front Page:** Headline-only overview with deep-linking to internal pages.
  - **Share Market:** Dual-view of Indian and World markets with 1-para summaries.
  - **Trade & Tech:** Analysis of business shifts and technology movements.
  - **Undervalued Gems:** (Daily Update) AI-curated list of 5 undervalued Indian stocks based on P/E ratios and recent filings.
  - **World & Indian News:** High-priority hourly news mixed with long-running stories.
  - **Miscellaneous:** Sports, Entertainment, and Lifestyle.
  - **Live Tracker:** A stateful timeline that tracks a single major global event, persisting until the story concludes.
- **Intelligent Scheduling:** Hybrid update cycles (Hourly, 4-Hourly, and 24-Hourly) to maximize the utility of the Gemini API quota.
- **Stateful Memory:** Uses a `data.json` file as a "database" to persist timelines and track update intervals across stateless GitHub Action runs.
- **Automated Grounding:** Every story includes a dynamically generated "Search on Google" link for instant verification.

## 🛠️ Stateful Agent Architecture
Unlike a simple scraper, this project operates as a **Stateful AI Agent** that manages its own persistence layer:
- **Database (`data.json`):** Acts as a local NoSQL state store, preserving the context of past updates and investment research.
- **Intelligent Sync Logic:** - **Global Sync:** Triggers every 1 hour for general news and tracker updates.
  - **Gems Research:** A deep-dive 24-hour cycle specifically for qualitative stock analysis.
- **Structured JSON Output:** Forced schema enforcement via the Gemini API to ensure 100% reliable data parsing and UI consistency.

## 🛠 Tech Stack
- **Language:** Python 3.10+
- **LLM:** Google Gemini 3.1 Flash Lite (via `google-genai` SDK)
- **CI/CD:** GitHub Actions (Automation & Scheduling)
- **Hosting:** GitHub Pages (Static Hosting)
- **Storage:** `data.json` (Flat-file state management)
- **Styling:** Vanilla CSS (Classic Newspaper Aesthetic)

## 🏗 System Architecture



1. **Trigger:** A GitHub Action cron job triggers at the start of every hour.
2. **Logic Engine (`update_news.py`):** - Loads the current state from `data.json`.
   - Compares timestamps to decide which sections require a fresh API call.
   - Communicates with Gemini 3.1 Flash Lite using a "Tag-based" batching system.
3. **Parsing:** The script cleans Markdown artifacts (stripping `**`, `#`, etc.) and splits the batch response into individual pages using custom tag-parsing logic.
4. **Build:** Generates 8 distinct `.html` files based on the pre-processed data.
5. **Persistence:** Commits the updated `data.json` and `.html` files back to the GitHub repository.
6. **Deploy:** GitHub Pages automatically detects the commit and serves the updated site.

## 🚦 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/your-username/DailyPaper.git](https://github.com/your-username/DailyPaper.git)
   ```

2. **Install Dependencies:**
   ```bash
   pip install google-genai
   ```

3. **Configure Secrets:**
   Add your `GEMINI_API_KEY` (from Google AI Studio) to your GitHub Repository Secrets:
   - Go to **Settings > Secrets and variables > Actions**.
   - Click **New repository secret**.
   - Name: `GEMINI_API_KEY` | Value: `[Your-Actual-Key]`.

4. **Enable Write Permissions:**
   Ensure the GitHub Action bot can commit changes back to your repository:
   - Go to **Settings > Actions > General**.
   - Under **Workflow permissions**, select **Read and write permissions**.
   - Click **Save**.

## ⚖️ Optimization & Quotas
- **Model Choice:** This project utilizes **Gemini 3.1 Flash Lite**, which offers a generous **500 Requests Per Day** on the Free Tier, making hourly updates reliable and sustainable.
- **Rate Limiting:** The script implements a cooldown sequence to respect **RPM (Requests Per Minute)** limits while maintaining high availability.
- **State Persistence:** By committing `data.json` back to the repository, the application maintains a "memory" of previous events, allowing for complex features like the **Live Tracker** timeline.

## ✅ Trust & Verification
To combat AI hallucinations and ensure data integrity, every news item and stock gem includes:
- **Dynamic Search Links:** Automated "Verify on Google ↗" deep-links generated for every single story.
- **Grounding:** All summaries are grounded in real-time Google Search results before being processed into the state store.

---
*Developed by dhruv8826*
   
