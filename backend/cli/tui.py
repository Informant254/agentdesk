"""Interactive TUI for AgentDesk - Terminal User Interface."""

import sys
import signal
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live

from backend.cli.config import load_config, AppConfig
from backend.cli.session import SessionManager, Session
from backend.cli.tools_display import ToolDisplay, console

# Slash commands
COMMANDS = {
    "/help": "Show help message",
    "/schedule": "View today's schedule",
    "/invoices": "View invoice summary",
    "/book": "Book a new job",
    "/route": "Optimize route for today",
    "/sessions": "List saved sessions",
    "/new": "Start a new session",
    "/load": "Load a saved session",
    "/delete": "Delete a saved session",
    "/clear": "Clear current session",
    "/verbose": "Toggle verbose tool output",
    "/model": "Switch AI model",
    "/quit": "Exit AgentDesk",
    "/exit": "Exit AgentDesk",
}

completer = WordCompleter(list(COMMANDS.keys()), ignore_case=True)


class AgentTUI:
    """Interactive terminal UI for AgentDesk."""

    def __init__(
        self,
        config_path: str | None = None,
        verbose: bool = False,
        model_override: str | None = None,
    ):
        self.config = load_config(config_path)
        if model_override:
            self.config.provider.model = model_override
        self.verbose = verbose
        self.display = ToolDisplay(verbose=verbose)
        self.session_manager = SessionManager()
        self.session: Session | None = None
        self.running = True
        self.session = self.session_manager.create_session()

    def run(self) -> None:
        """Start the interactive TUI."""
        self.display.show_welcome()
        self.display.show_session_info(
            self.session.id, len(self.session.messages)
        )

        session = PromptSession(history=InMemoryHistory(), completer=completer)

        while self.running:
            try:
                user_input = session.prompt(
                    self._get_prompt(),
                    completer=completer,
                )
                if not user_input.strip():
                    continue

                self._handle_input(user_input.strip())

            except KeyboardInterrupt:
                continue
            except EOFError:
                self._quit()
                break

    def _get_prompt(self) -> str:
        """Build the prompt string."""
        msg_count = len(self.session.messages) if self.session else 0
        return f"agentdesk({msg_count}) > "

    def _handle_input(self, user_input: str) -> None:
        """Handle user input."""
        # Handle slash commands
        if user_input.startswith("/"):
            self._handle_command(user_input)
            return

        # Send message to agent
        self._send_message(user_input)

    def _handle_command(self, user_input: str) -> None:
        """Handle slash commands."""
        parts = user_input.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command in ("/quit", "/exit"):
            self._quit()

        elif command == "/help":
            self.display.show_help()

        elif command == "/clear":
            if self.session:
                self.session.messages.clear()
                self.session_manager.save_current()
                console.print("[green]Session cleared.[/]")

        elif command == "/new":
            name = args if args else ""
            self.session = self.session_manager.create_session(name)
            console.print(f"[green]New session: {self.session.id}[/]")

        elif command == "/sessions":
            sessions = self.session_manager.list_sessions()
            self.display.show_sessions_list(sessions)

        elif command == "/load":
            if not args:
                console.print("[red]Usage: /load <session_id>[/]")
                return
            try:
                self.session = self.session_manager.load_session(args)
                console.print(f"[green]Loaded session: {self.session.name} ({len(self.session.messages)} messages)[/]")
            except FileNotFoundError:
                console.print(f"[red]Session {args} not found.[/]")

        elif command == "/delete":
            if not args:
                console.print("[red]Usage: /delete <session_id>[/]")
                return
            if self.session_manager.delete_session(args):
                console.print(f"[green]Deleted session {args}[/]")
            else:
                console.print(f"[red]Session {args} not found.[/]")

        elif command == "/verbose":
            self.verbose = not self.verbose
            self.display.verbose = self.verbose
            status = "ON" if self.verbose else "OFF"
            console.print(f"[cyan]Verbose mode: {status}[/]")

        elif command == "/model":
            if not args:
                console.print(f"[cyan]Current model: {self.config.provider.model}[/]")
                console.print("[dim]Usage: /model <provider/model>[/]")
                return
            self.config.provider.model = args
            console.print(f"[green]Switched to model: {args}[/]")

        elif command == "/schedule":
            self._handle_schedule(args)

        elif command == "/invoices":
            self._handle_invoices()

        elif command == "/book":
            self._handle_book()

        elif command == "/route":
            self._handle_route(args)

        else:
            console.print(f"[red]Unknown command: {command}[/]")
            console.print("[dim]Type /help for available commands.[/]")

    def _send_message(self, message: str) -> None:
        """Send a message to the agent and display the response."""
        # Add user message to session
        assert self.session is not None
        self.session.add_message("user", message)
        self.session_manager.save_current()

        # Show thinking
        self.display.show_thinking()

        try:
            # Import and run the agent
            from backend.agent.graph import run_agent
            import asyncio

            result = asyncio.run(
                run_agent(
                    user_message=message,
                    user_id=self.session.id,
                    context={
                        "session_id": self.session.id,
                        "model": self.config.provider.model,
                    },
                )
            )

            self.display.clear_thinking()

            # Extract response
            last_message = result["messages"][-1]
            response = last_message.content

            # Show response with markdown
            console.print()
            console.print(Markdown(response))
            console.print()

            # Add assistant message to session
            self.session.add_message("assistant", response)
            self.session_manager.save_current()

            # Show updated session info
            self.display.show_session_info(
                self.session.id, len(self.session.messages)
            )

        except Exception as e:
            self.display.clear_thinking()
            self.display.show_error(str(e))

    def _handle_schedule(self, date_str: str) -> None:
        """Handle /schedule command."""
        import asyncio
        from backend.agent.workflows import scheduling_workflow

        date = date_str if date_str else "today"
        console.print(f"[dim]Fetching schedule for {date}...[/]")

        try:
            result = asyncio.run(
                scheduling_workflow.get_daily_schedule(self.session.id, date)
            )
            if result.success:
                console.print()
                console.print(Markdown(result.data.get("message", "No schedule found")))
                console.print()
            else:
                self.display.show_error("; ".join(result.errors))
        except Exception as e:
            self.display.show_error(str(e))

    def _handle_invoices(self) -> None:
        """Handle /invoices command."""
        import asyncio
        from backend.agent.workflows import invoice_workflow

        console.print("[dim]Fetching invoice summary...[/]")

        try:
            result = asyncio.run(invoice_workflow.get_invoice_summary(self.session.id))
            if result.success:
                console.print()
                console.print(Markdown(result.data.get("message", "No invoices found")))
                console.print()
            else:
                self.display.show_error("; ".join(result.errors))
        except Exception as e:
            self.display.show_error(str(e))

    def _handle_book(self) -> None:
        """Handle /book command with guided input."""
        console.print("[bold]Book a New Job[/bold]")
        console.print("[dim]Provide details or describe naturally in chat.[/]")
        console.print()

        # For now, redirect to chat
        console.print("[dim]You can describe the job in the chat, e.g.:")
        console.print('[dim]  "Book an AC repair for Johnson at 123 Main St tomorrow at 9am"[/]')
        console.print()

    def _handle_route(self, date_str: str) -> None:
        """Handle /route command."""
        console.print("[dim]Route optimization requires a starting location.[/]")
        console.print("[dim]Describe it in chat, e.g.:")
        console.print('[dim]  "Optimize my route for today starting from the shop"[/]')
        console.print()

    def _quit(self) -> None:
        """Exit the TUI."""
        if self.session:
            self.session_manager.save_current()
        console.print("\n[dim]Goodbye![/]\n")
        self.running = False


def start_tui(
    config_path: str | None = None,
    verbose: bool = False,
    model_override: str | None = None,
) -> None:
    """Start the interactive TUI."""
    # Handle Ctrl+C gracefully
    def signal_handler(sig: int, frame: Any) -> None:
        console.print("\n[dim]Goodbye![/]\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    tui = AgentTUI(
        config_path=config_path,
        verbose=verbose,
        model_override=model_override,
    )
    tui.run()


def run_single_prompt(
    prompt: str,
    config_path: str | None = None,
    model_override: str | None = None,
    output_format: str = "text",
    quiet: bool = False,
) -> None:
    """Run a single prompt and print the response."""
    import asyncio
    import json

    config = load_config(config_path)
    if model_override:
        config.provider.model = model_override

    if not quiet:
        console.print(f"[dim]Running: {prompt}[/]")

    try:
        from backend.agent.graph import run_agent

        result = asyncio.run(run_agent(prompt, "cli_user"))
        last_message = result["messages"][-1]
        response = last_message.content

        if output_format == "json":
            print(json.dumps({"response": response}, indent=2))
        else:
            print(response)

    except Exception as e:
        if output_format == "json":
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            console.print(f"[red]Error: {e}[/]")
        sys.exit(1)
