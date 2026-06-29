"""Tool execution display for the terminal."""

from datetime import datetime, timezone
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax

console = Console()


class ToolDisplay:
    """Display tool execution progress in the terminal."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def show_tool_call(self, tool_name: str, tool_args: dict[str, Any]) -> None:
        """Display when a tool is being called."""
        args_text = ""
        for key, value in tool_args.items():
            if isinstance(value, str) and len(value) > 60:
                value = value[:57] + "..."
            args_text += f"  dim_cyan){key}: white){value}\n"

        panel = Panel(
            args_text.strip() if args_text else "  (no arguments)",
            title=f"[bold cyan] {tool_name}[/]",
            border_style="cyan",
            padding=(0, 1),
        )
        console.print(panel)

    def show_tool_result(self, tool_name: str, result: str, success: bool = True) -> None:
        """Display tool execution result."""
        if not self.verbose and success:
            # Show compact result for successful calls
            status = "[green]OK[/green]" if success else "[red]FAILED[/red]"
            # Truncate long results
            display_result = result[:200] + "..." if len(result) > 200 else result
            console.print(f"    dim){status} {tool_name}: {display_result}[/]")
            return

        # Show full result for verbose mode or failures
        style = "green" if success else "red"
        panel = Panel(
            result[:500] if len(result) > 500 else result,
            title=f"[{style}] {tool_name} - {'Success' if success else 'Error'}[/{style}]",
            border_style=style,
            padding=(0, 1),
        )
        console.print(panel)

    def show_tool_error(self, tool_name: str, error: str) -> None:
        """Display tool execution error."""
        panel = Panel(
            f"[red]{error}[/red]",
            title=f"[red] {tool_name} - Error[/red]",
            border_style="red",
            padding=(0, 1),
        )
        console.print(panel)

    def show_routing(self, from_provider: str, to_provider: str) -> None:
        """Display model routing decision."""
        console.print(f"  dim_cyan) {from_provider} -> {to_provider}[/]")

    def show_thinking(self) -> None:
        """Display thinking indicator."""
        console.print("  dim_yellow) Thinking...[/]", end="\r")

    def clear_thinking(self) -> None:
        """Clear thinking indicator."""
        console.print("\r" + " " * 30 + "\r", end="")

    def show_streaming_start(self) -> None:
        """Display start of streaming response."""
        console.print()

    def show_streaming_token(self, token: str) -> None:
        """Display a streaming token."""
        console.print(token, end="", highlight=False)

    def show_streaming_end(self) -> None:
        """Display end of streaming response."""
        console.print()

    def show_command(self, command: str, description: str = "") -> None:
        """Display a slash command."""
        console.print(f"  [bold blue]/command[/bold_blue] [dim]{description}[/dim]")

    def show_error(self, message: str) -> None:
        """Display an error message."""
        console.print(f"\n[red]Error:[/red] {message}\n")

    def show_info(self, message: str) -> None:
        """Display an info message."""
        console.print(f"[dim]{message}[/dim]")

    def show_warning(self, message: str) -> None:
        """Display a warning message."""
        console.print(f"[yellow]Warning:[/yellow] {message}")

    def show_session_info(self, session_id: str, message_count: int) -> None:
        """Display session info."""
        console.print(f"  [dim]Session: {session_id} ({message_count} messages)[/]")

    def show_welcome(self) -> None:
        """Display welcome message."""
        welcome = Text()
        welcome.append("AgentDesk", style="bold blue")
        welcome.append(" - AI Agent for Trades Businesses", style="dim")
        console.print(Panel(welcome, border_style="blue", padding=(0, 2)))
        console.print()
        console.print("  [dim]Type your message or use /commands:[/]")
        console.print("  [dim]  /help     - Show all commands[/]")
        console.print("  [dim]  /schedule - View today's schedule[/]")
        console.print("  [dim]  /invoices - View invoice summary[/]")
        console.print("  [dim]  /book     - Book a new job[/]")
        console.print("  [dim]  /route    - Optimize route[/]")
        console.print("  [dim]  /sessions - Manage sessions[/]")
        console.print("  [dim]  /clear    - Clear current session[/]")
        console.print("  [dim]  /quit     - Exit AgentDesk[/]")
        console.print()

    def show_help(self) -> None:
        """Display help information."""
        table = Table(title="Commands", show_header=True, header_style="bold")
        table.add_column("Command", style="cyan", width=20)
        table.add_column("Description", style="white")

        table.add_row("/help", "Show this help message")
        table.add_row("/schedule [date]", "View schedule for a date")
        table.add_row("/invoices", "View invoice summary")
        table.add_row("/book", "Book a new job (guided)")
        table.add_row("/route [date]", "Optimize route for a date")
        table.add_row("/sessions", "List saved sessions")
        table.add_row("/new [name]", "Start a new session")
        table.add_row("/load <id>", "Load a saved session")
        table.add_row("/delete <id>", "Delete a saved session")
        table.add_row("/clear", "Clear current session messages")
        table.add_row("/verbose", "Toggle verbose tool output")
        table.add_row("/model <name>", "Switch AI model")
        table.add_row("/quit", "Exit AgentDesk")

        console.print(table)

    def show_sessions_list(self, sessions: list[dict[str, str]]) -> None:
        """Display list of saved sessions."""
        if not sessions:
            console.print("  [dim]No saved sessions.[/]")
            return

        table = Table(title="Saved Sessions", show_header=True, header_style="bold")
        table.add_column("ID", style="cyan", width=14)
        table.add_column("Name", style="white")
        table.add_column("Messages", justify="right")
        table.add_column("Created", style="dim")

        for s in sessions:
            created = s["created_at"][:10] if s["created_at"] else ""
            table.add_row(s["id"], s["name"], s["messages"], created)

        console.print(table)
