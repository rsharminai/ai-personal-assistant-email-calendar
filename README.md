# Personal AI Assistant: Email to Calendar

A Python-based personal assistant that monitors your Gmail inbox, extracts potential calendar events (meetings, deadlines, appointments) from emails, and automatically adds them to your Google Calendar.

## Features
- Authenticate with Gmail and Google Calendar via OAuth
- Fetch recent/unread emails
- Use AI (OpenAI) or rule-based parsing to detect events
- Create calendar events with extracted details
- Optional: Run as a scheduled script or extend into a full agent

## Prerequisites
1. A Google account
2. Python 3.9+
3. (Optional) OpenAI API key for smarter extraction

## Setup Instructions

### 1. Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the following APIs:
   - Gmail API
   - Google Calendar API
4. Go to **Credentials** → **Create Credentials** → **OAuth client ID**
5. Choose **Desktop app**
6. Download the JSON file and rename it to `credentials.json` in this project folder

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file:
```
OPENAI_API_KEY=your_key_here   # Optional, for AI extraction
```

### 4. Run the Assistant
```bash
python assistant.py
```
On first run, a browser window will open for Google authorization. Grant permissions for Gmail (read) and Calendar (read/write).

## How It Works
1. Authenticates using OAuth (tokens saved to `token.json`)
2. Fetches the latest emails from Gmail
3. Analyzes each email for event-related information (dates, times, titles, attendees)
4. If an event is detected, creates it on your primary Google Calendar
5. Marks processed emails (optional)

## Customization
- Edit the system prompt in `assistant.py` for better AI extraction
- Adjust scopes or add more features (e.g., Slack notifications, task creation)
- Schedule with cron or run as a background service

## Privacy & Security
- Credentials stay local (`credentials.json` and `token.json` are gitignored)
- Only requests necessary scopes: `gmail.readonly` and `calendar.events`
- Review the code before running

## Next Steps / Extensions
- Integrate with n8n or Make.com for no-code version
- Add voice interface using the Voice tool
- Build a full conversational agent with LangChain or LangGraph
- Support Outlook via Microsoft Graph API

## Disclaimer
This is a starter template. Always review extracted events before relying on them. Test thoroughly with your own data.
