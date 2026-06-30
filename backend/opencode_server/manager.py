"""OpenCode process manager — one instance per user, with provider injection."""

import asyncio
import os
import shutil
import signal
import subprocess
import time
from typing import Any

from backend.config import settings

_BASE_PORT = 4097
_MAX_USERS = 50
_IDLE_TIMEOUT_SECONDS = 30 * 60


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


def _find_opencode_binary(env: dict[str, str]) -> str | None:
    """Locate the opencode binary, checking PATH and known install locations."""
    found = shutil.which("opencode", path=env.get("PATH", ""))
    if found:
        return found
    home = env.get("HOME") or os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".opencode", "bin", "opencode"),
        os.path.join(home, ".local", "bin", "opencode"),
        "/usr/local/bin/opencode",
        "/usr/bin/opencode",
        "/opt/render/project/.opencode/bin/opencode",
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


async def _install_opencode_runtime(env: dict[str, str]) -> str | None:
    """Install opencode at runtime if the build didn't do it. Returns binary path or None."""
    home = env.get("HOME") or os.path.expanduser("~")
    install_dir = os.path.join(home, ".opencode", "bin")
    try:
        proc = await asyncio.create_subprocess_shell(
            "curl -fsSL https://opencode.ai/install | bash",
            env={**env, "HOME": home},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=120)
    except Exception:
        pass
    binary = os.path.join(install_dir, "opencode")
    if os.path.isfile(binary) and os.access(binary, os.X_OK):
        return binary
    return None


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

    def get_decrypted_keys(self, user_id: str) -> dict[str, str]:
        """Return a dict of provider → plaintext API key for the given user."""
        from backend.security.encryption import decrypt_data
        result: dict[str, str] = {}
        for provider, encrypted in self._user_providers.get(user_id, {}).items():
            try:
                result[provider] = decrypt_data(encrypted)
            except Exception:
                pass
        return result

    def delete_provider_key(self, user_id: str, provider: str):
        self._user_providers.get(user_id, {}).pop(provider, None)

    def list_providers(self, user_id: str) -> list[str]:
        return list(self._user_providers.get(user_id, {}).keys())

    # ── Process lifecycle ──────────────────────────────────────────────────

    def _env_for_user(self, user_id: str) -> dict[str, str]:
        from backend.security.encryption import decrypt_data
        env = os.environ.copy()
        home = env.get("HOME") or os.path.expanduser("~")
        opencode_bin_dir = os.path.join(home, ".opencode", "bin")
        local_bin_dir = os.path.join(home, ".local", "bin")
        current_path = env.get("PATH", "")
        extra = ":".join(d for d in [opencode_bin_dir, local_bin_dir] if d not in current_path)
        if extra:
            env["PATH"] = f"{extra}:{current_path}"

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

            if not self._port_pool:
                return {"status": "failed", "error": "No available ports (server at capacity)"}

            if instance and not instance.is_running() and instance.port in self._port_pool:
                port = instance.port
                self._port_pool.remove(port)
            else:
                port = self._port_pool.pop(0)

            inst = UserOpenCodeProcess(user_id, port)
            env = self._env_for_user(user_id)

            working_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )

            app_url = getattr(settings, "app_url", None) or "https://agentdesk-v2.netlify.app"

            opencode_bin = _find_opencode_binary(env)
            if not opencode_bin:
                # Try installing at runtime (build may have failed silently)
                opencode_bin = await _install_opencode_runtime(env)

            if not opencode_bin:
                self._port_pool.append(port)
                return {
                    "status": "failed",
                    "error": (
                        "OpenCode binary not found and runtime install failed. "
                        "The server may not have internet access during startup."
                    ),
                }

            cmd = [
                opencode_bin, "serve",
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
                    stdout = inst.process.stdout.read().decode() if inst.process.stdout else ""
                    self._port_pool.append(port)
                    return {
                        "status": "failed",
                        "error": stderr or stdout or "OpenCode process exited unexpectedly",
                    }
                self._instances[user_id] = inst
                return {
                    "status": "started", "port": port,
                    "url": inst.url, "user_id": user_id,
                    "pid": inst.process.pid,
                }
            except FileNotFoundError:
                self._port_pool.append(port)
                return {"status": "failed", "error": f"OpenCode binary not executable: {opencode_bin}"}
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
