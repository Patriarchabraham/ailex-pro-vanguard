"""
AILEX Pilot — secrets.py
Secure secrets management: load, store, rotate API keys.
Encrypts secrets at rest using Fernet (cryptography package) when available,
falls back to plain .env with file-permission protection.
"""
from __future__ import annotations

import base64
import hashlib
import os
import stat
from pathlib import Path
from typing import Dict, Optional

SECRETS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".ailex_secrets"
)

KNOWN_KEYS = {
    "ANTHROPIC_API_KEY":    "Claude API (required for real agents)",
    "REPLICATE_API_TOKEN":  "Replicate API (image + video generation)",
    "TOGETHER_API_KEY":     "Together AI (alternative image generation)",
    "STABILITY_API_KEY":    "Stability AI (SDXL, SD3)",
    "GITHUB_TOKEN":         "GitHub token (for PR creation)",
    "OPENAI_API_KEY":       "OpenAI API (optional, for comparison)",
}


class SecretsManager:
    """
    Manages API keys and secrets for AILEX Pilot.
    Loads from env vars, .env files, and optionally encrypted storage.
    """

    def __init__(self, secrets_file: str = SECRETS_FILE):
        self.secrets_file = secrets_file
        self._cache: Dict[str, str] = {}
        self._loaded = False

    def load_all(self) -> Dict[str, str]:
        """Load all secrets from env vars and .env files."""
        secrets: Dict[str, str] = {}

        # 1. Environment variables (highest priority)
        for key in KNOWN_KEYS:
            val = os.environ.get(key, "")
            if val:
                secrets[key] = val

        # 2. .env file in aiox-core
        for env_path in [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
            os.path.expanduser("~/.env"),
            ".env",
        ]:
            if os.path.exists(env_path):
                loaded = self._parse_env_file(env_path)
                for k, v in loaded.items():
                    if k not in secrets and v:  # don't override env vars
                        secrets[k] = v

        # 3. Encrypted secrets file
        if os.path.exists(self.secrets_file):
            encrypted = self._load_encrypted()
            for k, v in encrypted.items():
                if k not in secrets:
                    secrets[k] = v

        self._cache = secrets
        self._loaded = True

        # Inject into environment
        for k, v in secrets.items():
            os.environ.setdefault(k, v)

        return secrets

    def get(self, key: str, default: str = "") -> str:
        if not self._loaded:
            self.load_all()
        return self._cache.get(key, os.environ.get(key, default))

    def set(self, key: str, value: str, persist: bool = True) -> None:
        """Set a secret in memory and optionally persist to encrypted file."""
        self._cache[key] = value
        os.environ[key] = value
        if persist:
            self._save_encrypted({**self._cache, key: value})

    def status(self) -> str:
        if not self._loaded:
            self.load_all()
        lines = ["API Keys Status:"]
        for key, desc in KNOWN_KEYS.items():
            val = self._cache.get(key, "")
            if val:
                masked = val[:8] + "..." + val[-4:] if len(val) > 12 else "***"
                lines.append(f"  ✓ {key:30s} {masked}  ({desc})")
            else:
                lines.append(f"  ✗ {key:30s} not set  ({desc})")
        return "\n".join(lines)

    def _parse_env_file(self, path: str) -> Dict[str, str]:
        result: Dict[str, str] = {}
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, _, v = line.partition("=")
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and v:
                            result[k] = v
        except (OSError, PermissionError):
            pass
        return result

    def _get_fernet(self) -> Optional[object]:
        try:
            from cryptography.fernet import Fernet
            # Derive key from machine ID
            machine_id = self._machine_id()
            key = base64.urlsafe_b64encode(
                hashlib.sha256(machine_id.encode()).digest()
            )
            return Fernet(key)
        except ImportError:
            return None

    def _machine_id(self) -> str:
        for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            if os.path.exists(path):
                return open(path).read().strip()
        return hashlib.md5(os.path.expanduser("~").encode()).hexdigest()

    def _save_encrypted(self, data: Dict[str, str]) -> None:
        fernet = self._get_fernet()
        if fernet:
            import json
            encrypted = fernet.encrypt(json.dumps(data).encode())
            with open(self.secrets_file, "wb") as f:
                f.write(encrypted)
            # Restrict permissions to owner only
            os.chmod(self.secrets_file, stat.S_IRUSR | stat.S_IWUSR)
        else:
            # Fallback: plain text with restricted permissions
            with open(self.secrets_file, "w") as f:
                for k, v in data.items():
                    f.write(f"{k}={v}\n")
            os.chmod(self.secrets_file, stat.S_IRUSR | stat.S_IWUSR)

    def _load_encrypted(self) -> Dict[str, str]:
        fernet = self._get_fernet()
        try:
            with open(self.secrets_file, "rb") as f:
                content = f.read()
            if fernet:
                import json
                decrypted = fernet.decrypt(content)
                return json.loads(decrypted)
            else:
                return self._parse_env_file(self.secrets_file)
        except Exception:
            return {}
