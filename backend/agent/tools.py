"""MCP tools integration for the agent.

This module connects MCP server tools to the LangGraph agent.
"""

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


# Schemas for tools


class ListEventsInput(BaseModel):
    access_token: str = Field(description="Google OAuth access token")
    calendar_id: str = Field(default="primary", description="Calendar ID")
    max_results: int = Field(default=20, description="Max events to return")


class CreateEventInput(BaseModel):
    access_token: str = Field(description="Google OAuth access token")
    summary: str = Field(description="Event title (job name)")
    start_datetime: str = Field(description="Start time in ISO format")
    end_datetime: str = Field(description="End time in ISO format")
    calendar_id: str = Field(default="primary")
    description: str | None = Field(default=None, description="Job notes")
    location: str | None = Field(default=None, description="Job site address")


class ListJobsInput(BaseModel):
    api_key: str | None = Field(default=None, description="Jobber API key")
    status: str | None = Field(default=None, description="Filter by status")
    limit: int = Field(default=20, description="Max jobs to return")


class CreateJobInput(BaseModel):
    client_id: str = Field(description="Jobber client ID")
    title: str = Field(description="Job title")
    scheduled_at: str = Field(description="Scheduled time in ISO format")
    description: str | None = Field(default=None)
    api_key: str | None = Field(default=None)


class CreateInvoiceInput(BaseModel):
    job_id: str = Field(description="Jobber job ID")
    line_items: list[dict[str, Any]] = Field(description="Invoice line items")
    api_key: str | None = Field(default=None)


class OptimizeRouteInput(BaseModel):
    origin: str = Field(description="Starting location")
    destinations: list[str] = Field(description="List of job site addresses")
    api_key: str = Field(description="Google Maps API key")


class GeocodeInput(BaseModel):
    address: str = Field(description="Address to geocode")
    api_key: str = Field(description="Google Maps API key")


class CalculateRouteInput(BaseModel):
    origin: str = Field(description="Starting location")
    destination: str = Field(description="Ending location")
    api_key: str = Field(description="Google Maps API key")


# Tool wrappers that call MCP servers


async def _list_events(access_token: str, calendar_id: str = "primary", max_results: int = 20) -> str:
    from backend.mcp_servers.google_calendar import google_calendar_server
    # Call the MCP server tool directly
    result = await google_calendar_server.call_tool(
        "get_events",
        {"access_token": access_token, "calendar_id": calendar_id, "max_results": max_results},
    )
    return str(result)


async def _create_event(
    access_token: str,
    summary: str,
    start_datetime: str,
    end_datetime: str,
    calendar_id: str = "primary",
    description: str | None = None,
    location: str | None = None,
) -> str:
    from backend.mcp_servers.google_calendar import google_calendar_server
    result = await google_calendar_server.call_tool(
        "create_event",
        {
            "access_token": access_token,
            "summary": summary,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "calendar_id": calendar_id,
            "description": description,
            "location": location,
        },
    )
    return str(result)


async def _list_jobs(api_key: str | None = None, status: str | None = None, limit: int = 20) -> str:
    from backend.mcp_servers.jobber import jobber_server
    kwargs: dict[str, Any] = {"limit": limit}
    if api_key:
        kwargs["api_key"] = api_key
    if status:
        kwargs["status"] = status
    result = await jobber_server.call_tool("list_jobs", kwargs)
    return str(result)


async def _create_job(
    client_id: str,
    title: str,
    scheduled_at: str,
    description: str | None = None,
    api_key: str | None = None,
) -> str:
    from backend.mcp_servers.jobber import jobber_server
    kwargs: dict[str, Any] = {
        "client_id": client_id,
        "title": title,
        "scheduled_at": scheduled_at,
    }
    if description:
        kwargs["description"] = description
    if api_key:
        kwargs["api_key"] = api_key
    result = await jobber_server.call_tool("create_job", kwargs)
    return str(result)


async def _create_invoice(job_id: str, line_items: list[dict[str, Any]], api_key: str | None = None) -> str:
    from backend.mcp_servers.jobber import jobber_server
    kwargs: dict[str, Any] = {"job_id": job_id, "line_items": line_items}
    if api_key:
        kwargs["api_key"] = api_key
    result = await jobber_server.call_tool("create_invoice", kwargs)
    return str(result)


async def _optimize_route(origin: str, destinations: list[str], api_key: str) -> str:
    from backend.mcp_servers.google_maps import google_maps_server
    result = await google_maps_server.call_tool(
        "optimize_route",
        {"origin": origin, "destinations": destinations, "api_key": api_key},
    )
    return str(result)


