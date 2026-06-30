"""OpenCode process manager — one instance per user, with provider injection."""

import asyncio
import os
import signal
import subprocess
import time
from typing import Any

from backend.config import settings

# Base port — each user gets base + offset
_BASE_PORT = 4096
_MAX_USERS = 50
_IDLE_TIMEOUT_SECONDS = 30 * 60  # 30 minutes


class UserOpenCodeProcess:
    """A single OpenCode server process for one user."""

    def __init__(self, user_id: str, port: int):
        self.user_id = user_id
        self.port = port
        self.hostname = "127.0.0.1"
        self.process: subprocess.Popen | None = None
        self.last_used: float = time.time()

    @property
    def url(self) -> str:
        return f"http://{self.hostname}:{self.port}"

    def touch(self):
        self.last_used = time.time()

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None


class OpenCodeManager:
    """Manage per-user OpenCode server processes."""

    def __init__(self):
        # user_id -> UserOpenCodeProcess
        self._instances: dict[str, UserOpenCodeProcess] = {}
        self._port_pool: list[int] = list(range(_BASE_PORT, _BASE_PORT + _MAX_USERS))
        self._user_providers: dict[str, dict[str, str]] = {}  # user_id -> {provider: encrypted_key}

    # ------------------------------------------------------------------ #
    # Provider key management (in-memory; add Supabase persistence later) #
    # ------------------------------------------------------------------ #

    def save_provider_key(self, user_id: str, provider: str, encrypted_key: str):
        """Store an encrypted provider API key for a user."""
        if user_id not in self._user_providers:
            self._user_providers[user_id] = {}
        self._user_providers[user_id][provider] = encrypted_key

    def get_provider_keys(self, user_id: str) -> dict[str, str]:
        """Return all encrypted provider keys for a user."""
        return self._user_providers.get(user_id, {})

    def delete_provider_key(self, user_id: str, provider: str):
        """Remove a provider key."""
        if user_id in self._user_providers:
            self._user_providers[user_id].pop(provider, None)

    def list_providers(self, user_id: str) -> list[str]:
        """Return names of configured providers (no keys)."""
        return list(self._user_providers.get(user_id, {}).keys())

    # ------------------------------------------------------------------ #
    # Process lifecycle                                                    #
    # ------------------------------------------------------------------ #

    def _env_for_user(self, user_id: str) -> dict[str, str]:
        """Build environment variables with the user's provider API keys."""
        from backend.security.encryption import decrypt_data

        env = os.environ.copy()

        # Provider env var mapping
        provider_env_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_GENERATIVE_AI_API_KEY",
            "gemini": "GOOGLE_GENERATIVE_AI_API_KEY",
            "groq": "GROQ_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "cohere": "COHERE_API_KEY",
            "xai": "XAI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "together": "TOGETHER_AI_API_KEY",
            "fireworks": "FIREWORKS_API_KEY",
            "perplexity": "PERPLEXITY_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "azure": "AZURE_API_KEY",
        }

        for provider, encrypted_key in self._user_providers.get(user_id, {}).items():
            env_var = provider_env_map.get(provider.lower())
            if env_var:
                try:
                    env[env_var] = decrypt_data(encrypted_key)
                except Exception:
                    pass  # Skip invalid/corrupted keys

        return env

    async def get_or_start(self, user_id: str) -> dict[str, Any]:
        """Get or start an OpenCode instance for this user."""
        # Clean up idle instances first
        await self._cleanup_idle()

        instance = self._instances.get(user_id)

        if instance and instance.is_running():
            instance.touch()
            return {
                "status": "running",
                "port": instance.port,
                "url": instance.url,
                "user_id": user_id,
            }

        # Allocate a port
        if not self._port_pool:
            return {"status": "failed", "error": "No available ports (too many active users)"}

        # Reuse existing port slot if user had one
        if instance and not instance.is_running():
            port = instance.port
        else:
            port = self._port_pool.pop(0)

        inst = UserOpenCodeProcess(user_id, port)
        env = self._env_for_user(user_id)

        # Find the project working directory (where AGENTS.md lives)
        working_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        cmd = [
            "opencode",
            "serve",
            "--port", str(port),
            "--hostname", inst.hostname,
            "--cors", settings.app_url or "https://agentdesk-v2.netlify.app",
            "--cors", "http://localhost:3000",
        ]

        try:
            inst.process = subprocess.Popen(
                cmd,
                cwd=working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            await asyncio.sleep(2)

            if inst.process.poll() is not None:
                stderr = inst.process.stderr.read().decode() if inst.process.stderr else ""
                if port not in self._port_pool:
                    self._port_pool.append(port)
                return {"status": "failed", "error": stderr or "OpenCode process exited unexpectedly"}

            self._instances[user_id] = inst
            return {
                "status": "started",
                "port": port,
                "url": inst.url,
                "user_id": user_id,
                "pid": inst.process.pid,
            }

        except FileNotFoundError:
            if port not in self._port_pool:
                self._port_pool.append(port)
            return {
                "status": "failed",
                "error": "OpenCode binary not found. Install with: curl -fsSL https://opencode.ai/install | bash",
            }
        except Exception as e:
            if port not in self._port_pool:
                self._port_pool.append(port)
            return {"status": "failed", "error": str(e)}

    async def stop_user(self, user_id: str) -> bool:
        """Stop a user's OpenCode instance."""
        instance = self._instances.pop(user_id, None)
        if instance:
            port = instance.port
            instance.stop()
            if port not in self._port_pool:
                self._port_pool.append(port)
            return True
        return False

    async def status(self, user_id: str) -> dict[str, Any]:
        """Get the status of a user's OpenCode instance."""
        instance = self._instances.get(user_id)
        if not instance:
            return {"status": "not_started"}
        if not instance.is_running():
            return {"status": "stopped"}
        return {
            "status": "running",
            "port": instance.port,
            "url": instance.url,
            "pid": instance.process.pid,
            "providers": self.list_providers(user_id),
        }

    def get_api_base(self, user_id: str) -> str | None:
        """Get OpenCode API base URL for a user."""
        instance = self._instances.get(user_id)
        if instance and instance.is_running():
            instance.touch()
            return instance.url
        return None

    async def _cleanup_idle(self):
        """Stop instances that have been idle too long."""
        now = time.time()
        to_remove = [
            uid for uid, inst in self._instances.items()
            if now - inst.last_used > _IDLE_TIMEOUT_SECONDS or not inst.is_running()
        ]
        for uid in to_remove:
            await self.stop_user(uid)


# Singleton
opencode_manager = OpenCodeManager()
