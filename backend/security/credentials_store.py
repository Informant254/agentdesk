"""Persistent storage for per-user AI provider API keys, backed by Supabase.

Provider keys used to live only in an in-memory dict on the running process.
Render's free tier spins the service down after idle and restarts it on the
next request, which wiped that dict and broke chat/OpenCode auth. This module
persists encrypted keys to a Supabase table so they survive restarts.
"""

import httpx

from backend.config import settings

_TABLE = "provider_keys"


def _headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_key,
        "Authorization": f"Bearer {settings.supabase_key}",
        "Content-Type": "application/json",
    }


def _configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_key)


async def save_key(user_id: str, provider: str, encrypted_key: str) -> bool:
    """Upsert one provider's encrypted key for a user."""
    if not _configured():
        return False
    url = f"{settings.supabase_url}/rest/v1/{_TABLE}"
    payload = {"user_id": user_id, "provider": provider, "encrypted_key": encrypted_key}
    headers = {**_headers(), "Prefer": "resolution=merge-duplicates"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url, json=payload, headers=headers, params={"on_conflict": "user_id,provider"}
            )
            return resp.status_code in (200, 201)
    except Exception:
        return False


async def load_keys(user_id: str) -> dict[str, str]:
    """Return {provider: encrypted_key} for everything saved for this user."""
    if not _configured():
        return {}
    url = f"{settings.supabase_url}/rest/v1/{_TABLE}"
    params = {"user_id": f"eq.{user_id}", "select": "provider,encrypted_key"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=_headers(), params=params)
            if resp.status_code == 200:
                return {row["provider"]: row["encrypted_key"] for row in resp.json()}
    except Exception:
        pass
    return {}


async def delete_key(user_id: str, provider: str) -> bool:
    if not _configured():
        return False
    url = f"{settings.supabase_url}/rest/v1/{_TABLE}"
    params = {"user_id": f"eq.{user_id}", "provider": f"eq.{provider}"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(url, headers=_headers(), params=params)
            return resp.status_code in (200, 204)
    except Exception:
        return False