async def _geocode(address: str, api_key: str) -> str:
    from backend.mcp_servers.google_maps import google_maps_server
    result = await google_maps_server.call_tool(
        "geocode_address",
        {"address": address, "api_key": api_key},
    )
    return str(result)


async def _calculate_route(origin: str, destination: str, api_key: str) -> str:
    from backend.mcp_servers.google_maps import google_maps_server
    result = await google_maps_server.call_tool(
        "calculate_route",
        {"origin": origin, "destination": destination, "api_key": api_key},
    )
    return str(result)


# LangChain-compatible tools


def get_all_tools() -> list[StructuredTool]:
    """Get all tools available to the agent."""
    return (
        get_scheduling_tools()
        + get_booking_tools()
        + get_dispatch_tools()
        + get_invoicing_tools()
        + get_route_tools()
        + get_followup_tools()
    )


def get_scheduling_tools() -> list[StructuredTool]:
    """Tools for the scheduling sub-agent."""
    return [
        StructuredTool(
            name="list_calendar_events",
            description="List upcoming events from Google Calendar for a trades business",
            func=_list_events,
            args_schema=ListEventsInput,
        ),
        StructuredTool(
            name="create_calendar_event",
            description="Create a new calendar event (book a job) in Google Calendar",
            func=_create_event,
            args_schema=CreateEventInput,
        ),
    ]


def get_booking_tools() -> list[StructuredTool]:
    """Tools for the booking sub-agent."""
    return [
        StructuredTool(
            name="list_calendar_events",
            description="List upcoming events from Google Calendar for a trades business",
            func=_list_events,
            args_schema=ListEventsInput,
        ),
        StructuredTool(
            name="create_calendar_event",
            description="Create a new calendar event (book a job) in Google Calendar",
            func=_create_event,
            args_schema=CreateEventInput,
        ),
        StructuredTool(
            name="list_jobs",
            description="List jobs from Jobber, optionally filtered by status",
            func=_list_jobs,
            args_schema=ListJobsInput,
        ),
        StructuredTool(
            name="create_job",
            description="Create a new job in Jobber for a client",
            func=_create_job,
            args_schema=CreateJobInput,
        ),
    ]


def get_dispatch_tools() -> list[StructuredTool]:
    """Tools for the dispatch sub-agent."""
    return [
        StructuredTool(
            name="list_jobs",
            description="List jobs from Jobber, optionally filtered by status",
            func=_list_jobs,
            args_schema=ListJobsInput,
        ),
        StructuredTool(
            name="create_job",
            description="Create a new job in Jobber for a client",
            func=_create_job,
            args_schema=CreateJobInput,
        ),
        StructuredTool(
            name="list_calendar_events",
            description="List upcoming events from Google Calendar for a trades business",
            func=_list_events,
            args_schema=ListEventsInput,
        ),
    ]


def get_invoicing_tools() -> list[StructuredTool]:
    """Tools for the invoicing sub-agent."""
    return [
        StructuredTool(
            name="create_invoice",
            description="Create an invoice from a Jobber job with line items",
            func=_create_invoice,
            args_schema=CreateInvoiceInput,
        ),
        StructuredTool(
            name="list_jobs",
            description="List jobs from Jobber, optionally filtered by status",
            func=_list_jobs,
            args_schema=ListJobsInput,
        ),
    ]


def get_route_tools() -> list[StructuredTool]:
    """Tools for the route optimization sub-agent."""
    return [
        StructuredTool(
            name="optimize_route",
            description="Optimize a multi-stop route for field technicians",
            func=_optimize_route,
            args_schema=OptimizeRouteInput,
        ),
        StructuredTool(
            name="geocode_address",
            description="Convert an address to coordinates",
            func=_geocode,
            args_schema=GeocodeInput,
        ),
        StructuredTool(
            name="calculate_route",
            description="Calculate driving route between two locations",
            func=_calculate_route,
            args_schema=CalculateRouteInput,
        ),
    ]


def get_followup_tools() -> list[StructuredTool]:
    """Tools for the customer follow-up sub-agent."""
    return [
        StructuredTool(
            name="list_jobs",
            description="List jobs from Jobber, optionally filtered by status",
            func=_list_jobs,
            args_schema=ListJobsInput,
        ),
        StructuredTool(
            name="list_calendar_events",
            description="List upcoming events from Google Calendar for a trades business",
            func=_list_events,
            args_schema=ListEventsInput,
        ),
    ]
