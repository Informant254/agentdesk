"""Google Calendar MCP Server - Connect AI agents to Google Calendar."""

from datetime import datetime
from typing import Any

import httpx
from fastmcp import FastMCP

from backend.config import settings

google_calendar_server = FastMCP(
    "Google Calendar",
    description="Connect AI agents to Google Calendar for scheduling trades jobs",
)

GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


async def _get_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}


@google_calendar_server.tool()
async def list_calendars(access_token: str) -> list[dict[str, Any]]:
    """List all calendars accessible to the authenticated user."""
    headers = await _get_headers(access_token)
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GOOGLE_CALENDAR_API}/users/me/calendarList", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return [
            {"id": cal["id"], "summary": cal["summary"], "primary": cal.get("primary", False)}
            for cal in data.get("items", [])
        ]


@google_calendar_server.tool()
async def get_events(
    access_token: str,
    calendar_id: str = "primary",
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """Get upcoming events from a calendar."""
    headers = await _get_headers(access_token)
    params: dict[str, Any] = {"maxResults": max_results, "singleEvents": True, "orderBy": "startTime"}
    if time_min:
        params["timeMin"] = time_min
    else:
        params["timeMin"] = datetime.utcnow().isoformat() + "Z"
    if time_max:
        params["timeMax"] = time_max

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "id": event["id"],
                "summary": event.get("summary", "No title"),
                "start": event["start"].get("dateTime", event["start"].get("date")),
                "end": event["end"].get("dateTime", event["end"].get("date")),
                "location": event.get("location"),
                "description": event.get("description"),
                "status": event.get("status"),
            }
            for event in data.get("items", [])
        ]


@google_calendar_server.tool()
async def create_event(
    access_token: str,
    summary: str,
    start_datetime: str,
    end_datetime: str,
    calendar_id: str = "primary",
    description: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Create a new calendar event (book a job)."""
    headers = await _get_headers(access_token)
    body: dict[str, Any] = {
        "summary": summary,
        "start": {"dateTime": start_datetime, "timeZone": "America/New_York"},
        "end": {"dateTime": end_datetime, "timeZone": "America/New_York"},
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        event = resp.json()
        return {
            "id": event["id"],
            "summary": event.get("summary"),
            "start": event["start"].get("dateTime"),
            "end": event["end"].get("dateTime"),
            "htmlLink": event.get("htmlLink"),
        }


@google_calendar_server.tool()
async def update_event(
    access_token: str,
    event_id: str,
    calendar_id: str = "primary",
    summary: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    description: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Update an existing calendar event (reschedule a job)."""
    headers = await _get_headers(access_token)
    body: dict[str, Any] = {}
    if summary:
        body["summary"] = summary
    if start_datetime:
        body["start"] = {"dateTime": start_datetime, "timeZone": "America/New_York"}
    if end_datetime:
        body["end"] = {"dateTime": end_datetime, "timeZone": "America/New_York"}
    if description:
        body["description"] = description
    if location:
        body["location"] = location

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        event = resp.json()
        return {
            "id": event["id"],
            "summary": event.get("summary"),
            "start": event["start"].get("dateTime"),
            "end": event["end"].get("dateTime"),
        }


@google_calendar_server.tool()
async def delete_event(
    access_token: str,
    event_id: str,
    calendar_id: str = "primary",
) -> bool:
    """Delete a calendar event (cancel a job)."""
    headers = await _get_headers(access_token)
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
            headers=headers,
        )
        return resp.status_code == 204


@google_calendar_server.resource("calendar://status")
async def calendar_status() -> str:
    """Check Google Calendar API connection status."""
    return "Google Calendar MCP server is running. Connect with an access_token to manage events."


if __name__ == "__main__":
    google_calendar_server.run()
