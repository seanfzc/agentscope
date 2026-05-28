#!/usr/bin/env python3
"""
AgentScope — AI Agent Permission Middleware
CLI prototype v0.1.0

Usage:
    agentscope init "task description"
    agentscope run "task description"
    agentscope status
"""

import sys
import json
import os
import time
from datetime import datetime
from pathlib import Path

VERSION = "0.1.0"
CONFIG_DIR = Path.home() / ".agentscope"
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSION_LOG = CONFIG_DIR / "sessions"

# Risk levels
RISK_LOW = "low"      # read, search, list, status
RISK_MED = "medium"   # edit, write, create, test
RISK_HIGH = "high"    # delete, push, deploy, publish, env vars
RISK_CRITICAL = "critical"  # database, auth, credentials, root

# Auto-approve rules by risk
AUTO_APPROVE = {
    RISK_LOW: True,
    RISK_MED: True,   # configurable
    RISK_HIGH: False,  # always flag
    RISK_CRITICAL: False,  # always deny
}

# Dangerous command patterns
DANGEROUS_PATTERNS = [
    ("database", ["drop", "delete", "truncate", "migrate", "seed"]),
    ("deploy", ["push", "deploy", "publish", "release", "ship"]),
    ("credentials", ["env", "secret", "token", "password", "key", "auth"]),
    ("destructive", ["rm -rf", "delete", "destroy", "nuke", "wipe"]),
    ("network", ["curl", "wget", "fetch", "http", "ssh", "scp"]),
]

def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_LOG.mkdir(parents=True, exist_ok=True)

def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {
        "auto_approve_medium": True,
        "auto_approve_high": False,
        "blocked_patterns": [],
        "sessions": 0,
    }

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def classify_risk(action: str) -> str:
    """Classify an action's risk level based on keywords."""
    action_lower = action.lower()
    
    for category, keywords in DANGEROUS_PATTERNS:
        for kw in keywords:
            if kw in action_lower:
                if category in ("database", "credentials"):
                    return RISK_CRITICAL
                elif category in ("deploy", "destructive"):
                    return RISK_HIGH
    
    # Medium risk: writing/editing
    edit_keywords = ["edit", "write", "create", "modify", "update", "add", "test", "run", "install"]
    for kw in edit_keywords:
        if kw in action_lower:
            return RISK_MED
    
    return RISK_LOW

def get_risk_emoji(risk: str) -> str:
    return {"low": "✓", "medium": "✓", "high": "⚠", "critical": "✗"}[risk]

def get_risk_color(risk: str) -> str:
    return {"low": "\033[92m", "medium": "\033[92m", "high": "\033[93m", "critical": "\033[91m"}[risk]

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

def print_header(text):
    print(f"\n{BOLD}\033[96m{text}{RESET}")

def print_action(action: str, risk: str, auto: bool):
    emoji = get_risk_emoji(risk)
    color = get_risk_color(risk)
    status = f"{color}{auto and 'auto-approved' or ('flagged' if risk == RISK_HIGH else 'DENIED')}{RESET}"
    print(f"  {color}{emoji}{RESET} {DIM}{action}{RESET} {color}({status}){RESET}")

def simulate_actions(task: str):
    """Simulate agent actions based on task description."""
    task_lower = task.lower()
    
    # Generate realistic-looking actions based on task
    actions = []
    
    # Always start with reads
    actions.extend([
        f"Read src/**/*.ts files",
        f"Grep for '{task_lower.split()[0] if task_lower.split() else 'pattern'}' in codebase",
        f"List project structure",
    ])
    
    if "auth" in task_lower or "login" in task_lower or "payment" in task_lower:
        actions.extend([
            f"Edit src/auth/login.ts",
            f"Read src/config/secrets.config.ts",
            "Run npm test -- --filter=auth",
        ])
    
    if "test" in task_lower:
        actions.append("Run npm test")
    
    if "refactor" in task_lower or "clean" in task_lower:
        actions.extend([
            "Edit src/utils/helpers.ts",
            "Edit src/services/api.ts",
            "Run npm test",
        ])
    
    if "deploy" in task_lower or "push" in task_lower:
        actions.append("Run deploy script")
    
    # Always add a push as the flagged action
    actions.append("Git push origin main")
    
    return actions

