"""OpenCode process manager - starts and manages OpenCode server instances."""

import asyncio
import os
import signal
import subprocess
from pathlib import Path
from typing import Any

from backend.config import settings


class OpenCodeManager:
    """Manage OpenCode server processes."""

    def __init__(self):
        self.process: subprocess.Popen | None = None
        self.port: int = 4096
        self.hostname: str = "127.0.0.1"
        self.password: str | None = None
        self.working_directory: str = os.getcwd()

    async def start(
        self,
        port: int = 4096,
        hostname: str = "127.0.0.1",
        password: str | None = None,
        working_dir: str | None = None,
    ) -> dict[str, Any]:
        """Start the OpenCode server."""
        if self.process and self.process.poll() is None:
            return {
                "status": "already_running",
                "port": self.port,
                "hostname": self.hostname,
                "url": f"http://{self.hostname}:{self.port}",
            }

        self.port = port
        self.hostname = hostname
        self.password = password
        self.working_directory = working_dir or os.getcwd()

        env = os.environ.copy()
        if password:
            env["OPENCODE_SERVER_PASSWORD"] = password

        cmd = [
            "opencode",
            "serve",
            "--port", str(port),
            "--hostname", hostname,
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=self.working_directory,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait a moment for server to start
            await asyncio.sleep(2)

            if self.process.poll() is not None:
                stderr = self.process.stderr.read().decode() if self.process.stderr else ""
                return {
                    "status": "failed",
                    "error": stderr or "Process exited unexpectedly",
                }

            return {
                "status": "started",
                "port": self.port,
                "hostname": self.hostname,
                "url": f"http://{self.hostname}:{self.port}",
                "pid": self.process.pid,
            }

        except FileNotFoundError:
            return {
                "status": "failed",
                "error": "OpenCode binary not found. Install with: curl -fsSL https://opencode.ai/install | bash",
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def stop(self) -> bool:
        """Stop the OpenCode server."""
        if self.process and self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            return True
        return False

    async def status(self) -> dict[str, Any]:
        """Get the status of the OpenCode server."""
        if self.process is None:
            return {"status": "not_started"}

        if self.process.poll() is not None:
            return {"status": "stopped", "exit_code": self.process.returncode}

        return {
            "status": "running",
            "port": self.port,
            "hostname": self.hostname,
            "url": f"http://{self.hostname}:{self.port}",
            "pid": self.process.pid,
        }

    def get_api_base(self) -> str:
        """Get the base URL for the OpenCode API."""
        return f"http://{self.hostname}:{self.port}"


# Singleton
opencode_manager = OpenCodeManager()
