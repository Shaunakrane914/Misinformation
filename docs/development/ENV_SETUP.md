# Environment Variables Setup Guide

This guide will help you set up all the required API keys for the Aegis Protocol system.

## Required API Keys

### 1. Google Gemini API Key (Required for AI processing)

**What it's for:** Powers the AI agents for claim verification and analysis

**How to get it:**
1. Visit https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key

**Where to add it:**
```env
GEMINI_API_KEY=YOUR_KEY_HERE
GEMINI_API_KEY_1=YOUR_KEY_HERE
GEMINI_API_KEY_2=YOUR_KEY_HERE
```

**Cost:** Free tier available (60 requests/minute)

---

### 2. Yahoo Finance API Key (Optional - for Scout Agent)

**What it's for:** Fetches real-time stock market data for financial misinformation detection

**How to get it:**
1. Visit https://www.yahoofinanceapi.com/
2. Sign up for an account
3. Get your API key from the dashboard

**Where to add it:**
```env
YF_API_KEY=YOUR_KEY_HERE
```

**Note:** The Scout Agent will work with limited functionality without this key.

---

### 3. Apify Token (Optional - for Trending Agent)

**What it's for:** Scrapes Instagram and social media for paparazzi content analysis

**How to get it:**
1. Visit https://console.apify.com/
2. Sign up for a free account
3. Go to Settings → Integrations
4. Copy your API token

**Where to add it:**
```env
APIFY_TOKEN=YOUR_TOKEN_HERE
```

**Note:** Without this, the Trending Agent will skip Instagram scraping but still work with news sources.

---

### 4. Supabase Database (Optional - for persistence)

**What it's for:** Stores claims, evidence, and verification results

**How to get it:**
1. Visit https://supabase.com/
2. Create a new project (free tier available)
3. Go to Project Settings → API
4. Copy the URL and service_role key

**Where to add it:**
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
```

**Note:** The system will work in demo mode without this, using cached data.

---

## Quick Setup Steps

1. **Copy the `.env` file template:**
   - The `.env` file already exists in your project root
   - Open it in a text editor

2. **Add your API keys:**
   - Replace the placeholder values with your actual keys
   - Keep the format: `KEY_NAME=value` (no spaces around =)

3. **Restart the server:**
   ```bash
   # Stop the current server (Ctrl+C)
   # Then restart it
   uvicorn backend.main:app --reload
   ```

4. **Verify setup:**
   - Check the startup logs
   - Warnings about missing keys should disappear

---

## Priority Levels

**🔴 Must Have:**
- `GEMINI_API_KEY` - Core AI functionality won't work without this

**🟡 Recommended:**
- `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` - For saving claims permanently

**🟢 Optional (Enhanced Features):**
- `YF_API_KEY` - Real-time stock data for Scout Agent
- `APIFY_TOKEN` - Instagram scraping for Trending Agent

---

## Troubleshooting

**Q: I added keys but still see warnings**
- Make sure there are no extra spaces in the `.env` file
- Ensure the file is named exactly `.env` (not `.env.txt`)
- Restart the server after making changes

**Q: Can I test without any API keys?**
- Yes! The system will work in demo mode with cached sample data
- You'll see warnings but core functionality remains

**Q: How do I hide my API keys from Git?**
- The `.env` file is already in `.gitignore`
- Never commit API keys to GitHub
- Share keys securely (password manager, environment variables in deployment)

---

## Cost Estimate

| Service | Free Tier | Cost After Free |
|---------|-----------|-----------------|
| Google Gemini | 60 req/min | Pay-as-you-go |
| Yahoo Finance API | Limited | ~$10/month |
| Apify | 5 actors/month | ~$49/month |
| Supabase | 500MB storage | ~$25/month |

**For development/testing:** You can stay within free tiers!

---

## Support

If you run into issues:
1. Check the server logs for specific error messages
2. Verify your API keys are valid by testing them in the provider's dashboard
3. Ensure all services are active and not suspended

**Note:** The system is designed to degrade gracefully - missing optional keys will reduce features but not break the app.
