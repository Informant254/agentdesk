"""Configuration system for AgentDesk CLI (opencode.json style)."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    """Configuration for an AI provider."""

    name: str
    api_key: str = ""
    model: str = "claude-3-5-sonnet-20241022"
    base_url: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7


class MCPConfig(BaseModel):
    """Configuration for an MCP server."""

    name: str
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class AgentConfig(BaseModel):
    """Configuration for the agent."""

    system_prompt: str = ""
    max_iterations: int = 20
    temperature: float = 0.7


class AppConfig(BaseModel):
    """Root application configuration."""

    project_name: str = "AgentDesk"
    working_directory: str = "."
    provider: ProviderConfig = Field(
        default_factory=lambda: ProviderConfig(name="anthropic", model="claude-3-5-sonnet-20241022")
    )
    mcp_servers: list[MCPConfig] = Field(default_factory=list)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    custom_commands: dict[str, str] = Field(default_factory=dict)

    model_config = {"json_schema_extra": {"examples": [{"project_name": "AgentDesk"}]}}


DEFAULT_CONFIG = AppConfig()


def find_config(starting_dir: str | Path | None = None) -> Path | None:
    """Find agentdesk.json config file by searching up from starting directory."""
    current = Path(starting_dir or ".").resolve()
    while True:
        config_file = current / "agentdesk.json"
        if config_file.exists():
            return config_file
        config_file = current / ".agentdesk.json"
        if config_file.exists():
            return config_file
        parent = current.parent
        if parent == current:
            return None
        current = parent


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """Load configuration from file, falling back to defaults."""
    if config_path is None:
        config_path = find_config()
    
    if config_path is None:
        return DEFAULT_CONFIG
    
    config_path = Path(config_path)
    if not config_path.exists():
        return DEFAULT_CONFIG

    with open(config_path) as f:
        data = json.load(f)

    return AppConfig(**data)


def save_config(config: AppConfig, config_path: str | Path = "agentdesk.json") -> None:
    """Save configuration to file."""
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w") as f:
        json.dump(config.model_dump(), f, indent=2, default=str)


def get_user_config_dir() -> Path:
    """Get the user-level config directory."""
    import os
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", "~"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config"))
    return (base / "agentdesk").expanduser()


def get_project_config_dir() -> Path:
    """Get the project-level config directory."""
    return Path(".agentdesk")
