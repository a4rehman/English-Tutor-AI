# English Vocabulary Extractor 🎓📚

An AI-powered tool that extracts English vocabulary from YouTube videos with **Urdu translations** — designed for Urdu-speaking English learners.

## ✨ Features

- 🎬 **YouTube Transcript Extraction** — Paste any YouTube URL and auto-fetch captions
- 🤖 **GPT-4o Analysis** — AI extracts high-value vocabulary with Urdu meanings
- 📊 **Google Sheets Integration** — Save results with automatic duplicate checking
- 📥 **CSV Download** — Export vocabulary for offline study
- 🔍 **Search & Filter** — Filter by difficulty level (Beginner/Intermediate/Advanced)
- 🌙 **Premium Dark UI** — Glassmorphic design with smooth animations

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python FastAPI |
| Transcript | youtube-transcript-api |
| AI | OpenAI GPT-4o |
| Storage | Google Sheets (gspread) |
| Frontend | Vanilla HTML/CSS/JS |

## 🚀 Quick Start

```bash
# 1. Activate virtual environment
.\.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file (copy from .env.example)
copy .env.example .env
# Edit .env with your API keys

# 4. Run the server
python main.py
```

Then open **http://127.0.0.1:8000** in your browser.

## ⚙️ Configuration

Create a `.env` file with:

```env
OPENAI_API_KEY=sk-your-key-here
GOOGLE_SHEET_ID=your-sheet-id          # Optional
GOOGLE_CREDENTIALS_PATH=credentials/service_account.json  # Optional
```

> **Note:** Google Sheets integration is optional. You can still extract vocabulary and download CSV without it.

## 📂 Project Structure

```
English_tutor/
├── main.py              # FastAPI server
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
├── src/
│   ├── transcript.py    # YouTube transcript fetcher
│   ├── vocabulary.py    # OpenAI vocabulary extraction
│   └── sheets.py        # Google Sheets integration
├── static/
│   ├── index.html       # Frontend UI
│   ├── style.css        # Dark glassmorphic theme
│   └── script.js        # Client-side logic
└── credentials/         # Google service account JSON
```
