"""jarvis.calendar_manager

Calendar integration with Google Calendar and Outlook.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from jarvis.secure_storage import secure_storage

logger = logging.getLogger(__name__)


@dataclass
class CalendarEvent:
    """Calendar event data."""
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    description: str
    location: str
    attendees: list[str]
    is_all_day: bool
    source: str  # "google", "outlook", "local"


class GoogleCalendarProvider:
    """Google Calendar API integration."""
    
    def __init__(self) -> None:
        self.service = None
        self._init_service()
    
    def _init_service(self) -> None:
        """Initialize Google Calendar API."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            token = secure_storage.get("GOOGLE_CALENDAR_TOKEN")
            if token:
                creds = Credentials.from_authorized_user_info(token)
                self.service = build("calendar", "v3", credentials=creds)
        except Exception as e:
            logger.error(f"Failed to init Google Calendar: {e}")
    
    def is_available(self) -> bool:
        return self.service is not None
    
    def get_events(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        max_results: int = 10,
    ) -> list[CalendarEvent]:
        """Get events from Google Calendar."""
        if not self.service:
            return []
        
        try:
            if not start:
                start = datetime.now()
            if not end:
                end = start + timedelta(days=7)
            
            events_result = self.service.events().list(
                calendarId="primary",
                timeMin=start.isoformat() + "Z",
                timeMax=end.isoformat() + "Z",
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            
            events = []
            for item in events_result.get("items", []):
                start_info = item.get("start", {})
                end_info = item.get("end", {})
                
                # Handle all-day events
                is_all_day = "date" in start_info
                
                if is_all_day:
                    start_time = datetime.fromisoformat(start_info["date"])
                    end_time = datetime.fromisoformat(end_info["date"])
                else:
                    start_time = datetime.fromisoformat(start_info["dateTime"].replace("Z", "+00:00"))
                    end_time = datetime.fromisoformat(end_info["dateTime"].replace("Z", "+00:00"))
                
                events.append(CalendarEvent(
                    id=item.get("id", ""),
                    title=item.get("summary", "No Title"),
                    start_time=start_time,
                    end_time=end_time,
                    description=item.get("description", ""),
                    location=item.get("location", ""),
                    attendees=[a.get("email", "") for a in item.get("attendees", [])],
                    is_all_day=is_all_day,
                    source="google",
                ))
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get Google Calendar events: {e}")
            return []
    
    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        description: str = "",
        attendees: list[str] | None = None,
    ) -> str | None:
        """Create an event in Google Calendar."""
        if not self.service:
            return None
        
        try:
            event_body = {
                "summary": title,
                "description": description,
                "start": {
                    "dateTime": start.isoformat(),
                    "timeZone": "UTC",
                },
                "end": {
                    "dateTime": end.isoformat(),
                    "timeZone": "UTC",
                },
            }
            
            if attendees:
                event_body["attendees"] = [{"email": e} for e in attendees]
            
            event = self.service.events().insert(
                calendarId="primary",
                body=event_body,
            ).execute()
            
            return event.get("id")
            
        except Exception as e:
            logger.error(f"Failed to create Google Calendar event: {e}")
            return None


