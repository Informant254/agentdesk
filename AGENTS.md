# AgentDesk — AI Agent for Trades Businesses

## What this is
AgentDesk is an AI-powered operations platform for trades businesses (HVAC, plumbing, electrical). It handles scheduling, dispatch, and invoicing through a web dashboard and AI chat interface. The AI agent uses LangGraph + Claude and connects to Jobber (field service management), Google Calendar, and Google Maps via MCP servers.

## Stack
- **Frontend**: Next.js 14 + Tailwind CSS, deployed on Netlify (https://agentdesk-v2.netlify.app)
- **Backend**: FastAPI (Python), deployed on Render (https://agentdesk-mzx6.onrender.com)
- **Database**: Supabase (PostgreSQL)
- **AI Agent**: LangGraph + LangChain + Anthropic Claude
- **MCP Servers**: Google Calendar, Google Maps, Jobber

## Project structure
```
agentdesk/
├── backend/
│   ├── api/main.py          # FastAPI app — all REST endpoints
│   ├── agent/               # LangGraph agent + tools
│   │   ├── graph.py         # Main agent graph
│   │   ├── scheduling.py    # Scheduling workflow
│   │   ├── invoicing.py     # Invoice workflow
│   │   ├── dispatch.py      # Dispatch workflow
│   │   └── tools.py         # Agent tools
│   ├── mcp_servers/         # MCP protocol servers
│   │   ├── google_calendar.py
│   │   ├── google_maps.py
│   │   └── jobber.py
│   ├── opencode_server/     # OpenCode server management
│   │   ├── manager.py       # Per-user OpenCode process manager
│   │   └── websocket_proxy.py  # FastAPI routes + WebSocket proxy
│   ├── security/
│   │   ├── auth.py          # JWT auth
│   │   ├── encryption.py    # Fernet encryption for API keys
│   │   └── audit.py         # Audit logging
│   └── config.py            # Settings (pydantic)
├── frontend/
│   └── src/
│       ├── app/             # Next.js app router
│       ├── components/
│       │   ├── Dashboard.tsx      # Main layout + auth
│       │   ├── Sidebar.tsx        # Navigation
│       │   ├── ChatPanel.tsx      # AI chat interface
│       │   ├── SchedulePanel.tsx  # Job scheduling
│       │   ├── InvoicesPanel.tsx  # Invoice management
│       │   ├── ProfilePanel.tsx   # User profile
│       │   └── opencode/          # OpenCode integration
│       │       ├── OpenCodePanel.tsx      # Main OpenCode UI
│       │       ├── OpenCodeTerminal.tsx   # xterm.js terminal + session manager
│       │       └── ProvidersPanel.tsx     # AI provider key management
│       ├── lib/
│       │   ├── api.ts       # Backend API client
│       │   └── supabase.ts  # Supabase client
│       └── types/index.ts   # TypeScript types
├── config/schema.sql        # Supabase DB schema
├── opencode.json            # OpenCode config (MCP servers, providers)
└── AGENTS.md                # This file — OpenCode project context
```

## API endpoints
- `POST /api/auth/register` — create account
- `POST /api/auth/login` — login
- `POST /api/auth/social` — exchange Supabase OAuth token for JWT
- `POST /api/chat` — send message to AI agent (requires auth)
- `GET /api/opencode/status` — OpenCode server status
- `POST /api/opencode/start` — start user's OpenCode server
- `GET /api/opencode/providers` — list user's configured providers
- `POST /api/opencode/providers/keys` — save/update a provider API key
- `DELETE /api/opencode/providers/{provider}` — remove a provider key
- `GET /api/opencode/sessions` — list OpenCode sessions
- `POST /api/opencode/sessions` — create a new session
- `GET /api/opencode/sessions/{id}/messages` — list messages
- `POST /api/opencode/sessions/{id}/messages` — send a message
- `WS /api/opencode/ws/{session_id}` — real-time WebSocket for session
- `GET /api/workflows/daily-schedule/{date}` — get schedule
- `GET /api/workflows/optimize-route/{date}` — optimize routes
- `POST /api/workflows/create-invoice` — create invoice
- `GET /api/workflows/invoice-summary` — invoice summary

## Supabase schema
- `jobs` — field service jobs (title, status, client, address, scheduled_at)
- `invoices` — invoices (job_id, amount_cents, status, due_date, line_items)
- `sessions` — OpenCode chat sessions

## Key patterns
- Auth: Supabase OAuth → exchange for backend JWT → include as `Authorization: Bearer <token>`
- API keys for OpenCode providers are encrypted with Fernet before storage
- OpenCode runs as a subprocess (`opencode serve`) managed by `OpenCodeManager`
- One OpenCode process per user, keyed by user_id, runs on its own port
- WebSocket proxy: browser ↔ FastAPI WS ↔ OpenCode HTTP/SSE API

## How to help users
When users ask about their business operations:
- Scheduling: look at `backend/agent/scheduling.py` and `backend/mcp_servers/google_calendar.py`
- Invoicing: look at `backend/agent/invoicing.py`
- Dispatch/routing: look at `backend/agent/dispatch.py` and `backend/mcp_servers/google_maps.py`
- Frontend UI: components are in `frontend/src/components/`
- API: all routes defined in `backend/api/main.py`

Always check `backend/config.py` for environment variable names before suggesting config changes.
