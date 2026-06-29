# AgentDesk

AI Agent for trades businesses (HVAC, plumbing, electrical) — handles scheduling, dispatch, and invoicing via terminal, web dashboard, or API.

## Quick Start

```bash
# Install
cd agentdesk
pip install -e ".[dev]"

# Configure
cp agentdesk.example.json agentdesk.json
# Edit agentdesk.json with your API keys

# Run the terminal UI
agentdesk

# Or run a single prompt
agentdesk run "Show me today's schedule"
```

## Terminal Interface (TUI)

The terminal interface works like OpenCode — interactive chat with slash commands, tool execution display, and session management.

### Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/schedule [date]` | View schedule for a date |
| `/invoices` | View invoice summary |
| `/book` | Book a new job (guided) |
| `/route [date]` | Optimize route for a date |
| `/sessions` | List saved sessions |
| `/new [name]` | Start a new session |
| `/load <id>` | Load a saved session |
| `/delete <id>` | Delete a saved session |
| `/clear` | Clear current session |
| `/verbose` | Toggle verbose tool output |
| `/model <name>` | Switch AI model |
| `/quit` | Exit AgentDesk |

### Examples

```bash
# Start interactive mode
agentdesk

# Start with a specific model
agentdesk --model claude-3-5-sonnet-20241022

# Run a single prompt
agentdesk run "Book an HVAC repair for Johnson at 123 Main St tomorrow at 9am"

# Run in JSON output mode
agentdesk run "What invoices are overdue?" --format json

# Start with verbose tool output
agentdesk --verbose
```

## Web Dashboard

```bash
# Backend
cd backend
uvicorn backend.api.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Architecture

```
agentdesk/
├── backend/
│   ├── cli/               # Terminal UI (OpenCode-style)
│   │   ├── main.py        # CLI entry point (click)
│   │   ├── tui.py         # Interactive TUI (prompt_toolkit + rich)
│   │   ├── session.py     # Session management
│   │   ├── config.py      # Configuration (agentdesk.json)
│   │   └── tools_display.py  # Tool execution display
│   ├── mcp_servers/       # MCP servers (Calendar, Maps, Jobber)
│   ├── agent/             # LangGraph agent + workflows
│   ├── security/          # Auth, encryption, audit logging
│   └── api/               # FastAPI REST API
├── frontend/              # Next.js dashboard
├── config/                # Database schema
└── tests/                 # Test suite
```

## Configuration

Create `agentdesk.json` in your project root:

```json
{
  "provider": {
    "name": "anthropic",
    "api_key": "your-key-here",
    "model": "claude-3-5-sonnet-20241022"
  },
  "mcp_servers": [
    {"name": "google_calendar", "enabled": true},
    {"name": "google_maps", "enabled": true},
    {"name": "jobber", "enabled": true}
  ],
  "agent": {
    "max_iterations": 20,
    "temperature": 0.7
  }
}
```

Or use environment variables:

```bash
export ANTHROPIC_API_KEY=your-key
export GOOGLE_MAPS_API_KEY=your-key
export JOBBER_API_KEY=your-key
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Terminal UI | Click + Rich + prompt_toolkit |
| AI Agent | LangGraph + LangChain + Claude |
| MCP Servers | FastMCP (Calendar, Maps, Jobber) |
| Backend API | FastAPI + Pydantic |
| Frontend | Next.js + Tailwind CSS |
| Database | Supabase (PostgreSQL) |
| Auth | JWT + bcrypt + Fernet encryption |

## Testing

```bash
pytest tests/ -v
```
