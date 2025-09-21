import os
import json
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import gspread
import pytz

# --- CONFIGURATION & CONSTANTS ---
SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/spreadsheets"]
CONFIG_FILE = 'config.json'

# --- AUTHENTICATION HELPER ---
def get_google_creds():
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

# --- BUSINESS LOGIC & TOOLS ---

def get_available_services() -> list:
    """
    Retrieves the list of available services, their duration, and price.
    This tool should be used when the user asks what services are offered.
    Returns a list of service dictionaries.
    """
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return config.get('services', [])
    except Exception as e:
        return [{"error": f"Error reading services: {e}"}]

def get_available_slots(date_str: str) -> list:
    """
    Finds available booking slots for a given date.
    The date must be in 'YYYY-MM-DD' format.
    Returns a list of available time slots as strings (e.g., ["09:00", "10:00"]).
    """
    try:
        creds = get_google_creds()
        service = build("calendar", "v3", credentials=creds)
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        business_hours = config['business_hours']
        start_hour, start_minute = map(int, business_hours['start'].split(':'))
        end_hour, end_minute = map(int, business_hours['end'].split(':'))
        
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        time_min = datetime(target_date.year, target_date.month, target_date.day, start_hour, start_minute, tzinfo=timezone.utc).isoformat()
        time_max = datetime(target_date.year, target_date.month, target_date.day, end_hour, end_minute, tzinfo=timezone.utc).isoformat()

        events_result = service.events().list(
            calendarId=os.getenv("GOOGLE_CALENDAR_ID", "primary"),
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])

        busy_slots = []
        for event in events:
            start = datetime.fromisoformat(event['start']['dateTime'])
            end = datetime.fromisoformat(event['end']['dateTime'])
            busy_slots.append((start, end))

        available_slots = []
        slot_start_time = datetime(target_date.year, target_date.month, target_date.day, start_hour, start_minute)
        slot_duration = timedelta(minutes=60) # Assume 60 min slots
        
        while slot_start_time.hour < end_hour:
            slot_end_time = slot_start_time + slot_duration
            is_busy = False
            for busy_start, busy_end in busy_slots:
                if max(slot_start_time.astimezone(timezone.utc), busy_start) < min(slot_end_time.astimezone(timezone.utc), busy_end):
                    is_busy = True
                    break
            
            if not is_busy:
                available_slots.append(slot_start_time.strftime("%H:%M"))
                
            slot_start_time += slot_duration
            
        return available_slots

    except Exception as e:
        return [{"error": f"Error getting slots: {e}"}]


def book_appointment(service_name: str, date_str: str, time_str: str, user_name: str, user_email: str) -> str:
    """
    Books an appointment. Returns a confirmation string.
    Use this only when all details (service, date, time, user name, and user email) are confirmed.
    """
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        service_details = next((s for s in config['services'] if s['name'].lower() == service_name.lower()), None)
        if not service_details:
            return f"Error: Service '{service_name}' not found."
        duration = service_details['duration_minutes']
        
        creds = get_google_creds()
        
        local_tz = pytz.timezone("Asia/Kolkata")
        naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        local_dt_start = local_tz.localize(naive_dt)
        local_dt_end = local_dt_start + timedelta(minutes=duration)

        event = {
            "summary": f"{service_name} for {user_name}",
            "start": {"dateTime": local_dt_start.isoformat(), "timeZone": str(local_tz)},
            "end": {"dateTime": local_dt_end.isoformat(), "timeZone": str(local_tz)},
            "attendees": [{"email": user_email}],
        }
        
        calendar_service = build("calendar", "v3", credentials=creds)
        created_event = calendar_service.events().insert(calendarId=os.getenv("GOOGLE_CALENDAR_ID", "primary"), body=event).execute()

        # --- CODE CORRECTION HERE ---
        # Use gspread.authorize() for OAuth credentials instead of service_account()
        gc = gspread.authorize(creds)
        # --- END CORRECTION ---

        spreadsheet = gc.open_by_url(os.environ["GOOGLE_SHEET_URL"])
        worksheet = spreadsheet.sheet1
        worksheet.append_row([datetime.now().isoformat(), user_name, user_email, service_name, date_str, time_str])

        send_confirmation_email(user_email, user_name, service_name, date_str, time_str)
        
        return f"Appointment confirmed for {service_name} on {date_str} at {time_str}. A confirmation email has been sent."

    except Exception as e:
        return f"Error booking appointment: {e}"

def send_confirmation_email(recipient_email, user_name, service_name, date_str, time_str):
    # Helper function, no changes needed
    sender_email = os.environ["SENDER_EMAIL"]
    sender_password = os.environ["SENDER_PASSWORD"]
    with open(CONFIG_FILE, 'r') as f: config = json.load(f)
    business_name = config['business_name']
    subject = f"Booking Confirmation from {business_name}"
    body = f"Hi {user_name},\n\nThis is a confirmation for your appointment.\n\nService: {service_name}\nDate: {date_str}\nTime: {time_str}\n\nWe look forward to seeing you!\n\nBest,\nThe {business_name} Team"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(sender_email, sender_password)
            smtp_server.sendmail(sender_email, recipient_email, msg.as_string())
    except Exception as e:
        print(f"Failed to send email: {e}")