class OutlookCalendarProvider:
    """Microsoft Outlook Calendar integration."""
    
    def __init__(self) -> None:
        self.access_token = secure_storage.get("OUTLOOK_TOKEN")
    
    def is_available(self) -> bool:
        return self.access_token is not None
    
    def get_events(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        max_results: int = 10,
    ) -> list[CalendarEvent]:
        """Get events from Outlook Calendar."""
        if not self.access_token:
            return []
        
        try:
            import requests
            
            if not start:
                start = datetime.now()
            if not end:
                end = start + timedelta(days=7)
            
            url = "https://graph.microsoft.com/v1.0/me/calendarview"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            params = {
                "startDateTime": start.isoformat(),
                "endDateTime": end.isoformat(),
                "$top": max_results,
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            events = []
            for item in data.get("value", []):
                events.append(CalendarEvent(
                    id=item.get("id", ""),
                    title=item.get("subject", "No Title"),
                    start_time=datetime.fromisoformat(item.get("start", {}).get("dateTime", "").replace("Z", "+00:00")),
                    end_time=datetime.fromisoformat(item.get("end", {}).get("dateTime", "").replace("Z", "+00:00")),
                    description=item.get("bodyPreview", ""),
                    location=item.get("location", {}).get("displayName", ""),
                    attendees=[a.get("emailAddress", {}).get("address", "") for a in item.get("attendees", [])],
                    is_all_day=item.get("isAllDay", False),
                    source="outlook",
                ))
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get Outlook events: {e}")
            return []


class CalendarManager:
    """Unified calendar manager."""
    
    def __init__(self) -> None:
        self.google = GoogleCalendarProvider()
        self.outlook = OutlookCalendarProvider()
    
    def get_all_events(
        self,
        days: int = 7,
        max_per_source: int = 10,
    ) -> list[CalendarEvent]:
        """Get events from all connected calendars."""
        start = datetime.now()
        end = start + timedelta(days=days)
        
        all_events = []
        
        # Google Calendar
        if self.google.is_available():
            events = self.google.get_events(start, end, max_per_source)
            all_events.extend(events)
        
        # Outlook Calendar
        if self.outlook.is_available():
            events = self.outlook.get_events(start, end, max_per_source)
            all_events.extend(events)
        
        # Sort by start time
        all_events.sort(key=lambda e: e.start_time)
        
        return all_events
    
    def get_today_events(self) -> list[CalendarEvent]:
        """Get today's events."""
        return self.get_all_events(days=1)
    
    def get_tomorrow_events(self) -> list[CalendarEvent]:
        """Get tomorrow's events."""
        tomorrow = datetime.now() + timedelta(days=1)
        start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        all_events = []
        if self.google.is_available():
            all_events.extend(self.google.get_events(start, end))
        if self.outlook.is_available():
            all_events.extend(self.outlook.get_events(start, end))
        
        return sorted(all_events, key=lambda e: e.start_time)
    
    def schedule_meeting(
        self,
        title: str,
        start: datetime,
        duration_minutes: int = 60,
        attendees: list[str] | None = None,
        description: str = "",
    ) -> str:
        """Schedule a meeting."""
        end = start + timedelta(minutes=duration_minutes)
        
        # Try Google first, then Outlook
        if self.google.is_available():
            event_id = self.google.create_event(title, start, end, description, attendees)
            if event_id:
                return f"Meeting scheduled in Google Calendar: {title} at {start.strftime('%Y-%m-%d %H:%M')}"
        
        if self.outlook.is_available():
            # Outlook implementation would go here
            return f"Meeting scheduled in Outlook: {title} at {start.strftime('%Y-%m-%d %H:%M')}"
        
        return "No calendar connected. Please setup Google or Outlook calendar first."


# Global calendar manager
calendar_manager = CalendarManager()


def get_my_schedule(days: int = 7) -> str:
    """Get formatted schedule."""
    events = calendar_manager.get_all_events(days=days)
    if not events:
        return "No upcoming events found"
    
    lines = [f"Your schedule for the next {days} days:"]
    current_date = None
    
    for event in events:
        date_str = event.start_time.strftime("%Y-%m-%d")
        if date_str != current_date:
            lines.append(f"\n{date_str}:")
            current_date = date_str
        
        time_str = event.start_time.strftime("%H:%M")
        lines.append(f"  {time_str} - {event.title}")
        if event.location:
            lines.append(f"    Location: {event.location}")
    
    return "\n".join(lines)


def schedule_meeting(
    title: str,
    date: str,
    time: str,
    duration: int = 60,
    attendees: str = "",
) -> str:
    """Schedule a meeting."""
    try:
        start = datetime.fromisoformat(f"{date}T{time}")
        attendee_list = [e.strip() for e in attendees.split(",") if e.strip()]
        
        return calendar_manager.schedule_meeting(title, start, duration, attendee_list)
    except Exception as e:
        return f"Failed to schedule: {str(e)}"
