# Reddit Opportunity Radar v2.0 🚀

AI-powered tool to scan Reddit for business opportunities, SaaS ideas, and user pain points.

## Features
- **Dual AI Support**: Choose between OpenAI (GPT-4o) or Google Gemini.
- **Real-time Scanning**: Monitors specific subreddits (e.g., r/SaaS, r/Entrepreneur).
- **Smart Filtering**: Uses keywords and AI analysis to find genuine opportunities.
- **CSV Export**: Saves found opportunities to `firsatlar.csv`.

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Create a `.env` file in the root directory:
   ```env
   # Choose AI Provider: "openai" or "gemini"
   AI_PROVIDER=openai

   # API Keys
   OPENAI_API_KEY=sk-your_key_here
   GEMINI_API_KEY=your_gemini_key_here

   # Optional Settings
   SCAN_INTERVAL=60
   ```

## Usage

Run the main script:
```bash
python market_radar_v2.py
```

The bot will start scanning Reddit and print any high-scoring opportunities to the console and save them to the CSV file.
