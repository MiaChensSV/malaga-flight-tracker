# Malaga Flight Tracker

Monitor flight prices from Scandinavia (CPH, GOT, ARN) to Malaga (AGP). Get Telegram alerts when flights are cheap **and** your rental apartment is available.

## How it works

1. **GitHub Actions** runs every 6 hours
2. Checks **Google Calendar** for apartment availability (5+ day free windows)
3. Fetches **flight prices** from Kiwi Tequila API for available dates only
4. Sends **Telegram alert** when price < threshold and apartment is free
5. **Dashboard** on GitHub Pages shows prices, calendar, and settings

## Setup

### 1. Supabase

1. Create a free project at [supabase.com](https://supabase.com)
2. Go to SQL Editor and run the contents of `supabase_schema.sql`
3. Update the `apartments` table with your real Google Calendar IDs
4. Note your project URL and anon key

### 2. Google Calendar

1. Create a [Google Cloud project](https://console.cloud.google.com)
2. Enable the **Google Calendar API**
3. Create a **Service Account** and download the JSON key
4. Share both apartment calendars with the service account email (read-only)

### 3. Kiwi Tequila API

1. Sign up at [tequila.kiwi.com](https://tequila.kiwi.com)
2. Get your API key

### 4. Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot, save the token
3. Get your chat ID (message [@userinfobot](https://t.me/userinfobot))

### 5. GitHub Repository

1. Create a public repo (required for free Actions minutes)
2. Push this code
3. Add these **repository secrets** (Settings → Secrets → Actions):
   - `KIWI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `GOOGLE_SERVICE_ACCOUNT_JSON` (entire JSON file contents)
4. Enable **GitHub Pages** (Settings → Pages → Source: Deploy from branch, `main`, `/docs`)

### 6. Dashboard

1. Open your GitHub Pages URL
2. Go to **Settings** tab
3. Enter your Supabase URL and anon key
4. Adjust price thresholds per route

## Local testing

```bash
cd scripts
pip install -r requirements.txt

# Set environment variables
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_KEY="eyJ..."
export KIWI_API_KEY="your-key"
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'

python check_prices.py
```

## Project structure

```
malaga-flight-tracker/
├── .github/workflows/check-prices.yml   # Cron job (every 6h)
├── scripts/
│   ├── check_prices.py                  # Main orchestrator
│   ├── flight_api.py                    # Kiwi Tequila API
│   ├── calendar_api.py                  # Google Calendar
│   ├── notify.py                        # Telegram alerts
│   ├── db.py                            # Supabase client
│   └── requirements.txt
├── docs/                                # GitHub Pages
│   ├── index.html                       # Dashboard
│   ├── settings.html                    # Settings page
│   ├── style.css
│   └── app.js
├── supabase_schema.sql                  # Database schema
└── README.md
```
