"""Google Maps MCP Server - Connect AI agents to Google Maps for route optimization."""

from typing import Any

import httpx
from fastmcp import FastMCP

from backend.config import settings

google_maps_server = FastMCP(
    "Google Maps",
    description="Connect AI agents to Google Maps for location and route data",
)

GOOGLE_MAPS_API = "https://maps.googleapis.com/maps/api"


@google_maps_server.tool()
async def geocode_address(address: str, api_key: str) -> dict[str, Any]:
    """Convert an address to latitude/longitude coordinates."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GOOGLE_MAPS_API}/geocode/json",
            params={"address": address, "key": api_key},
        )
        resp.raise_for_status()
        data = resp.json()
        if data["status"] != "OK":
            return {"error": f"Geocoding failed: {data['status']}"}
        result = data["results"][0]
        return {
            "formatted_address": result["formatted_address"],
            "lat": result["geometry"]["location"]["lat"],
            "lng": result["geometry"]["location"]["lng"],
            "place_id": result["place_id"],
        }


@google_maps_server.tool()
async def calculate_route(
    origin: str,
    destination: str,
    api_key: str,
    departure_time: str | None = None,
) -> dict[str, Any]:
    """Calculate driving route between two locations with distance and duration."""
    params: dict[str, Any] = {
        "origin": origin,
        "destination": destination,
        "mode": "driving",
        "key": api_key,
    }
    if departure_time:
        params["departure_time"] = departure_time

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GOOGLE_MAPS_API}/directions/json",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()
        if data["status"] != "OK":
            return {"error": f"Directions failed: {data['status']}"}
        route = data["routes"][0]["legs"][0]
        return {
            "distance": route["distance"]["text"],
            "distance_meters": route["distance"]["value"],
            "duration": route["duration"]["text"],
            "duration_seconds": route["duration"]["value"],
            "start_address": route["start_address"],
            "end_address": route["end_address"],
            "steps": [
                {
                    "instruction": step["html_instructions"],
                    "distance": step["distance"]["text"],
                    "duration": step["duration"]["text"],
                }
                for step in route["steps"]
            ],
        }


@google_maps_server.tool()
async def optimize_route(
    origin: str,
    destinations: list[str],
    api_key: str,
) -> dict[str, Any]:
    """Optimize a multi-stop route for a field technician visiting multiple job sites."""
    destination_str = "|".join(destinations)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GOOGLE_MAPS_API}/directions/json",
            params={
                "origin": origin,
                "destination": destinations[-1],
                "waypoints": f"optimize:true|{'|'.join(destinations[:-1])}",
                "mode": "driving",
                "key": api_key,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data["status"] != "OK":
            return {"error": f"Route optimization failed: {data['status']}"}
        route = data["routes"][0]
        waypoint_order = route.get("waypoint_order", [])
        legs = route["legs"]
        return {
            "optimized_order": waypoint_order,
            "total_distance": sum(leg["distance"]["value"] for leg in legs),
            "total_duration": sum(leg["duration"]["value"] for leg in legs),
            "stops": [
                {
                    "order": i,
                    "address": legs[i]["end_address"],
                    "distance": legs[i]["distance"]["text"],
                    "duration": legs[i]["duration"]["text"],
                }
                for i in range(len(legs))
            ],
        }


@google_maps_server.resource("maps://status")
async def maps_status() -> str:
    """Check Google Maps API connection status."""
    return "Google Maps MCP server is running. Provide an API key for each tool call."


if __name__ == "__main__":
    google_maps_server.run()