def cmd_init(task: str):
    ensure_dirs()
    cfg = load_config()
    
    print_header(f"AgentScope v{VERSION}")
    print(f"\n{DIM}Initializing permission scope...{RESET}\n")
    
    risk = classify_risk(task)
    print(f"  Task: {BOLD}{task}{RESET}")
    print(f"  Risk Profile: {get_risk_color(risk)}{risk.upper()}{RESET}")
    print(f"  Permission Scope: read, edit, test")
    
    if risk == RISK_HIGH or risk == RISK_CRITICAL:
        print(f"\n  ⚠ {get_risk_color(risk)}High-risk task detected. Manual review required for destructive actions.{RESET}")
    
    print(f"\n{DIM}Config saved to {CONFIG_FILE}{RESET}")
    cfg["sessions"] = cfg.get("sessions", 0) + 1
    save_config(cfg)

def cmd_run(task: str):
    ensure_dirs()
    cfg = load_config()
    
    print_header(f"AgentScope v{VERSION}")
    print(f"\n{DIM}Scanning task scope...{RESET}\n")
    
    task_risk = classify_risk(task)
    print(f"  {DIM}▸ Task:{RESET} {task}")
    print(f"  {DIM}▸ Risk profile:{RESET} {task_risk}")
    print(f"  {DIM}▸ Permission scope:{RESET} read, edit, test\n")
    
    actions = simulate_actions(task)
    
    auto_count = 0
    flag_count = 0
    deny_count = 0
    
    for action in actions:
        risk = classify_risk(action)
        cfg = load_config()  # re-read config each time
        
        if risk == RISK_LOW:
            auto = True
            auto_count += 1
        elif risk == RISK_MED:
            auto = cfg.get("auto_approve_medium", True)
            if auto:
                auto_count += 1
            else:
                flag_count += 1
        elif risk == RISK_HIGH:
            auto = False
            flag_count += 1
        else:  # CRITICAL
            auto = False
            deny_count += 1
        
        print_action(action, risk, auto)
        time.sleep(0.15)  # dramatic pause
    
    # Summary
    print(f"\n{DIM}{'─' * 50}{RESET}")
    print(f"  {DIM}▸ Session complete:{RESET} {auto_count} auto, {flag_count} flagged, {deny_count} denied")
    print(f"  {DIM}▸ Time saved:{RESET} ~{len(actions) * 4} seconds of approval clicks")
    
    # Log session
    session = {
        "task": task,
        "ts": datetime.now().isoformat(),
        "auto_approved": auto_count,
        "flagged": flag_count,
        "denied": deny_count,
        "actions": len(actions),
    }
    session_file = SESSION_LOG / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    session_file.write_text(json.dumps(session, indent=2))
    
    cfg = load_config()
    cfg["sessions"] = cfg.get("sessions", 0) + 1
    save_config(cfg)
    
    print(f"\n{DIM}  Session logged: {session_file}{RESET}\n")

def cmd_status():
    ensure_dirs()
    cfg = load_config()
    
    print_header(f"AgentScope v{VERSION} — Status\n")
    print(f"  {DIM}Version:{RESET} {VERSION}")
    print(f"  {DIM}Sessions:{RESET} {cfg.get('sessions', 0)}")
    print(f"  {DIM}Auto-approve medium:{RESET} {cfg.get('auto_approve_medium', True)}")
    print(f"  {DIM}Auto-approve high:{RESET} {cfg.get('auto_approve_high', False)}")
    print(f"  {DIM}Config:{RESET} {CONFIG_FILE}")
    
    # List recent sessions
    if SESSION_LOG.exists():
        sessions = sorted(SESSION_LOG.glob("*.json"), reverse=True)[:5]
        if sessions:
            print(f"\n{BOLD}  Recent Sessions:{RESET}")
            for s in sessions:
                data = json.loads(s.read_text())
                print(f"  {DIM}{data['ts']}{RESET} — {data['task'][:50]}... ({data['auto_approved']} auto, {data['flagged']} flagged)")

def main():
    if len(sys.argv) < 2:
        print(f"\n{BOLD}AgentScope v{VERSION}{RESET} — AI Agent Permissions, Without the Pain\n")
        print("Usage:")
        print("  agentscope init \"task description\"   — Initialize permission scope")
        print("  agentscope run \"task description\"     — Run with auto-approval")
        print("  agentscope status                     — Show status & history")
        print("\nDocs: https://agentscope.dev")
        print("GitHub: https://github.com/agentscope/agentscope")
        sys.exit(0)
    
    cmd = sys.argv[1]
    task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "general task"
    
    if cmd == "init":
        cmd_init(task)
    elif cmd == "run":
        cmd_run(task)
    elif cmd == "status":
        cmd_status()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
