"""OpenCode process manager — one instance per user, with provider injection."""

import asyncio
import os
import signal
import subprocess
import time
from typing import Any

from backend.config import settings

_BASE_PORT = 4097          # Avoid clash with the default 4096
_MAX_USERS = 50
_IDLE_TIMEOUT_SECONDS = 30 * 60  # 30 minutes


class UserOpenCodeProcess:
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
        self._instances: dict[str, UserOpenCodeProcess] = {}
        self._port_pool: list[int] = list(range(_BASE_PORT, _BASE_PORT + _MAX_USERS))
        self._user_providers: dict[str, dict[str, str]] = {}
        self._lock = asyncio.Lock()

    # ── Provider key management ────────────────────────────────────────────

    def save_provider_key(self, user_id: str, provider: str, encrypted_key: str):
        if user_id not in self._user_providers:
            self._user_providers[user_id] = {}
        self._user_providers[user_id][provider] = encrypted_key

    def get_provider_keys(self, user_id: str) -> dict[str, str]:
        return self._user_providers.get(user_id, {})

    def delete_provider_key(self, user_id: str, provider: str):
        self._user_providers.get(user_id, {}).pop(provider, None)

    def list_providers(self, user_id: str) -> list[str]:
        return list(self._user_providers.get(user_id, {}).keys())

    # ── Process lifecycle ──────────────────────────────────────────────────

    def _env_for_user(self, user_id: str) -> dict[str, str]:
        from backend.security.encryption import decrypt_data

        env = os.environ.copy()
        provider_env_map = {
            "anthropic":  "ANTHROPIC_API_KEY",
            "openai":     "OPENAI_API_KEY",
            "google":     "GOOGLE_GENERATIVE_AI_API_KEY",
            "gemini":     "GOOGLE_GENERATIVE_AI_API_KEY",
            "groq":       "GROQ_API_KEY",
            "mistral":    "MISTRAL_API_KEY",
            "cohere":     "COHERE_API_KEY",
            "xai":        "XAI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "together":   "TOGETHER_AI_API_KEY",
            "fireworks":  "FIREWORKS_API_KEY",
            "perplexity": "PERPLEXITY_API_KEY",
            "deepseek":   "DEEPSEEK_API_KEY",
        }
        for provider, encrypted_key in self._user_providers.get(user_id, {}).items():
            env_var = provider_env_map.get(provider.lower())
            if env_var:
                try:
                    env[env_var] = decrypt_data(encrypted_key)
                except Exception:
                    pass
        return env

    async def get_or_start(self, user_id: str) -> dict[str, Any]:
        await self._cleanup_idle()

        async with self._lock:
            instance = self._instances.get(user_id)

            if instance and instance.is_running():
                instance.touch()
                return {"status": "running", "port": instance.port, "url": instance.url, "user_id": user_id}

            # Allocate port
            if not self._port_pool:
                return {"status": "failed", "error": "No available ports (server at capacity)"}

            # Reuse existing slot or take new port
            if instance and not instance.is_running() and instance.port in self._port_pool:
                port = instance.port
                self._port_pool.remove(port)
            else:
                port = self._port_pool.pop(0)

            inst = UserOpenCodeProcess(user_id, port)
            env = self._env_for_user(user_id)

            # Working directory = project root (where AGENTS.md lives)
            working_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )

            app_url = getattr(settings, "app_url", None) or "https://agentdesk-v2.netlify.app"
            cmd = [
                "opencode", "serve",
                "--port", str(port),
                "--hostname", inst.hostname,
                "--cors", app_url,
                "--cors", "http://localhost:3000",
            ]

            try:
                inst.process = subprocess.Popen(
                    cmd, cwd=working_dir, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                await asyncio.sleep(2)

                if inst.process.poll() is not None:
                    stderr = inst.process.stderr.read().decode() if inst.process.stderr else ""
                    self._port_pool.append(port)
                    return {"status": "failed", "error": stderr or "Process exited unexpectedly"}

                self._instances[user_id] = inst
                return {
                    "status": "started", "port": port,
                    "url": inst.url, "user_id": user_id,
                    "pid": inst.process.pid,
                }

            except FileNotFoundError:
                self._port_pool.append(port)
                return {
                    "status": "failed",
                    "error": "OpenCode binary not found. Run: curl -fsSL https://opencode.ai/install | bash",
                }
            except Exception as e:
                self._port_pool.append(port)
                return {"status": "failed", "error": str(e)}

    async def stop_user(self, user_id: str) -> bool:
        async with self._lock:
            instance = self._instances.pop(user_id, None)
            if instance:
                port = instance.port
                instance.stop()
                if port not in self._port_pool:
                    self._port_pool.append(port)
                return True
            return False

    async def status(self, user_id: str) -> dict[str, Any]:
        instance = self._instances.get(user_id)
        if not instance:
            return {"status": "not_started"}
        if not instance.is_running():
            return {"status": "stopped"}
        return {
            "status": "running",
            "port": instance.port,
            "url": instance.url,
            "pid": instance.process.pid if instance.process else None,
            "providers": self.list_providers(user_id),
        }

    def get_api_base(self, user_id: str) -> str | None:
        instance = self._instances.get(user_id)
        if instance and instance.is_running():
            instance.touch()
            return instance.url
        return None

    async def _cleanup_idle(self):
        now = time.time()
        async with self._lock:
            to_remove = [
                uid for uid, inst in self._instances.items()
                if now - inst.last_used > _IDLE_TIMEOUT_SECONDS or not inst.is_running()
            ]
        for uid in to_remove:
            await self.stop_user(uid)


opencode_manager = OpenCodeManager()
