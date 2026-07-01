"""Route Map API — structured route data for the Live Map frontend.

Uses free, keyless services instead of Google Maps (which requires billing
even on the free tier):
  - Geocoding: Nominatim (OpenStreetMap)
  - Routing / trip optimization: OSRM public server

OSRM's default polyline encoding matches Google's Encoded Polyline Algorithm
Format, so the frontend's existing polyline decoder needs no changes.
"""

import asyncio
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.db import get_jobs_for_date, update_job_coords
from backend.security.auth import auth_manager

router = APIRouter(prefix="/api/workflows", tags=["route-map"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org"
_HEADERS = {"User-Agent": "AgentDesk-TradesAI/1.0 (https://github.com/Informant254/agentdesk)"}

# Nominatim's usage policy caps public-server use at ~1 request/second.
_NOMINATIM_DELAY_SECONDS = 1.1


async def _geocode(address: str) -> dict[str, Any] | None:
    """Geocode a single address via Nominatim."""
    async with httpx.AsyncClient(headers=_HEADERS, timeout=15) as client:
        resp = await client.get(
            NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1},
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None
        return {"lat": float(results[0]["lat"]), "lng": float(results[0]["lon"])}


def _fmt_km(meters: float) -> str:
    return f"{meters / 1000:.1f} km"


def _fmt_min(seconds: float) -> str:
    return f"{seconds / 60:.0f} min"


async def _osrm_trip(
    points: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Optimize visiting order for a list of stops (source fixed at first,
    destination fixed at last, middle stops reordered for shortest trip).

    points: list of {"lat": ..., "lng": ..., "label": ...}, in original order.
    Returns polyline, legs, totals, and the optimized point order.
    """
    if len(points) < 2:
        return None

    coord_str = ";".join(f"{p['lng']},{p['lat']}" for p in points)
    url = f"{OSRM_URL}/trip/v1/driving/{coord_str}"

    async with httpx.AsyncClient(headers=_HEADERS, timeout=20) as client:
        resp = await client.get(
            url,
            params={
                "source": "first",
                "destination": "last",
                "roundtrip": "false",
                "overview": "full",
                "geometries": "polyline",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != "Ok":
        return None

    trip = data["trips"][0]
    # data["waypoints"] is parallel to input `points`; each has waypoint_index
    # telling us that point's position in the optimized visiting order.
    order = sorted(range(len(points)), key=lambda i: data["waypoints"][i]["waypoint_index"])
    ordered_points = [points[i] for i in order]

    legs = [
        {
            "distance_m": leg["distance"],
            "distance_text": _fmt_km(leg["distance"]),
            "duration_s": leg["duration"],
            "duration_text": _fmt_min(leg["duration"]),
            "start_address": ordered_points[i]["label"],
            "end_address": ordered_points[i + 1]["label"],
            "start_lat": ordered_points[i]["lat"],
            "start_lng": ordered_points[i]["lng"],
            "end_lat": ordered_points[i + 1]["lat"],
            "end_lng": ordered_points[i + 1]["lng"],
        }
        for i, leg in enumerate(trip["legs"])
    ]

    return {
        "polyline": trip["geometry"],
        "legs": legs,
        "total_distance_m": trip["distance"],
        "total_duration_s": trip["duration"],
        "order": order,  # indices into the ORIGINAL `points` list
    }


async def _osrm_route(points: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Route through stops in the EXACT given order (no reordering)."""
    if len(points) < 2:
        return None

    coord_str = ";".join(f"{p['lng']},{p['lat']}" for p in points)
    url = f"{OSRM_URL}/route/v1/driving/{coord_str}"

    async with httpx.AsyncClient(headers=_HEADERS, timeout=20) as client:
        resp = await client.get(url, params={"overview": "full", "geometries": "polyline"})
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != "Ok":
        return None

    route = data["routes"][0]
    legs = [
        {
            "distance_m": leg["distance"],
            "distance_text": _fmt_km(leg["distance"]),
            "duration_s": leg["duration"],
            "duration_text": _fmt_min(leg["duration"]),
            "start_address": points[i]["label"],
            "end_address": points[i + 1]["label"],
            "start_lat": points[i]["lat"],
            "start_lng": points[i]["lng"],
            "end_lat": points[i + 1]["lat"],
            "end_lng": points[i + 1]["lng"],
        }
        for i, leg in enumerate(route["legs"])
    ]

    return {
        "polyline": route["geometry"],
        "legs": legs,
        "total_distance_m": route["distance"],
        "total_duration_s": route["duration"],
    }


async def _ensure_geocoded(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fill in lat/lng for any jobs missing coordinates, caching results to the DB."""
    geocoded_jobs = []
    for job in jobs:
        lat = job.get("address_lat")
        lng = job.get("address_lng")
        address = job.get("address", "")

        if (lat is None or lng is None) and address:
            result = await _geocode(address)
            await asyncio.sleep(_NOMINATIM_DELAY_SECONDS)
            if result:
                lat, lng = result["lat"], result["lng"]
                try:
                    await update_job_coords(job["id"], lat, lng)
                except Exception:
                    pass

        geocoded_jobs.append({
            "id": job["id"],
            "title": job.get("title", ""),
            "client_name": job.get("client_name", ""),
            "address": address,
            "status": job.get("status", "scheduled"),
            "scheduled_at": job.get("scheduled_at", ""),
            "estimated_duration_minutes": job.get("estimated_duration_minutes", 60),
            "lat": lat,
            "lng": lng,
        })
    return geocoded_jobs


@router.get("/route-map/{date}")
async def get_route_map(
    date: str,
    starting_location: str = Query(default="", description="Starting location for the day"),
    token: dict = Depends(auth_manager.verify_token),
):
    """
    Get structured route map data for a given date.

    Returns jobs with geocoded coordinates, optimized route order,
    polyline data, and total distance/duration. Uses free OSM-based
    services (Nominatim + OSRM) — no API key required.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = token.get("sub", "")

    jobs = await get_jobs_for_date(user_id, date)
    if not jobs:
        return {"success": True, "jobs": [], "route": None, "total_jobs": 0}

    try:
        geocoded_jobs = await _ensure_geocoded(jobs)
    except Exception as e:
        return {
            "success": False,
            "error": f"Geocoding failed: {e}",
            "jobs": [],
            "route": None,
        }

    valid_jobs = [j for j in geocoded_jobs if j.get("lat") is not None]
    if not valid_jobs:
        return {
            "success": True,
            "jobs": geocoded_jobs,
            "route": None,
            "note": "Could not geocode any job addresses — route optimization unavailable",
        }

    points = [{"lat": j["lat"], "lng": j["lng"], "label": j["address"]} for j in valid_jobs]
    origin_label = None

    if starting_location:
        origin_geo = await _geocode(starting_location)
        if origin_geo:
            points = [{"lat": origin_geo["lat"], "lng": origin_geo["lng"], "label": starting_location}] + points
            origin_label = starting_location

    if len(points) < 2:
        return {
            "success": True,
            "jobs": geocoded_jobs,
            "route": None,
            "note": "Need at least 2 stops to build a route",
        }

    try:
        trip = await _osrm_trip(points)
    except Exception as e:
        return {
            "success": True,
            "jobs": geocoded_jobs,
            "route": None,
            "note": f"Route optimization failed: {e}",
        }

    if trip is None:
        return {
            "success": True,
            "jobs": geocoded_jobs,
            "route": None,
            "note": "Route optimization failed — check addresses for accuracy",
        }

    # Map optimized point order back to job order (drop the synthetic origin point, if any)
    job_index_offset = 1 if origin_label else 0
    ordered_job_indices = [i - job_index_offset for i in trip["order"] if i >= job_index_offset]
    ordered_jobs = [valid_jobs[i] for i in ordered_job_indices]

    return {
        "success": True,
        "starting_location": origin_label or (valid_jobs[0]["address"] if valid_jobs else ""),
        "jobs": geocoded_jobs,
        "optimized_order": ordered_jobs,
        "route": {
            "polyline": trip["polyline"],
            "legs": trip["legs"],
            "total_distance_m": trip["total_distance_m"],
            "total_distance_km": round(trip["total_distance_m"] / 1000, 1),
            "total_duration_s": trip["total_duration_s"],
            "total_duration_min": round(trip["total_duration_s"] / 60, 1),
        },
        "total_jobs": len(geocoded_jobs),
    }


@router.post("/route-map/reorder")
async def reorder_route(
    date: str = Query(..., description="Date string YYYY-MM-DD"),
    job_order: list[str] = Query(..., description="Job IDs in new order"),
    starting_location: str = Query(default="", description="Starting location"),
    token: dict = Depends(auth_manager.verify_token),
):
    """Recalculate route after drag-and-drop reorder (no re-optimization — exact order given)."""
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = token.get("sub", "")

    jobs = await get_jobs_for_date(user_id, date)
    job_map = {j["id"]: j for j in jobs}
    ordered = [job_map[jid] for jid in job_order if jid in job_map]
    if not ordered:
        raise HTTPException(status_code=400, detail="No valid jobs found")

    try:
        geocoded = await _ensure_geocoded(ordered)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Geocoding failed: {e}")

    valid = [j for j in geocoded if j.get("lat") is not None]
    if len(valid) < 2:
        return {"success": True, "route": None, "note": "Need at least 2 geocoded jobs"}

    points = [{"lat": j["lat"], "lng": j["lng"], "label": j["address"]} for j in valid]
    if starting_location:
        origin_geo = await _geocode(starting_location)
        if origin_geo:
            points = [{"lat": origin_geo["lat"], "lng": origin_geo["lng"], "label": starting_location}] + points

    try:
        route = await _osrm_route(points)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Route recalculation failed: {e}")

    if not route:
        raise HTTPException(status_code=502, detail="Route recalculation failed")

    return {
        "success": True,
        "route": {
            "polyline": route["polyline"],
            "legs": route["legs"],
            "total_distance_m": route["total_distance_m"],
            "total_distance_km": round(route["total_distance_m"] / 1000, 1),
            "total_duration_s": route["total_duration_s"],
            "total_duration_min": round(route["total_duration_s"] / 60, 1),
        },
    }
