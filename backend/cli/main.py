"""Main CLI entry point for AgentDesk terminal interface."""

import sys
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.group(invoke_without_command=True)
@click.option("--config", "-C", type=click.Path(), help="Path to config file")
@click.option("--verbose", "-v", is_flag=True, help="Verbose tool output")
@click.option("--model", "-m", type=str, help="Override AI model")
@click.pass_context
def cli(ctx: click.Context, config: str | None, verbose: bool, model: str | None) -> None:
    """AgentDesk - AI Agent for Trades Businesses

    Terminal interface for scheduling, dispatch, and invoicing.
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["verbose"] = verbose
    ctx.obj["model"] = model

    if ctx.invoked_subcommand is None:
        # Start interactive TUI mode
        from backend.cli.tui import start_tui
        start_tui(
            config_path=config,
            verbose=verbose,
            model_override=model,
        )


@cli.command()
@click.argument("prompt")
@click.option("--format", "-f", "output_format", type=click.Choice(["text", "json"]), default="text")
@click.option("--quiet", "-q", is_flag=True, help="Suppress spinner")
@click.pass_context
def run(ctx: click.Context, prompt: str, output_format: str, quiet: bool) -> None:
    """Run a single prompt and print the response."""
    from backend.cli.tui import run_single_prompt
    run_single_prompt(
        prompt=prompt,
        config_path=ctx.obj.get("config_path"),
        model_override=ctx.obj.get("model"),
        output_format=output_format,
        quiet=quiet,
    )


@cli.command()
@click.option("--port", "-p", type=int, default=8080, help="Port to listen on")
@click.pass_context
def serve(ctx: click.Context, port: int) -> None:
    """Start a headless HTTP server for programmatic access."""
    console.print(f"[dim]Starting AgentDesk server on port {port}...[/]")
    # TODO: Implement HTTP server mode
    console.print("[yellow]Server mode not yet implemented.[/]")


@cli.command("config")
@click.argument("action", type=click.Choice(["show", "init", "set", "get"]))
@click.argument("key", required=False)
@click.argument("value", required=False)
def config_cmd(action: str, key: str | None, value: str | None) -> None:
    """Manage AgentDesk configuration."""
    from backend.cli.config import load_config, save_config, AppConfig
    from rich.table import Table

    if action == "show":
        config = load_config()
        table = Table(title="AgentDesk Configuration", show_header=True)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("project_name", config.project_name)
        table.add_row("provider", config.provider.name)
        table.add_row("model", config.provider.model)
        table.add_row("api_key", "***" if config.provider.api_key else "(not set)")
        table.add_row("mcp_servers", str(len(config.mcp_servers)))
        table.add_row("max_iterations", str(config.agent.max_iterations))
        console.print(table)

    elif action == "init":
        config_path = Path("agentdesk.json")
        if config_path.exists():
            console.print("[yellow]agentdesk.json already exists. Use 'config set' to modify.[/]")
            return
        config = AppConfig()
        save_config(config, config_path)
        console.print("[green]Created agentdesk.json with default configuration.[/]")

    elif action == "set":
        if not key or not value:
            console.print("[red]Usage: agentdesk config set <key> <value>[/]")
            return
        config = load_config()
        if key == "provider.name":
            config.provider.name = value
        elif key == "provider.model":
            config.provider.model = value
        elif key == "provider.api_key":
            config.provider.api_key = value
        elif key == "agent.max_iterations":
            config.agent.max_iterations = int(value)
        else:
            console.print(f"[red]Unknown config key: {key}[/]")
            return
        save_config(config)
        console.print(f"[green]Set {key} = {value}[/]")

    elif action == "get":
        if not key:
            console.print("[red]Usage: agentdesk config get <key>[/]")
            return
        config = load_config()
        if key == "provider.name":
            console.print(config.provider.name)
        elif key == "provider.model":
            console.print(config.provider.model)
        elif key == "provider.api_key":
            console.print("***" if config.provider.api_key else "")
        elif key == "agent.max_iterations":
            console.print(str(config.agent.max_iterations))
        else:
            console.print(f"[red]Unknown config key: {key}[/]")


@cli.command("sessions")
@click.argument("action", type=click.Choice(["list", "delete"]))
@click.argument("session_id", required=False)
def sessions_cmd(action: str, session_id: str | None) -> None:
    """Manage conversation sessions."""
    from backend.cli.session import SessionManager
    from backend.cli.tools_display import ToolDisplay

    manager = SessionManager()
    display = ToolDisplay()

    if action == "list":
        sessions = manager.list_sessions()
        display.show_sessions_list(sessions)

    elif action == "delete":
        if not session_id:
            console.print("[red]Usage: agentdesk sessions delete <session_id>[/]")
            return
        if manager.delete_session(session_id):
            console.print(f"[green]Deleted session {session_id}[/]")
        else:
            console.print(f"[red]Session {session_id} not found[/]")


@cli.command("mcp")
def mcp_cmd() -> None:
    """List available MCP servers."""
    from backend.mcp_servers.registry import list_mcp_servers
    from rich.table import Table

    servers = list_mcp_servers()
    table = Table(title="MCP Servers", show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")

    for name in servers:
        table.add_row(name, "[green]Available[/green]")

    console.print(table)


if __name__ == "__main__":
    cli()
