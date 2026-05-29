"""Configuration management with OS keychain support."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .platform import get_config_dir, is_windows


@dataclass
class Config:
    """agentscope configuration."""
    auto_approve_medium: bool = True
    auto_approve_high: bool = False
    blocked_patterns: list = field(default_factory=list)
    sessions: int = 0
    use_keychain: bool = True

    @classmethod
    def load(cls) -> "Config":
        """Load config from OS-standard location."""
        config_file = get_config_dir() / "config.json"
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text())
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    def save(self) -> None:
        """Save config to OS-standard location."""
        config_file = get_config_dir() / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "auto_approve_medium": self.auto_approve_medium,
            "auto_approve_high": self.auto_approve_high,
            "blocked_patterns": self.blocked_patterns,
            "sessions": self.sessions,
            "use_keychain": self.use_keychain,
        }
        config_file.write_text(json.dumps(data, indent=2))


class SecretStore:
    """Store secrets in OS keychain with plaintext fallback."""

    SERVICE_NAME = "agentscope"

    def __init__(self):
        self._keyring = None
        try:
            import keyring
            self._keyring = keyring
        except ImportError:
            pass

    def is_available(self) -> bool:
        """Check if OS keychain is available."""
        return self._keyring is not None

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret from OS keychain."""
        if not self._keyring:
            return self._get_fallback(key)
        try:
            return self._keyring.get_password(self.SERVICE_NAME, key)
        except Exception:
            return self._get_fallback(key)

    def set_secret(self, key: str, value: str) -> bool:
        """Store a secret in OS keychain."""
        if not self._keyring:
            return self._set_fallback(key, value)
        try:
            self._keyring.set_password(self.SERVICE_NAME, key, value)
            return True
        except Exception:
            return self._set_fallback(key, value)

    def delete_secret(self, key: str) -> bool:
        """Delete a secret from OS keychain."""
        if not self._keyring:
            return self._delete_fallback(key)
        try:
            self._keyring.delete_password(self.SERVICE_NAME, key)
            return True
        except Exception:
            return self._delete_fallback(key)

    def _secrets_file(self) -> Path:
        from .platform import get_data_dir
        return get_data_dir() / ".secrets.json"

    def _get_fallback(self, key: str) -> Optional[str]:
        """Fallback to encrypted file storage."""
        secrets_file = self._secrets_file()
        if not secrets_file.exists():
            return None
        try:
            data = json.loads(secrets_file.read_text())
            return data.get(key)
        except (json.JSONDecodeError, KeyError):
            return None

    def _set_fallback(self, key: str, value: str) -> bool:
        """Fallback to file storage."""
        secrets_file = self._secrets_file()
        secrets_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(secrets_file.read_text()) if secrets_file.exists() else {}
        except (json.JSONDecodeError, FileNotFoundError):
            data = {}
        data[key] = value
        secrets_file.write_text(json.dumps(data, indent=2))
        return True

    def _delete_fallback(self, key: str) -> bool:
        """Delete from file storage."""
        secrets_file = self._secrets_file()
        if not secrets_file.exists():
            return False
        try:
            data = json.loads(secrets_file.read_text())
            if key in data:
                del data[key]
                secrets_file.write_text(json.dumps(data, indent=2))
                return True
        except (json.JSONDecodeError, KeyError):
            pass
        return False
