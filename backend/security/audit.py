"""Audit logging for compliance and security monitoring."""

import json
from datetime import datetime, timezone
from typing import Any


class AuditLogger:
    """Log agent actions for audit trail and compliance."""

    def __init__(self):
        self.logs: list[dict[str, Any]] = []

    def log_action(
        self,
        user_id: str,
        action: str,
        tool_name: str,
        tool_args: dict[str, Any],
        result: dict[str, Any],
        status: str = "success",
        error: str | None = None,
    ) -> None:
        """Log an agent action to the audit trail."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "action": action,
            "tool": tool_name,
            "arguments": _sanitize_args(tool_args),
            "result_status": status,
            "error": error,
        }
        self.logs.append(entry)
        # In production: write to Supabase audit_logs table

    def log_auth_event(
        self,
        user_id: str,
        event_type: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log authentication events (login, logout, token refresh)."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "event_type": event_type,
            "details": details or {},
        }
        self.logs.append(entry)

    def log_mcp_connection(
        self,
        user_id: str,
        server_name: str,
        action: str,
        status: str,
    ) -> None:
        """Log MCP server connection events."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "server": server_name,
            "action": action,
            "status": status,
        }
        self.logs.append(entry)

    def get_user_logs(self, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Get audit logs for a specific user."""
        user_logs = [log for log in self.logs if log.get("user_id") == user_id]
        return user_logs[-limit:]


def _sanitize_args(args: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive fields from logged arguments."""
    sensitive_keys = {"access_token", "api_key", "password", "secret", "token"}
    return {k: "***" if k.lower() in sensitive_keys else v for k, v in args.items()}


audit_logger = AuditLogger()
