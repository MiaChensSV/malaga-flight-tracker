"""Google Calendar integration to find available apartment windows."""

import json
import os
from datetime import date, datetime, timedelta, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
MIN_WINDOW_DAYS = 5


def _get_calendar_service():
    """Build a Google Calendar API service using a service account."""
    creds_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    creds_info = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_info, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=credentials)


def _get_booked_dates(
    service, calendar_id: str, start: date, end: date
) -> set[date]:
    """Return the set of dates that have events (= booked) in the given range."""
    time_min = datetime(start.year, start.month, start.day, tzinfo=timezone.utc).isoformat()
    time_max = datetime(end.year, end.month, end.day, tzinfo=timezone.utc).isoformat()

    booked = set()
    page_token = None

    while True:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token,
        ).execute()

        for event in events_result.get("items", []):
            event_start = event["start"].get("date") or event["start"].get("dateTime", "")[:10]
            event_end = event["end"].get("date") or event["end"].get("dateTime", "")[:10]
            s = date.fromisoformat(event_start)
            e = date.fromisoformat(event_end)
            current = s
            while current < e:
                booked.add(current)
                current += timedelta(days=1)

        page_token = events_result.get("nextPageToken")
        if not page_token:
            break

    return booked


def _find_available_windows(
    booked_dates: set[date], start: date, end: date, min_days: int = MIN_WINDOW_DAYS
) -> list[tuple[date, date]]:
    """Find consecutive available windows of at least min_days."""
    windows = []
    current = start
    window_start = None

    while current <= end:
        if current not in booked_dates:
            if window_start is None:
                window_start = current
        else:
            if window_start is not None:
                length = (current - window_start).days
                if length >= min_days:
                    windows.append((window_start, current - timedelta(days=1)))
                window_start = None
        current += timedelta(days=1)

    # Close any trailing window
    if window_start is not None:
        length = (end - window_start).days + 1
        if length >= min_days:
            windows.append((window_start, end))

    return windows


def get_available_windows(
    apartments: list[dict], look_ahead_days: int
) -> list[dict]:
    """Check all apartment calendars and return available windows.

    Returns a list of dicts:
        {
            "apartment_id": ...,
            "apartment_name": ...,
            "window_start": date,
            "window_end": date,
        }
    """
    service = _get_calendar_service()
    today = date.today()
    end_date = today + timedelta(days=look_ahead_days)

    results = []
    for apt in apartments:
        calendar_id = apt["google_calendar_id"]
        booked = _get_booked_dates(service, calendar_id, today, end_date)
        windows = _find_available_windows(booked, today, end_date)
        for w_start, w_end in windows:
            results.append(
                {
                    "apartment_id": apt["id"],
                    "apartment_name": apt["name"],
                    "window_start": w_start,
                    "window_end": w_end,
                }
            )

    return results
