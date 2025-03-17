import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_calendar_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '../env/google_calendar.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service


def create_event(service, summary, location, description, start_time, end_time):
    """Creates a calendar event."""
    event = {
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'America/Los_Angeles',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 30},
            ],
        },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    print(f'Event created: {event.get("htmlLink")}')
    return event


def convert_md_to_datetime_range(date_str):
    # Split the string by the period
    parts = date_str.split('.')

    # Ensure we have exactly 2 parts (month and day)
    if len(parts) != 2:
        raise ValueError("Date format must be 'm.d'")

    try:
        month = int(parts[0])
        day = int(parts[1])
    except ValueError:
        raise ValueError("Month and day must be numbers")

    # Validate month and day
    if not 1 <= month <= 12:
        raise ValueError("Month must be between 1 and 12")

    # Get the current year
    current_year = datetime.datetime.now().year

    # Create the start datetime (00:00:00)
    start_datetime = datetime.datetime(current_year, month, day, 0, 0, 0)

    # Create the end datetime (23:59:59)
    end_datetime = datetime.datetime(current_year, month, day, 23, 59, 59)

    return start_datetime, end_datetime


# Example usage
if __name__ == '__main__':
    service = get_calendar_service()

    # Create an event 1 hour from now that lasts 1 hour
    now = datetime.datetime.now(datetime.UTC)
    start_time = now + datetime.timedelta(hours=1)
    end_time = start_time + datetime.timedelta(hours=1)

    create_event(
        service=service,
        summary='Team Meeting',
        location='Conference Room 1',
        description='Weekly team sync-up',
        start_time=start_time,
        end_time=end_time
    )