"""WebSocket proxy + REST routes for OpenCode integration."""

import asyncio
import json
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.websockets import WebSocketState

from backend.opencode_server.manager import opencode_manager
from backend.security.auth import auth_manager
from backend.security.encryption import decrypt_data, encrypt_data

router = APIRouter(prefix="/api/opencode", tags=["opencode"])


# ── Auth helper ───────────────────────────────────────────────────────────────────────────────────────────────

async def _require_user(token: dict = Depends(auth_manager.verify_token)) -> str:
    if not token:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return token.get("sub", "")


# ── Server lifecycle ────────────────────────────────────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_opencode_server(user_id: str = Depends(_require_user)):
    return await opencode_manager.get_or_start(user_id)


@router.post("/stop")
async def stop_opencode_server(user_id: str = Depends(_require_user)):
    return {"stopped": await opencode_manager.stop_user(user_id)}


@router.get("/status")
async def opencode_status(user_id: str = Depends(_require_user)):
    return await opencode_manager.status(user_id)


# ── Provider management ─────────────────────────────────────────────────────────────────────────────────────────────

SUPPORTED_PROVIDERS = [
    {"id": "anthropic",  "name": "Anthropic (Claude)",     "env": "ANTHROPIC_API_KEY",             "url": "https://console.anthropic.com/keys"},
    {"id": "openai",     "name": "OpenAI (GPT-4o)",        "env": "OPENAI_API_KEY",                "url": "https://platform.openai.com/api-keys"},
    {"id": "google",     "name": "Google Gemini",           "env": "GOOGLE_GENERATIVE_AI_API_KEY", "url": "https://aistudio.google.com/app/apikey"},
    {"id": "groq",       "name": "Groq (fast inference)",   "env": "GROQ_API_KEY",                 "url": "https://console.groq.com/keys"},
    {"id": "mistral",    "name": "Mistral AI",              "env": "MISTRAL_API_KEY",              "url": "https://console.mistral.ai/api-keys"},
    {"id": "openrouter", "name": "OpenRouter (75+ models)", "env": "OPENROUTER_API_KEY",           "url": "https://openrouter.ai/keys"},
    {"id": "deepseek",   "name": "DeepSeek",                "env": "DEEPSEEK_API_KEY",             "url": "https://platform.deepseek.com/api_keys"},
    {"id": "xai",        "name": "xAI (Grok)",              "env": "XAI_API_KEY",                  "url": "https://console.x.ai"},
    {"id": "cohere",     "name": "Cohere",                  "env": "COHERE_API_KEY",               "url": "https://dashboard.cohere.com/api-keys"},
    {"id": "together",   "name": "Together AI",             "env": "TOGETHER_AI_API_KEY",          "url": "https://api.together.xyz/settings/api-keys"},
    {"id": "fireworks",  "name": "Fireworks AI",            "env": "FIREWORKS_API_KEY",            "url": "https://fireworks.ai/account/api-keys"},
    {"id": "perplexity", "name": "Perplexity",              "env": "PERPLEXITY_API_KEY",           "url": "https://www.perplexity.ai/settings/api"},
]
_VALID_PROVIDER_IDS = {p["id"] for p in SUPPORTED_PROVIDERS}


@router.get("/providers")
async def list_providers(user_id: str = Depends(_require_user)):
    configured = set(await opencode_manager.list_providers(user_id))
    return {"providers": [{**p, "connected": p["id"] in configured} for p in SUPPORTED_PROVIDERS]}


class SaveProviderKeyRequest(BaseModel):
    provider: str
    api_key: str


@router.post("/providers/keys")
async def save_provider_key(req: SaveProviderKeyRequest, user_id: str = Depends(_require_user)):
    if req.provider not in _VALID_PROVIDER_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}")
    if not req.api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty")

    encrypted = encrypt_data(req.api_key.strip())
    await opencode_manager.save_provider_key(user_id, req.provider, encrypted)

    # Restart so the new key is in the env
    if (await opencode_manager.status(user_id)).get("status") == "running":
        await opencode_manager.stop_user(user_id)
        await opencode_manager.get_or_start(user_id)

    return {"success": True, "provider": req.provider}


@router.delete("/providers/{provider}")
async def delete_provider_key(provider: str, user_id: str = Depends(_require_user)):
    await opencode_manager.delete_provider_key(user_id, provider)
    # Restart so the key is removed from env
    if (await opencode_manager.status(user_id)).get("status") == "running":
        await opencode_manager.stop_user(user_id)
        await opencode_manager.get_or_start(user_id)
    return {"success": True, "provider": provider}


# ── Session management ──────────────────────────────────────────────────────────────────────────────────────────────

async def _ensure_running(user_id: str) -> str:
    base = opencode_manager.get_api_base(user_id)
    if base:
        return base
    result = await opencode_manager.get_or_start(user_id)
    if result["status"] not in ("started", "running"):
        raise HTTPException(status_code=503, detail=f"OpenCode unavailable: {result.get('error')}")
    return result["url"]


