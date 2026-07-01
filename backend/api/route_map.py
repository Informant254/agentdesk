"""Route Map API — structured route data for the Live Map frontend."""

import asyncio
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config import settings
from backend.db import get_jobs_for_date, update_job_coords
from backend.security.auth import auth_manager

router = APIRouter(prefix="/api/workflows", tags=["route-map"])

GOOGLE_MAPS_API = "https://maps.googleapis.com/maps/api"


async def _geocode(address: str, api_key: str) -> dict[str, Any] | None:
    """Geocode a single address."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GOOGLE_MAPS_API}/geocode/json",
            params={"address": address, "key": api_key},
        )
        resp.raise_for_status()
        data = resp.json()
        if data["status"] != "OK":
            return None
        loc = data["results"][0]["geometry"]["location"]
        return {"lat": loc["lat"], "lng": loc["lng"]}


async def _get_route_polyline(
    origin: str,
    destination: str,
    waypoints: list[str],
    api_key: str,
) -> dict[str, Any] | None:
    """Get the route polyline and leg data from Google Maps."""
    if not waypoints:
        params: dict[str, Any] = {
            "origin": origin,
            "destination": destination,
            "mode": "driving",
            "key": api_key,
        }
    else:
        params = {
            "origin": origin,
            "destination": destination,
            "waypoints": f"optimize:true|{'|'.join(waypoints)}",
            "mode": "driving",
            "key": api_key,
        }

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GOOGLE_MAPS_API}/directions/json", params=params)
        resp.raise_for_status()
        data = resp.json()
        if data["status"] != "OK":
            return None

        route = data["routes"][0]
        waypoint_order = route.get("waypoint_order", [])
        legs = route["legs"]
        polyline = route["overview_polyline"]["points"]

        return {
            "polyline": polyline,
            "waypoint_order": waypoint_order,
            "legs": [
                {
                    "distance_m": leg["distance"]["value"],
                    "distance_text": leg["distance"]["text"],
                    "duration_s": leg["duration"]["value"],
                    "duration_text": leg["duration"]["text"],
                    "start_address": leg["start_address"],
                    "end_address": leg["end_address"],
                    "start_lat": leg["start_location"]["lat"],
                    "start_lng": leg["start_location"]["lng"],
                    "end_lat": leg["end_location"]["lat"],
                    "end_lng": leg["end_location"]["lng"],
                }
                for leg in legs
            ],
            "total_distance_m": sum(leg["distance"]["value"] for leg in legs),
            "total_duration_s": sum(leg["duration"]["value"] for leg in legs),
        }


@router.get("/route-map/{date}")
async def get_route_map(
    date: str,
    starting_location: str = Query(default="", description="Starting location for the day"),
    token: dict = Depends(auth_manager.verify_token),
):
    """Get structured route map data for a given date.

    Returns jobs with geocoded coordinates, optimized route order,
    polyline data, and total distance/duration.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = token.get("sub", "")

    api_key = settings.google_maps_api_key
    if not api_key:
        return {
            "success": False,
            "error": "Google Maps API key not configured. Set GOOGLE_MAPS_API_KEY in .env",
            "jobs": [],
            "route": None,
        }

    jobs = await get_jobs_for_date(user_id, date)
    if not jobs:
        return {
            "success": True,
            "jobs": [],
            "route": None,
            "total_jobs": 0,
        }

    geocoded_jobs = []
    coords_ok = True

    for job in jobs:
        lat = job.get("address_lat")
        lng = job.get("address_lng")
        address = job.get("address", "")

        if (lat is None or lng is None) and address:
            result = await _geocode(address, api_key)
            if result:
                lat, lng = result["lat"], result["lng"]
                try:
                    await update_job_coords(job["id"], lat, lng)
                except Exception:
                    pass
            else:
                coords_ok = False

        geocoded_jobs.append({
            "id": job["id"],
            "title": job.get("title", ""),
            "client_name": job.get("client_name", ""),
            "address": job.get("address", ""),
            "status": job.get("status", "scheduled"),
            "scheduled_at": job.get("scheduled_at", ""),
            "estimated_duration_minutes": job.get("estimated_duration_minutes", 60),
            "lat": lat,
            "lng": lng,
        })

    if not coords_ok or not any(j.get("lat") for j in geocoded_jobs):
        return {
            "success": True,
            "jobs": geocoded_jobs,
            "route": None,
            "note": "Some jobs could not be geocoded — route optimization unavailable",
        }

    origin = starting_location or geocoded_jobs[0]["address"]
    addresses = [j["address"] for j in geocoded_jobs if j.get("lat")]

    if len(addresses) < 2:
        return {
            "success": True,
            "jobs": geocoded_jobs,
            "route": None,
            "note": "Need at least 2 jobs to optimize a route",
        }

    route_data = await _get_route_polyline(origin, addresses[-1], addresses[:-1], api_key)

    if route_data is None:
        return {
            "success": True,
            "jobs": geocoded_jobs,
            "route": None,
            "note": "Route optimization failed — check your Google Maps API key and address accuracy",
        }

    optimized_order = route_data["waypoint_order"]
    ordered_jobs = [geocoded_jobs[i] for i in optimized_order] if optimized_order else geocoded_jobs[1:]

    return {
        "success": True,
        "starting_location": origin,
        "jobs": geocoded_jobs,
        "optimized_order": ordered_jobs,
        "route": {
            "polyline": route_data["polyline"],
            "legs": route_data["legs"],
            "total_distance_m": route_data["total_distance_m"],
            "total_distance_km": round(route_data["total_distance_m"] / 1000, 1),
            "total_duration_s": route_data["total_duration_s"],
            "total_duration_min": round(route_data["total_duration_s"] / 60, 1),
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
    """Recalculate route after drag-and-drop reorder."""
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = token.get("sub", "")

    api_key = settings.google_maps_api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="Google Maps API key not configured")

    jobs = await get_jobs_for_date(user_id, date)
    job_map = {j["id"]: j for j in jobs}

    ordered = []
    for jid in job_order:
        if jid in job_map:
            ordered.append(job_map[jid])

    if not ordered:
        raise HTTPException(status_code=400, detail="No valid jobs found")

    addresses = [j.get("address", "") for j in ordered if j.get("address")]
    if len(addresses) < 2:
        return {"success": True, "route": None, "note": "Need at least 2 jobs"}

    origin = starting_location or addresses[0]
    route_data = await _get_route_polyline(origin, addresses[-1], addresses[:-1], api_key)

    if not route_data:
        raise HTTPException(status_code=502, detail="Route recalculation failed")

    return {
        "success": True,
        "route": {
            "polyline": route_data["polyline"],
            "legs": route_data["legs"],
            "total_distance_m": route_data["total_distance_m"],
            "total_distance_km": round(route_data["total_distance_m"] / 1000, 1),
            "total_duration_s": route_data["total_duration_s"],
            "total_duration_min": round(route_data["total_duration_s"] / 60, 1),
        },
    }
