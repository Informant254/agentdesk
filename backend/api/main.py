"""FastAPI application for AgentDesk backend."""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import settings
from backend.agent.graph import run_agent
from backend.agent.workflows import scheduling_workflow, invoice_workflow
from backend.security.auth import auth_manager
from backend.security.audit import audit_logger
from backend.opencode_server.websocket_proxy import router as opencode_router
from backend.opencode_server.manager import opencode_manager

app = FastAPI(
    title="AgentDesk API",
    description="AI Agent for trades businesses - scheduling, dispatch, invoicing",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.app_url,
        "http://localhost:3000",
        "http://localhost:4096",
        "https://agentdesk-v2.netlify.app",
        "https://agentdesk.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(opencode_router)


# ── Auth ──────────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    business_name: str
    business_type: str


class SocialAuthRequest(BaseModel):
    supabase_token: str


@app.post("/api/auth/register", response_model=LoginResponse)
async def register(req: RegisterRequest):
    hashed = auth_manager.hash_password(req.password)
    user_id = f"user_{req.email.replace('@', '_at_')}"
    token = auth_manager.create_access_token(user_id, {"business_name": req.business_name})
    audit_logger.log_auth_event(user_id, "register")
    return LoginResponse(access_token=token, user_id=user_id)


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    user_id = f"user_{req.email.replace('@', '_at_')}"
    token = auth_manager.create_access_token(user_id)
    audit_logger.log_auth_event(user_id, "login")
    return LoginResponse(access_token=token, user_id=user_id)


@app.post("/api/auth/social", response_model=LoginResponse)
async def social_auth(req: SocialAuthRequest):
    user_data = await auth_manager.verify_supabase_token(req.supabase_token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired Supabase token")
    user_id = user_data.get("id", "")
    email = user_data.get("email", "")
    provider = user_data.get("app_metadata", {}).get("provider", "oauth")
    token = auth_manager.create_access_token(user_id, {"email": email, "provider": provider})
    audit_logger.log_auth_event(user_id, f"oauth_{provider}")
    return LoginResponse(access_token=token, user_id=user_id)


# ── Chat ──────────────────────────────────────────────────────────────────────

# Priority order for picking which user key to use in the chat agent
_CHAT_PROVIDER_PRIORITY = ["anthropic", "openai", "google", "gemini", "groq", "mistral"]


async def _pick_chat_key(user_id: str) -> tuple[str | None, str]:
    """Return (api_key, provider) for the best available key for this user."""
    decrypted = await opencode_manager.get_decrypted_keys(user_id)
    for provider in _CHAT_PROVIDER_PRIORITY:
        if provider in decrypted and decrypted[provider]:
            return decrypted[provider], provider
    # Fall back to server-side anthropic key
    if settings.anthropic_api_key:
        return settings.anthropic_api_key, "anthropic"
    return None, "anthropic"


class ChatRequest(BaseModel):
    message: str
    context: dict | None = None


class ChatResponse(BaseModel):
    response: str
    actions_taken: list[str] = []
    provider_used: str | None = None


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, token: dict = Depends(auth_manager.verify_token)):
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = token.get("sub", "")

    api_key, provider = await _pick_chat_key(user_id)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=(
                "No AI provider key found. "
                "Please add an API key in the AI Providers section "
                "(Anthropic Claude or OpenAI GPT-4o are recommended)."
            ),
        )

    try:
        result = await run_agent(
            req.message,
            user_id,
            req.context,
            api_key=api_key,
            provider=provider,
        )
        collected = result.get("collected_data", {})
        final_response = collected.get("result", "")
        if not final_response and result.get("messages"):
            last_msg = result["messages"][-1]
            final_response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        actions = [k for k in collected.keys() if k != "result"]
        audit_logger.log_tool_usage(user_id, "supervisor_routing", {
            "actions": actions,
            "message": req.message[:100],
            "provider": provider,
        })
        return ChatResponse(response=final_response, actions_taken=actions, provider_used=provider)
    except ValueError as e:
        # Raised by _make_llm when no key is available
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Workflows ─────────────────────────────────────────────────────────────────


class BookJobRequest(BaseModel):
    client_name: str
    job_title: str
    job_address: str
    start_time: str
    end_time: str
    description: str = ""


@app.post("/api/workflows/book-job")
async def book_job(req: BookJobRequest, token: dict = Depends(auth_manager.verify_token)):
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = token.get("sub", "")
    result = await scheduling_workflow.book_job(
        user_id=user_id, client_name=req.client_name, job_title=req.job_title,
        job_address=req.job_address, start_time=req.start_time, end_time=req.end_time,
        description=req.description,
    )
    return {"success": result.success, "data": result.data, "errors": result.errors}


class CreateInvoiceRequest(BaseModel):
    job_id: str
    line_items: list[dict]
    due_days: int = 30


@app.post("/api/workflows/create-invoice")
async def create_invoice(req: CreateInvoiceRequest, token: dict = Depends(auth_manager.verify_token)):
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = token.get("sub", "")
    result = await invoice_workflow.create_invoice_from_job(
        user_id=user_id, job_id=req.job_id, line_items=req.line_items, due_days=req.due_days,
    )
    return {"success": result.success, "data": result.data, "errors": result.errors}


@app.get("/api/workflows/daily-schedule/{date}")
async def get_daily_schedule(date: str, token: dict = Depends(auth_manager.verify_token)):
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = token.get("sub", "")
    result = await scheduling_workflow.get_daily_schedule(user_id, date)
    return {"success": result.success, "data": result.data, "errors": result.errors}


@app.get("/api/workflows/optimize-route/{date}")
async def optimize_route(date: str, starting_location: str, token: dict = Depends(auth_manager.verify_token)):
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = token.get("sub", "")
    result = await scheduling_workflow.optimize_day_route(user_id, date, starting_location)
    return {"success": result.success, "data": result.data, "errors": result.errors}


@app.get("/api/workflows/invoice-summary")
async def invoice_summary(token: dict = Depends(auth_manager.verify_token)):
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = token.get("sub", "")
    result = await invoice_workflow.get_invoice_summary(user_id)
    return {"success": result.success, "data": result.data, "errors": result.errors}


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