@router.get("/sessions")
async def list_sessions(user_id: str = Depends(_require_user)):
    base = await _ensure_running(user_id)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{base}/session")
        resp.raise_for_status()
        return resp.json()


@router.post("/sessions")
async def create_session(body: dict[str, Any] = {}, user_id: str = Depends(_require_user)):
    base = await _ensure_running(user_id)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{base}/session", json=body)
        resp.raise_for_status()
        return resp.json()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user_id: str = Depends(_require_user)):
    base = await _ensure_running(user_id)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{base}/session/{session_id}")
        resp.raise_for_status()
        return resp.json()


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user_id: str = Depends(_require_user)):
    base = await _ensure_running(user_id)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(f"{base}/session/{session_id}")
        resp.raise_for_status()
        return resp.json()


@router.get("/sessions/{session_id}/messages")
async def list_messages(session_id: str, limit: int = 50, user_id: str = Depends(_require_user)):
    base = await _ensure_running(user_id)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{base}/session/{session_id}/message", params={"limit": limit})
        resp.raise_for_status()
        return resp.json()


@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, body: dict[str, Any], user_id: str = Depends(_require_user)):
    base = await _ensure_running(user_id)
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{base}/session/{session_id}/message", json=body)
        resp.raise_for_status()
        return resp.json()


@router.post("/sessions/{session_id}/abort")
async def abort_session(session_id: str, user_id: str = Depends(_require_user)):
    base = await _ensure_running(user_id)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{base}/session/{session_id}/abort")
        resp.raise_for_status()
        return resp.json()


# ── WebSocket proxy ───────────────────────────────────────────────────────────────────────────────────────────────

@router.websocket("/ws/{session_id}")
async def websocket_proxy(websocket: WebSocket, session_id: str):
    """
    Real-time bridge: browser xterm ↔ FastAPI WS ↔ OpenCode HTTP/SSE.

    Protocol:
      1. First frame: {"type": "auth", "token": "<jwt>"}
      2. Send:        {"type": "message", "content": "..."}
      3. Receive:     {"type": "message"|"error"|"connected", ...}

    Message deduplication: tracks the last forwarded message ID so the
    polling loop never resends the same message.
    """
    await websocket.accept()

    # ── Auth handshake ────────────────────────────────────────────────────────────────────────
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        init = json.loads(raw)
    except (asyncio.TimeoutError, Exception):
        await websocket.send_json({"type": "error", "message": "Auth timeout"})
        await websocket.close()
        return

    if init.get("type") != "auth":
        await websocket.send_json({"type": "error", "message": "First message must be auth"})
        await websocket.close()
        return

    token = auth_manager.verify_token_raw(init.get("token", ""))
    if not token:
        await websocket.send_json({"type": "error", "message": "Invalid token"})
        await websocket.close()
        return

    user_id = token.get("sub", "")

    try:
        base = await _ensure_running(user_id)
    except HTTPException as e:
        await websocket.send_json({"type": "error", "message": e.detail})
        await websocket.close()
        return

    await websocket.send_json({
        "type": "connected",
        "providers": await opencode_manager.list_providers(user_id),
    })

    # ── Main loop ──────────────────────────────────────────────────────────────────────────────────────
    last_message_id: str | None = None   # deduplication cursor

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            while websocket.client_state == WebSocketState.CONNECTED:
                try:
                    raw = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                    msg = json.loads(raw)
                except asyncio.TimeoutError:
                    # Poll for new messages since last forwarded one
                    try:
                        resp = await client.get(
                            f"{base}/session/{session_id}/message",
                            params={"limit": 5},
                            timeout=0.5,
                        )
                        if resp.status_code == 200:
                            messages: list[dict] = resp.json()
                            for m in messages:
                                mid = m.get("id") or m.get("messageID") or str(m)
                                if mid != last_message_id:
                                    last_message_id = mid
                                    await websocket.send_json({"type": "message", "data": m})
                    except Exception:
                        pass
                    continue
                except WebSocketDisconnect:
                    break
                except Exception:
                    break

                msg_type = msg.get("type")

                if msg_type == "message":
                    try:
                        resp = await client.post(
                            f"{base}/session/{session_id}/message",
                            json={
                                "parts": [{"type": "text", "text": msg.get("content", "")}],
                                "model": msg.get("model"),
                                "agent": msg.get("agent", "build"),
                            },
                            timeout=120,
                        )
                        if resp.status_code == 200:
                            result = resp.json()
                            mid = result.get("id") or result.get("messageID") or str(result)
                            last_message_id = mid
                            await websocket.send_json({"type": "message", "data": result})
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "message": f"OpenCode returned {resp.status_code}",
                            })
                    except Exception as e:
                        await websocket.send_json({"type": "error", "message": str(e)})

                elif msg_type == "abort":
                    try:
                        await client.post(f"{base}/session/{session_id}/abort")
                    except Exception:
                        pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
