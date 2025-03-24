import datetime
import os.path
import json
import hashlib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the token files in the secrets folder.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Get the secrets directory path from environment variable
SECRETS_DIR = os.environ.get('SECRETS_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'secrets'))

# Path to the client secrets file
CLIENT_SECRETS_PATH = os.path.join(SECRETS_DIR, 'google_client_secrets.json')


def get_user_secrets_dir(username=None):
    """Get the path to the secrets directory for a specific user.
    
    Args:
        username (str, optional): Username to get secrets for. If None, uses a default directory.
        
    Returns:
        str: Path to the user's secrets directory
    """
    if not username:
        # Use a default directory for anonymous users or system operations
        user_dir = os.path.join(SECRETS_DIR, 'default')
    else:
        # Create a directory for this user
        # Use the username directly as the directory name
        # This is safe because directories can have special characters
        user_dir = os.path.join(SECRETS_DIR, username)
    
    # Ensure the user's secrets directory exists
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
        print(f"Created secrets directory for user {username or 'default'} at {user_dir}")
    
    return user_dir


def get_token_path(username=None):
    """Get the path to the token file for a specific user.
    
    Args:
        username (str, optional): Username to get token for. If None, uses a default token.
        
    Returns:
        str: Path to the token file
    """
    user_dir = get_user_secrets_dir(username)
    return os.path.join(user_dir, 'google_token.json')


def get_calendar_service(username=None):
    """Gets an authorized Google Calendar API service instance for a specific user.
    
    Args:
        username (str, optional): Username to get service for. If None, uses a default token.
    
    Returns:
        A Google Calendar API service instance.
    """
    # Get the token path for this user
    token_path = get_token_path(username)
    
    creds = None
    # Check if the user's token file exists
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Check if client secrets file exists
            if not os.path.exists(CLIENT_SECRETS_PATH):
                # Try to find it in the old location
                old_path = '../env/google_calendar.json'
                if os.path.exists(old_path):
                    # Copy the file to the new location
                    import shutil
                    shutil.copy(old_path, CLIENT_SECRETS_PATH)
                    print(f"Copied client secrets from {old_path} to {CLIENT_SECRETS_PATH}")
                else:
                    raise FileNotFoundError(
                        f"Client secrets file not found at {CLIENT_SECRETS_PATH}. "
                        f"Please place your Google Calendar API credentials in this file.")
            
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials in the user's token file
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            print(f"Saved token for {'default user' if not username else username} to {token_path}")

    service = build('calendar', 'v3', credentials=creds)
    return service


def create_event(service, summary, location, description, start_time, end_time):
    """Creates a calendar event.
    
    Args:
        service: Google Calendar API service instance
        summary: Title of the event
        location: Location of the event
        description: Description of the event
        start_time: Start time of the event (datetime object)
        end_time: End time of the event (datetime object)
        
    Returns:
        The created event object
    """
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


def create_events(events_data, username=None):
    """Creates multiple calendar events from a list of event data.
    
    Args:
        events_data: List of event dictionaries or JSON string containing event data
            Each event should have:
            - summary: Title of the event
            - description: Description of the event
            - start_date: Start date in format 'YYYY-MM-DD' or 'MM-DD'
            - end_date: End date in format 'YYYY-MM-DD' or 'MM-DD' (optional)
            - location: Location of the event (optional)
        username (str, optional): Username to create events for. If None, uses a default token.
    
    Returns:
        List of created event objects
    """
    # Parse events_data if it's a JSON string
    if isinstance(events_data, str):
        try:
            events_data = json.loads(events_data)
        except json.JSONDecodeError:
            print("Error: events_data is not a valid JSON string")
            return []
    
    # Get calendar service for this user
    try:
        service = get_calendar_service(username)
    except Exception as e:
        print(f"Error getting calendar service for user {username or 'default'}: {str(e)}")
        return []
    
    created_events = []
    
    # Process each event
    for event_data in events_data:
        try:
            summary = event_data.get('summary', 'Untitled Event')
            description = event_data.get('description', '')
            location = event_data.get('location', '')
            
            # Parse start date
            start_date_str = event_data.get('start_date')
            if not start_date_str:
                print(f"Skipping event '{summary}': No start date provided")
                continue
            
            # Parse end date (use start date if not provided)
            end_date_str = event_data.get('end_date', start_date_str)
            
            # Convert dates to datetime objects
            try:
                # Try to parse as 'YYYY-MM-DD'
                start_time = datetime.datetime.fromisoformat(start_date_str)
                end_time = datetime.datetime.fromisoformat(end_date_str)
            except ValueError:
                try:
                    # Try to parse as 'MM-DD'
                    start_time, _ = convert_md_to_datetime_range(start_date_str)
                    end_time, _ = convert_md_to_datetime_range(end_date_str)
                    # Set end time to end of day
                    end_time = end_time.replace(hour=23, minute=59, second=59)
                except ValueError as e:
                    print(f"Skipping event '{summary}': {str(e)}")
                    continue
            
            # Create the event
            created_event = create_event(
                service=service,
                summary=summary,
                location=location,
                description=description,
                start_time=start_time,
                end_time=end_time
            )
            
            created_events.append(created_event)
            
        except Exception as e:
            print(f"Error creating event '{event_data.get('summary', 'Unknown')}': {str(e)}")
    
    return created_events


def convert_md_to_datetime_range(date_str):
    """Converts a date string in format 'm.d' to a datetime range.
    
    Args:
        date_str: Date string in format 'm.d'
        
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
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
    service = get_calendar_service("test_user")

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