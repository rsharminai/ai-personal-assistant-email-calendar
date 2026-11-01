#!/usr/bin/env python3
"""
Personal AI Assistant: Extract events from Gmail and update Google Calendar
"""

import os
import base64
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dateutil import parser as date_parser
from dotenv import load_dotenv
import openai

load_dotenv()

# Scopes required
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]

def get_credentials():
    """Obtain and refresh Google credentials."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def get_gmail_service(creds):
    return build("gmail", "v1", credentials=creds)

def get_calendar_service(creds):
    return build("calendar", "v3", credentials=creds)

def fetch_recent_emails(service, max_results=10):
    """Fetch the most recent emails."""
    try:
        results = service.users().messages().list(
            userId="me", maxResults=max_results, q="is:unread"
        ).execute()
        messages = results.get("messages", [])
        emails = []
        for msg in messages:
            msg_data = service.users().messages().get(
                userId="me", id=msg["id"], format="full"
            ).execute()
            payload = msg_data.get("payload", {})
            headers = payload.get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
            body = ""
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain":
                        data = part["body"].get("data")
                        if data:
                            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                            break
            else:
                data = payload.get("body", {}).get("data")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            emails.append({
                "id": msg["id"],
                "subject": subject,
                "sender": sender,
                "body": body[:2000]  # Limit length
            })
        return emails
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

def extract_event_with_ai(email, openai_client):
    """Use OpenAI to extract event details from email."""
    prompt = f"""
Analyze the following email and extract any calendar event information.
If there is a meeting, appointment, deadline, or event mentioned, return a JSON object with:
- summary: short title
- description: brief description
- start_datetime: ISO format (YYYY-MM-DDTHH:MM:SS) or null
- end_datetime: ISO format or null (default 1 hour after start)
- location: if mentioned, else null
- attendees: list of emails if mentioned, else []

If no clear event, return null.

Email Subject: {email['subject']}
From: {email['sender']}
Body:
{email['body']}
"""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500
        )
        content = response.choices[0].message.content.strip()
        # Simple cleanup for JSON
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        import json
        return json.loads(content)
    except Exception as e:
        print(f"AI extraction failed: {e}")
        return None

def extract_event_rule_based(email):
    """Fallback rule-based extraction."""
    text = f"{email['subject']} {email['body']}".lower()
    # Look for date/time patterns
    date_matches = re.findall(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4}|tomorrow|next \w+)', text)
    time_matches = re.findall(r'(\d{1,2}:\d{2}\s?(am|pm)?|\d{1,2}\s?(am|pm))', text)
    
    if not date_matches and not time_matches:
        return None
    
    # Very basic - user should improve this
    try:
        start = date_parser.parse(date_matches[0] if date_matches else "tomorrow", fuzzy=True)
        if time_matches:
            # Rough time attach
            pass
        return {
            "summary": email["subject"][:100],
            "description": f"Extracted from email from {email['sender']}",
            "start_datetime": start.isoformat(),
            "end_datetime": (start + timedelta(hours=1)).isoformat(),
            "location": None,
            "attendees": []
        }
    except:
        return None

def create_calendar_event(service, event_data):
    """Create an event on Google Calendar."""
    if not event_data or not event_data.get("start_datetime"):
        return None
    try:
        start = date_parser.parse(event_data["start_datetime"])
        end = date_parser.parse(event_data.get("end_datetime") or (start + timedelta(hours=1)).isoformat())
        
        event = {
            "summary": event_data.get("summary", "New Event from Email"),
            "description": event_data.get("description", ""),
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        }
        if event_data.get("location"):
            event["location"] = event_data["location"]
        
        created = service.events().insert(calendarId="primary", body=event).execute()
        print(f"Event created: {created.get('htmlLink')}")
        return created
    except Exception as e:
        print(f"Failed to create event: {e}")
        return None

def main():
    print("Starting Personal Email-to-Calendar Assistant...")
    creds = get_credentials()
    gmail = get_gmail_service(creds)
    calendar = get_calendar_service(creds)
    
    openai_client = None
    if os.getenv("OPENAI_API_KEY"):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        openai_client = openai
        print("OpenAI enabled for smarter extraction.")
    else:
        print("No OpenAI key found. Using basic rule-based extraction.")
    
    emails = fetch_recent_emails(gmail)
    print(f"Found {len(emails)} recent unread emails.")
    
    for email in emails:
        print(f"\nProcessing: {email['subject']}")
        event_data = None
        if openai_client:
            event_data = extract_event_with_ai(email, openai_client)
        if not event_data:
            event_data = extract_event_rule_based(email)
        
        if event_data and event_data.get("summary"):
            print(f"Detected event: {event_data['summary']}")
            create_calendar_event(calendar, event_data)
        else:
            print("No clear event detected.")
    
    print("\nDone. Check your Google Calendar.")

if __name__ == "__main__":
    main()
