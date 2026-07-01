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


async def get_all_jobs(user_id: str) -> list[dict[str, Any]]:
    """Fetch all jobs for a user, ordered by scheduled time descending."""
    supabase = get_db()
    result = supabase.table("jobs") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("scheduled_at", desc=True) \
        .execute()
    return result.data


async def create_job(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Insert a new job row and return the created record."""
    supabase = get_db()
    payload = {**data, "user_id": user_id}
    result = supabase.table("jobs").insert(payload).execute()
    return result.data[0] if result.data else {}


async def get_invoices(user_id: str) -> list[dict[str, Any]]:
    """Fetch all invoices for a user, ordered by due_date descending."""
    supabase = get_db()
    result = supabase.table("invoices") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("due_date", desc=True) \
        .execute()
    return result.data


async def create_invoice_record(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Insert a new invoice row and return the created record."""
    supabase = get_db()
    payload = {**data, "user_id": user_id}
    result = supabase.table("invoices").insert(payload).execute()
    return result.data[0] if result.data else {}


async def update_job_coords(job_id: str, lat: float, lng: float):
    """Update a job's geocoded coordinates."""
    supabase = get_db()
    supabase.table("jobs") \
        .update({"address_lat": lat, "address_lng": lng}) \
        .eq("id", job_id) \
        .execute()
