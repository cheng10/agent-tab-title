#!/usr/bin/env python3
"""Keep a Byobu/tmux window named after its Trae or Codex task."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MAX_TITLE = 32
SENSITIVE_OR_COMMAND = re.compile(
    r"(?i)(?:\bcurl\b|--header\b|(?:^|\s)-H\s|\bcookie\b|"
    r"\bauthorization\b|\bpassword\b|\bsecret\b|\bapi[_-]?key\b|"
    r"\baccess[_-]?token\b|\brefresh[_-]?token\b)"
)
URL = re.compile(r"https?://\S+", re.IGNORECASE)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
SECRET_VALUE = re.compile(
    r"(?i)(?:\bAKIA[0-9A-Z]{16}\b|\b(?:sk|gh[pousr])[-_][A-Za-z0-9_-]{16,}\b|"
    r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b)"
)
UUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$", re.IGNORECASE)


def tmux_binary() -> str:
    override = os.environ.get("AGENT_TAB_TITLE_TMUX_BIN", "")
    if override:
        return override

    fields = os.environ.get("TMUX", "").split(",")
    if len(fields) > 1 and fields[1].isdigit():
        server_executable = Path("/proc") / fields[1] / "exe"
        if server_executable.exists():
            # tmux clients and servers must speak the same protocol. This is
            # especially important for iTerm2 Control Mode when it is started
            # with a newer, non-PATH tmux binary.
            return str(server_executable)

    return shutil.which("tmux") or "tmux"


def tmux(*args: str, check: bool = False) -> str:
    socket = os.environ.get("TMUX", "").split(",", 1)[0]
    if not socket:
        socket = f"/tmp/tmux-{os.getuid()}/default"
    result = subprocess.run(
        [tmux_binary(), "-S", socket, *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return result.stdout.strip()


def log_error(message: str) -> None:
    try:
        path = Path.home() / ".cache" / "agent-tab-title.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")
    except Exception:
        pass


def normalize_slug(slug: str) -> str:
    value = slug.strip().replace("_", "-")
    value = re.sub(r"^(?:codex|trae)[-_]+", "", value, flags=re.I)
    value = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff.-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-.")
    return value[:MAX_TITLE].rstrip("-.")


def safe_prompt_title(prompt: str) -> str:
    if SECRET_VALUE.search(prompt):
        return ""
    value = re.sub(r"```.*?```", " ", prompt, flags=re.S)
    value = URL.sub(" ", value)
    value = EMAIL.sub(" ", value)
    marker = SENSITIVE_OR_COMMAND.search(value)
    if marker:
        value = value[: marker.start()]
    value = re.sub(r"[\x00-\x1f\x7f]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" ：:，,。.;；-|`")
    value = re.sub(r"^(?:请|帮我|麻烦)?(?:看下|看看|分析下|处理下)[:： ]*", "", value)
    if len(value) < 4:
        return ""
    return value[:MAX_TITLE].rstrip(" ：:，,。.;；-|")


def state_database(product: str) -> Path | None:
    if product == "codex":
        root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    else:
        root = Path(os.environ.get("TRAE_HOME", Path.home() / ".trae")) / "cli"
    def version(path: Path) -> int:
        match = re.search(r"state_(\d+)\.sqlite$", path.name)
        return int(match.group(1)) if match else -1

    candidates = sorted(root.glob("state_*.sqlite"), key=version, reverse=True)
    return candidates[0] if candidates else None


def read_task(product: str, session_id: str, prompt: str, title_source: str) -> str:
    db = state_database(product)
    slug = ""
    stored_title = ""
    stored_prompt = ""
    if db and db.exists() and UUID.match(session_id):
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=1)
        try:
            try:
                row = conn.execute(
                    "SELECT rollout_slug FROM stage1_outputs WHERE thread_id = ?",
                    (session_id,),
                ).fetchone()
                slug = row[0] if row and row[0] else ""
            except sqlite3.OperationalError:
                pass
            try:
                row = conn.execute(
                    "SELECT title, first_user_message FROM threads WHERE id = ?",
                    (session_id,),
                ).fetchone()
                if row:
                    stored_title = (row[0] or "").strip()
                    stored_prompt = (row[1] or "").strip()
            except sqlite3.OperationalError:
                pass
        finally:
            conn.close()
    if slug:
        return normalize_slug(slug)
    title = safe_prompt_title(stored_title)
    if not title and title_source == "prompt":
        title = safe_prompt_title(prompt or stored_prompt)
    if title:
        return title
    label = "trae" if product in ("trae", "trae-next") else product
    return f"{label}-{session_id[-6:]}" if session_id else label


def should_preserve_manual(pane: str) -> bool:
    # Only explicit commands enter manual mode. Agent UIs may emit transient
    # tmux names; inferring intent from a changed name makes them sticky.
    return tmux("display-message", "-p", "-t", pane, "#{@ctx_manual}") == "1"


def update_title(product: str, payload: dict[str, object], title_source: str) -> None:
    pane = os.environ.get("TMUX_PANE", "")
    if not pane or should_preserve_manual(pane):
        return
    session_id = str(payload.get("session_id") or "")
    prompt = str(payload.get("prompt") or "")
    title = read_task(product, session_id, prompt, title_source)
    if not title:
        return
    tmux("rename-window", "-t", pane, title, check=True)
    tmux("set-window-option", "-t", pane, "@ctx_auto_owned", "1")
    tmux("set-window-option", "-t", pane, "@ctx_auto_title", title)
    tmux("refresh-client", "-S")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--product",
        choices=("codex", "trae", "trae-next"),
        required=True,
        help="agent adapter; trae is accepted for compatibility with older installs",
    )
    parser.add_argument(
        "--title-source",
        choices=("safe", "prompt"),
        default="safe",
        help="safe avoids raw prompt text; prompt enables sanitized prompt fallback",
    )
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
        if isinstance(payload, dict):
            update_title(args.product, payload, args.title_source)
    except Exception as exc:
        log_error(f"{args.product}: {type(exc).__name__}: {exc}")
    print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
