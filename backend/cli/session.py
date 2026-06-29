"""Session management for AgentDesk CLI."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SessionMessage(BaseModel):
    """A single message in a session."""

    role: str  # "user" | "assistant" | "system" | "tool"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: str | None = None


class Session(BaseModel):
    """A conversation session."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    messages: list[SessionMessage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_message(self, role: str, content: str, **kwargs: Any) -> SessionMessage:
        """Add a message to the session."""
        msg = SessionMessage(role=role, content=content, **kwargs)
        self.messages.append(msg)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return msg

    def get_context_messages(self, max_messages: int = 50) -> list[SessionMessage]:
        """Get recent messages for context window."""
        return self.messages[-max_messages:]


class SessionManager:
    """Manage conversation sessions."""

    def __init__(self, storage_dir: str | Path = ".agentdesk/sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Session | None = None

    def create_session(self, name: str = "") -> Session:
        """Create a new session."""
        session = Session(name=name or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self.current_session = session
        self._save_session(session)
        return session

    def load_session(self, session_id: str) -> Session:
        """Load an existing session by ID."""
        session_file = self.storage_dir / f"{session_id}.json"
        if not session_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")
        with open(session_file) as f:
            data = json.load(f)
        session = Session(**data)
        self.current_session = session
        return session

    def list_sessions(self) -> list[dict[str, str]]:
        """List all saved sessions."""
        sessions = []
        for f in sorted(self.storage_dir.glob("*.json"), reverse=True):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                sessions.append({
                    "id": data.get("id", f.stem),
                    "name": data.get("name", "Unnamed"),
                    "created_at": data.get("created_at", ""),
                    "messages": str(len(data.get("messages", []))),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        session_file = self.storage_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
            return True
        return False

    def _save_session(self, session: Session) -> None:
        """Save session to disk."""
        session_file = self.storage_dir / f"{session.id}.json"
        with open(session_file, "w") as f:
            json.dump(session.model_dump(), f, indent=2, default=str)

    def save_current(self) -> None:
        """Save the current session."""
        if self.current_session:
            self._save_session(self.current_session)
