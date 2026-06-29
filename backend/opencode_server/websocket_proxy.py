"""WebSocket proxy for connecting browser xterm.js to OpenCode server."""

import asyncio
import json
from typing import Any

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from backend.opencode_server.manager import opencode_manager

router = APIRouter(prefix="/api/opencode", tags=["opencode"])


@router.post("/start")
async def start_opencode_server(
    port: int = 4096,
    hostname: str = "127.0.0.1",
    password: str | None = None,
    working_dir: str | None = None,
):
    """Start the OpenCode server."""
    result = await opencode_manager.start(
        port=port, hostname=hostname, password=password, working_dir=working_dir
    )
    return result


@router.post("/stop")
async def stop_opencode_server():
    """Stop the OpenCode server."""
    stopped = await opencode_manager.stop()
    return {"stopped": stopped}


@router.get("/status")
async def opencode_status():
    """Get OpenCode server status."""
    return await opencode_manager.status()


@router.get("/sessions")
async def list_sessions():
    """List OpenCode sessions via the REST API."""
    base = opencode_manager.get_api_base()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base}/session")
        resp.raise_for_status()
        return resp.json()


@router.post("/sessions")
async def create_session(title: str | None = None):
    """Create a new OpenCode session."""
    base = opencode_manager.get_api_base()
    body: dict[str, Any] = {}
    if title:
        body["title"] = title
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{base}/session", json=body)
        resp.raise_for_status()
        return resp.json()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    base = opencode_manager.get_api_base()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base}/session/{session_id}")
        resp.raise_for_status()
        return resp.json()


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    base = opencode_manager.get_api_base()
    async with httpx.AsyncClient() as client:
        resp = await client.delete(f"{base}/session/{session_id}")
        resp.raise_for_status()
        return resp.json()


@router.get("/sessions/{session_id}/messages")
async def list_messages(session_id: str, limit: int = 50):
    """List messages in a session."""
    base = opencode_manager.get_api_base()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{base}/session/{session_id}/message", params={"limit": limit}
        )
        resp.raise_for_status()
        return resp.json()


@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, body: dict[str, Any]):
    """Send a message to a session."""
    base = opencode_manager.get_api_base()
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{base}/session/{session_id}/message", json=body
        )
        resp.raise_for_status()
        return resp.json()


@router.post("/sessions/{session_id}/prompt_async")
async def send_prompt_async(session_id: str, body: dict[str, Any]):
    """Send a message asynchronously (no wait)."""
    base = opencode_manager.get_api_base()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/session/{session_id}/prompt_async", json=body
        )
        resp.raise_for_status()
        return {"status": "sent"}


@router.post("/sessions/{session_id}/abort")
async def abort_session(session_id: str):
    """Abort a running session."""
    base = opencode_manager.get_api_base()
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{base}/session/{session_id}/abort")
        resp.raise_for_status()
        return resp.json()


@router.get("/config")
async def get_config():
    """Get OpenCode config."""
    base = opencode_manager.get_api_base()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base}/config")
        resp.raise_for_status()
        return resp.json()


@router.get("/providers")
async def list_providers():
    """List available providers."""
    base = opencode_manager.get_api_base()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base}/provider")
        resp.raise_for_status()
        return resp.json()


@router.get("/mcp")
async def list_mcp_servers():
    """List MCP server status."""
    base = opencode_manager.get_api_base()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base}/mcp")
        resp.raise_for_status()
        return resp.json()


@router.get("/agents")
async def list_agents():
    """List available agents."""
    base = opencode_manager.get_api_base()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base}/agent")
        resp.raise_for_status()
        return resp.json()


@router.websocket("/ws/{session_id}")
async def websocket_terminal(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for terminal streaming.

    Bridges browser xterm.js to OpenCode's event stream.
    """
    await websocket.accept()

    base = opencode_manager.get_api_base()

    try:
        # Connect to OpenCode's SSE event stream
        async with httpx.AsyncClient() as client:
            # Send initial connection message
            await websocket.send_json({"type": "connected", "session_id": session_id})

            # Main loop - receive from browser, forward to OpenCode
            while True:
                try:
                    # Receive data from browser
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                    msg = json.loads(data)

                    if msg.get("type") == "input":
                        # Forward terminal input to OpenCode
                        pass  # Handled via REST API

                    elif msg.get("type") == "message":
                        # Send a chat message
                        resp = await client.post(
                            f"{base}/session/{session_id}/prompt_async",
                            json={
                                "parts": [{"type": "text", "text": msg["content"]}],
                                "model": msg.get("model"),
                                "agent": msg.get("agent"),
                            },
                        )

                    elif msg.get("type") == "resize":
                        # Terminal resize - no-op for web
                        pass

                except asyncio.TimeoutError:
                    # No data from browser, poll for events
                    pass

                except WebSocketDisconnect:
                    break

                # Poll OpenCode events
                try:
                    resp = await client.get(
                        f"{base}/session/{session_id}/message",
                        params={"limit": 1},
                        timeout=0.5,
                    )
                    if resp.status_code == 200:
                        messages = resp.json()
                        if messages:
                            await websocket.send_json({
                                "type": "message",
                                "data": messages[-1],
                            })
                except Exception:
                    pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
