"""Cross-platform detection and configuration."""

import os
import sys
import subprocess
from pathlib import Path

try:
    from platformdirs import user_config_dir, user_data_dir
    HAS_PLATFORMDIRS = True
except ImportError:
    HAS_PLATFORMDIRS = False


def is_windows() -> bool:
    return sys.platform == "win32"


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_headless() -> bool:
    """Detect if running without TTY (Docker, CI, SSH)."""
    if not hasattr(sys.stdout, "isatty"):
        return True
    return not sys.stdout.isatty()


def get_config_dir() -> Path:
    """Get OS-standard config directory."""
    if HAS_PLATFORMDIRS:
        return Path(user_config_dir("agentscope"))
    # Fallback
    if is_windows():
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "agentscope"
    return Path.home() / ".config" / "agentscope"


def get_data_dir() -> Path:
    """Get OS-standard data directory."""
    if HAS_PLATFORMDIRS:
        return Path(user_data_dir("agentscope"))
    if is_windows():
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "agentscope"
    return Path.home() / ".local" / "share" / "agentscope"


def get_platform_name() -> str:
    if is_windows():
        return "windows"
    elif is_macos():
        return "macos"
    elif is_linux():
        return "linux"
    return "unknown"


def supports_ansi() -> bool:
    """Check if terminal supports ANSI escape codes."""
    if is_headless():
        return False
    if is_windows():
        # Windows 10+ supports ANSI, but older cmd.exe doesn't
        try:
            result = subprocess.run(
                ["ver"], capture_output=True, text=True, timeout=5
            )
            if "Windows 10" in result.stdout or "Windows 11" in result.stdout:
                return True
            return False
        except Exception:
            return False
    return True
