"""agentscope CLI — AI Agent Permissions, Without the Pain."""

import json
import sys
import time
from typing import Optional

from . import __version__
from .config import Config, SecretStore
from .platform import get_config_dir, get_platform_name, is_headless, supports_ansi
from .risk_engine import (
    RiskLevel,
    RiskResult,
    ToolCall,
    classify_tool_call,
    classify_text_action,
    format_risk,
    get_risk_color,
)
from .session_log import SessionLogger


def print_header(text: str, use_ansi: bool = True):
    if use_ansi:
        print(f"\n\033[1m\033[96m{text}\033[0m")
    else:
        print(f"\n{text}")


def print_status_line(label: str, value: str, use_ansi: bool = True):
    if use_ansi:
        print(f"  \033[2m{label}:\033[0m {value}")
    else:
        print(f"  {label}: {value}")


def simulate_actions(task: str) -> list[dict]:
    """Simulate agent actions based on task description."""
    task_lower = task.lower()

    actions = [
        {"name": "read", "arguments": {"path": "src/**/*.ts"}},
        {"name": "read", "arguments": {"path": "package.json"}},
    ]

    if any(kw in task_lower for kw in ["auth", "login", "payment", "checkout"]):
        actions.extend([
            {"name": "edit", "arguments": {"path": "src/auth/login.ts", "action": "modify"}},
            {"name": "exec", "arguments": {"command": "npm test -- --filter=auth"}},
        ])
    elif any(kw in task_lower for kw in ["refactor", "clean", "optimize"]):
        actions.extend([
            {"name": "edit", "arguments": {"path": "src/utils/helpers.ts", "action": "modify"}},
            {"name": "edit", "arguments": {"path": "src/services/api.ts", "action": "modify"}},
            {"name": "exec", "arguments": {"command": "npm test"}},
        ])
    elif any(kw in task_lower for kw in ["deploy", "push", "release"]):
        actions.extend([
            {"name": "exec", "arguments": {"command": "git push origin main"}},
        ])
    elif any(kw in task_lower for kw in ["database", "db", "sql", "table", "user data"]):
        actions.extend([
            {"name": "exec", "arguments": {"command": "SELECT * FROM users LIMIT 10"}},
            {"name": "exec", "arguments": {"command": "DELETE FROM users WHERE id = 1"}},
        ])
    elif any(kw in task_lower for kw in ["test", "verify", "check"]):
        actions.extend([
            {"name": "exec", "arguments": {"command": "npm test"}},
        ])
    elif any(kw in task_lower for kw in ["secret", "key", "token", "password", "env"]):
        actions.extend([
            {"name": "exec", "arguments": {"command": "cat .env"}},
            {"name": "exec", "arguments": {"command": "echo $API_KEY"}},
        ])
    elif any(kw in task_lower for kw in ["rm", "delete", "remove", "destroy"]):
        actions.extend([
            {"name": "exec", "arguments": {"command": "rm -rf /var/data/backups"}},
        ])
    else:
        actions.extend([
            {"name": "edit", "arguments": {"path": "src/main.ts", "action": "modify"}},
            {"name": "exec", "arguments": {"command": "npm test"}},
        ])

    # Always add a push as the flagged action
    actions.append({"name": "exec", "arguments": {"command": "git push origin main"}})

    return actions


def cmd_init(task: str):
    """Initialize permission scope for a task."""
    cfg = Config.load()
    use_ansi = supports_ansi() and not is_headless()
    platform = get_platform_name()

    print_header(f"agentscope v{__version__} — Init", use_ansi)
    print()

    risk = classify_text_action(task, platform)
    risk_str = risk.level.value.upper()

    print_status_line("Task", task, use_ansi)
    print_status_line("Risk Profile", risk_str, use_ansi)
    print_status_line("Permission Scope", "read, edit, test", use_ansi)
    print_status_line("Platform", platform, use_ansi)

    if risk.level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        color = get_risk_color(risk.level, use_ansi)
        reset = "\033[0m" if use_ansi else ""
        print(f"\n  {color}⚠ High-risk task detected. Manual review required for destructive actions.{reset}")

    print()
    print_status_line("Config", str(get_config_dir() / "config.json"), use_ansi)

    cfg.sessions += 1
    cfg.save()


