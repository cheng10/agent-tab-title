#!/usr/bin/env python3
"""Idempotent installer for Agent Tab Title Kit."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOME = Path.home()
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
SCRIPT = HOME / ".local" / "bin" / "agent-tab-title"
CONFIG_DIR = HOME / ".config" / "agent-tab-title"


def backup(path: Path) -> None:
    if path.exists():
        target = path.with_name(f"{path.name}.agent-tab-title-backup-{STAMP}")
        shutil.copy2(path, target)
        print(f"backup: {target}")


def install_file(source: Path, target: Path, executable: bool = False) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() == source.read_bytes():
        print(f"unchanged: {target}")
        return
    backup(target)
    shutil.copy2(source, target)
    if executable:
        target.chmod(target.stat().st_mode | stat.S_IXUSR)
    print(f"installed: {target}")


def ensure_line(path: Path, marker: str, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in text:
        print(f"configured: {path}")
        return
    backup(path)
    separator = "" if not text or text.endswith("\n") else "\n"
    path.write_text(f"{text}{separator}\n{marker}\n{line}\n", encoding="utf-8")
    print(f"updated: {path}")


def hook_command(product: str, title_source: str) -> dict[str, object]:
    python = shutil.which("python3") or sys.executable
    command = " ".join(
        shlex.quote(part)
        for part in (
            python,
            str(SCRIPT),
            "--product",
            product,
            "--title-source",
            title_source,
        )
    )
    return {
        "type": "command",
        "command": command,
        "timeout": 3,
    }


def merge_hooks(path: Path, product: str, title_source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Refusing to modify invalid JSON {path}: {exc}")
    else:
        data = {}
    hooks = data.setdefault("hooks", {})
    changed = False
    for event in ("SessionStart", "UserPromptSubmit", "Stop"):
        entries = hooks.setdefault(event, [])
        found = False
        for entry in entries:
            for item in entry.get("hooks", []):
                if "agent-tab-title" in str(item.get("command", "")):
                    desired = hook_command(product, title_source)
                    if any(item.get(key) != value for key, value in desired.items()):
                        item.update(desired)
                        changed = True
                    found = True
        if not found:
            entry: dict[str, object] = {"hooks": [hook_command(product, title_source)]}
            if event == "SessionStart":
                entry["matcher"] = "startup|resume"
            entries.append(entry)
            changed = True
    if changed:
        backup(path)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"updated: {path}")
    else:
        print(f"configured: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--products",
        default="codex",
        help="comma-separated adapters: codex,trae-next (default: codex)",
    )
    parser.add_argument(
        "--title-source",
        choices=("safe", "prompt"),
        default="safe",
        help="safe avoids raw prompt titles; prompt enables sanitized prompt fallback",
    )
    args = parser.parse_args()
    products = {item.strip() for item in args.products.split(",") if item.strip()}
    unknown = products - {"codex", "trae-next"}
    if unknown or not products:
        parser.error(f"invalid --products value: {','.join(sorted(unknown or products))}")

    install_file(ROOT / "agent-tab-title.py", SCRIPT, executable=True)
    install_file(ROOT / "zsh-context-title.zsh", CONFIG_DIR / "zsh-context-title.zsh")
    install_file(ROOT / "tmux.conf", CONFIG_DIR / "tmux.conf")
    ensure_line(
        HOME / ".zshrc",
        "# agent-tab-title-kit",
        'source "$HOME/.config/agent-tab-title/zsh-context-title.zsh"',
    )
    ensure_line(
        HOME / ".byobu" / ".tmux.conf",
        "# agent-tab-title-kit",
        "source-file ~/.config/agent-tab-title/tmux.conf",
    )
    if "codex" in products:
        merge_hooks(HOME / ".codex" / "hooks.json", "codex", args.title_source)
    if "trae-next" in products:
        merge_hooks(
            HOME / ".trae" / "cli" / "hooks.json",
            "trae-next",
            args.title_source,
        )
    print("\nReload with: exec zsh")
    print("Inside Byobu/tmux: tmux source-file ~/.byobu/.tmux.conf")


if __name__ == "__main__":
    main()
