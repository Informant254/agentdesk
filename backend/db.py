"""Supabase database client for direct DB operations."""

from typing import Any

from supabase import create_client, Client

from backend.config import settings

_supabase: Client | None = None


def get_db() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase


async def get_jobs_for_date(user_id: str, date: str) -> list[dict[str, Any]]:
    """Fetch all jobs scheduled for a given date."""
    supabase = get_db()
    result = supabase.table("jobs") \
        .select("*") \
        .eq("user_id", user_id) \
        .gte("scheduled_at", f"{date}T00:00:00Z") \
        .lte("scheduled_at", f"{date}T23:59:59Z") \
        .order("scheduled_at") \
        .execute()
    return result.data


async def update_job_coords(job_id: str, lat: float, lng: float):
    """Update a job's geocoded coordinates."""
    supabase = get_db()
    supabase.table("jobs") \
        .update({"address_lat": lat, "address_lng": lng}) \
        .eq("id", job_id) \
        .execute()