def cmd_run(task: str):
    """Run with auto-approval."""
    cfg = Config.load()
    use_ansi = supports_ansi() and not is_headless()
    platform = get_platform_name()
    logger = SessionLogger()

    print_header(f"agentscope v{__version__} — Run", use_ansi)
    print()

    task_risk = classify_text_action(task, platform)
    print_status_line("Task", task, use_ansi)
    print_status_line("Risk profile", task_risk.level.value, use_ansi)
    print_status_line("Platform", platform, use_ansi)
    print()

    actions = simulate_actions(task)
    auto_count = 0
    flag_count = 0
    deny_count = 0

    for action_data in actions:
        tc = ToolCall.from_dict(action_data)
        risk = classify_tool_call(tc, platform)

        # Determine action
        if risk.level == RiskLevel.CRITICAL:
            auto = False
            deny_count += 1
            decision = "deny"
        elif risk.level == RiskLevel.HIGH:
            auto = False
            flag_count += 1
            decision = "flag"
        elif risk.level == RiskLevel.MEDIUM:
            auto = cfg.auto_approve_medium
            if auto:
                auto_count += 1
                decision = "auto_approve"
            else:
                flag_count += 1
                decision = "flag"
        else:
            auto = True
            auto_count += 1
            decision = "auto_approve"

        # Check blocked patterns
        tc_text = f"{tc.name} {json.dumps(tc.arguments)}"
        for pattern in cfg.blocked_patterns:
            if pattern.lower() in tc_text.lower():
                auto = False
                deny_count += 1
                decision = "deny"
                risk = RiskResult(level=RiskLevel.CRITICAL, category="blocked", reason="Blocked pattern", action="deny")

        # Format and display
        action_str = f"{tc.name} {json.dumps(tc.arguments)}" if tc.arguments else tc.name
        print(format_risk(risk.level, action_str, auto, use_ansi))

        # Log
        logger.log_tool_call(tc.name, tc.arguments, risk.level.value, decision)

        time.sleep(0.15)  # Dramatic pause

    # Summary
    separator = "─" * 50
    print(f"\n\033[2m{separator}\033[0m" if use_ansi else f"\n{separator}")
    print_status_line("Session complete", f"{auto_count} auto, {flag_count} flagged, {deny_count} denied", use_ansi)
    print_status_line("Time saved", f"~{len(actions) * 4} seconds of approval clicks", use_ansi)

    # Verify log integrity
    valid, error = logger.verify_chain()
    if not valid:
        print(f"\n  ⚠ Log integrity check failed: {error}")

    cfg.sessions += 1
    cfg.save()


def cmd_status():
    """Show status and history."""
    cfg = Config.load()
    use_ansi = supports_ansi() and not is_headless()
    platform = get_platform_name()
    secrets = SecretStore()

    print_header(f"agentscope v{__version__} — Status", use_ansi)
    print()
    print_status_line("Version", __version__, use_ansi)
    print_status_line("Platform", platform, use_ansi)
    print_status_line("Sessions", str(cfg.sessions), use_ansi)
    print_status_line("Auto-approve medium", str(cfg.auto_approve_medium), use_ansi)
    print_status_line("Auto-approve high", str(cfg.auto_approve_high), use_ansi)
    print_status_line("Keychain available", str(secrets.is_available()), use_ansi)
    print_status_line("Config", str(get_config_dir()), use_ansi)

    # Verify log integrity
    from .platform import get_data_dir
    sessions_dir = get_data_dir() / "sessions"
    if sessions_dir.exists():
        session_files = sorted(sessions_dir.glob("*.jsonl"), reverse=True)[:5]
        if session_files:
            print(f"\n\033[1m  Recent Sessions:\033[0m" if use_ansi else "\n  Recent Sessions:")
            for sf in session_files:
                logger = SessionLogger(sf.stem)
                valid, _ = logger.verify_chain()
                integrity = "✓" if valid else "✗"
                summary = logger.get_summary()
                print(f"  {sf.stem} — {summary['total_events']} events ({integrity})")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print(f"\n\033[1magentscope v{__version__}\033[0m — AI Agent Permissions, Without the Pain\n")
        print("Usage:")
        print("  agentscope init \"task description\"   — Initialize permission scope")
        print("  agentscope run \"task description\"     — Run with auto-approval")
        print("  agentscope status                     — Show status & history")
        print("  agentscope verify                     — Verify session log integrity")
        print("\nDocs: https://observeco.ai")
        print("GitHub: https://github.com/observeco/agentscope")
        sys.exit(0)

    cmd = sys.argv[1]
    task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "general task"

    if cmd == "init":
        cmd_init(task)
    elif cmd == "run":
        cmd_run(task)
    elif cmd == "status":
        cmd_status()
    elif cmd == "verify":
        from .platform import get_data_dir
        sessions_dir = get_data_dir() / "sessions"
        if sessions_dir.exists():
            for sf in sorted(sessions_dir.glob("*.jsonl")):
                logger = SessionLogger(sf.stem)
                valid, error = logger.verify_chain()
                status = "✓ VALID" if valid else f"✗ INVALID: {error}"
                print(f"{sf.stem}: {status}")
        else:
            print("No sessions found.")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
