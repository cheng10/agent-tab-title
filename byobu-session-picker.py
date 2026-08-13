#!/usr/bin/env python3
"""A compact Byobu/tmux session picker with useful task titles."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from typing import List, Union


ENVIRONMENT_KEYS = (
    "DISPLAY",
    "DBUS_SESSION_BUS_ADDRESS",
    "SESSION_MANAGER",
    "GPG_AGENT_INFO",
    "XDG_SESSION_COOKIE",
    "XDG_SESSION_PATH",
    "GNOME_KEYRING_CONTROL",
    "GNOME_KEYRING_PID",
    "SSH_ASKPASS",
    "SSH_AUTH_SOCK",
    "SSH_AGENT_PID",
    "WINDOWID",
)


@dataclass(frozen=True)
class Session:
    name: str
    windows: int
    attached: bool
    group: str
    task: str
    context: str


def tmux(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["tmux", *args],
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return result.stdout.rstrip("\n")


def clean(value: str) -> str:
    value = re.sub(r"[\x00-\x1f\x7f]+", " ", value).strip()
    return re.sub(r"^[\u2800-\u28ff]+\s*", "", value)


def display_width(value: str) -> int:
    width = 0
    for character in value:
        if unicodedata.combining(character):
            continue
        width += 2 if unicodedata.east_asian_width(character) in ("W", "F") else 1
    return width


def shorten(value: str, width: int) -> str:
    if display_width(value) <= width:
        return value
    result = ""
    for character in value:
        character_width = display_width(character)
        if display_width(result) + character_width + 1 > width:
            break
        result += character
    return result.rstrip() + "…"


def pad(value: str, width: int) -> str:
    return value + " " * max(0, width - display_width(value))


def read_sessions() -> List[Session]:
    output = tmux(
        "list-sessions",
        "-F",
        "#{session_name}\t#{session_windows}\t#{session_attached}\t#{session_group}",
        check=False,
    )
    sessions: List[Session] = []
    for line in output.splitlines():
        fields = line.split("\t", 3)
        if len(fields) != 4 or fields[0].startswith("_"):
            continue
        name, windows, attached, group = fields
        detail = tmux(
            "display-message",
            "-p",
            "-t",
            f"{name}:",
            "#{window_name}\t#{pane_title}",
            check=False,
        ).split("\t", 1)
        task = clean(detail[0]) if detail else ""
        context = clean(detail[1]) if len(detail) > 1 else ""
        sessions.append(
            Session(
                name=clean(name),
                windows=int(windows or "0"),
                attached=attached != "0",
                group=clean(group),
                task=task,
                context=context,
            )
        )
    return sessions


def session_label(session: Session, width: int) -> str:
    title = session.task if session.task and session.task != "-" else "untitled"
    if session.context and session.context not in title:
        title = f"{title} | {session.context}"
    state = "attached" if session.attached else "detached"
    metadata = f"[{session.windows}w {state}]"
    prefix = pad(session.name, 12) + " "
    available = max(18, width - display_width(prefix) - len(metadata) - 2)
    return f"{prefix}{pad(shorten(title, available), available)}  {metadata}"


def update_environment(name: str) -> None:
    for key in ENVIRONMENT_KEYS:
        value = os.environ.get(key)
        if value:
            subprocess.run(
                ["tmux", "setenv", "-t", name, key, value],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )


def cull_zombies(session: Session) -> None:
    if not session.group:
        return
    output = tmux(
        "list-sessions",
        "-F",
        "#{session_name}\t#{session_group}\t#{session_attached}",
        check=False,
    )
    prefix = f"_{session.name}-"
    for line in output.splitlines():
        fields = line.split("\t", 2)
        if (
            len(fields) == 3
            and fields[0].startswith(prefix)
            and fields[1] == session.group
            and fields[2] == "0"
        ):
            subprocess.run(
                ["tmux", "kill-session", "-t", fields[0]],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )


def attach(session: Session) -> None:
    update_environment(session.name)
    cull_zombies(session)
    os.execvp(
        "tmux",
        [
            "tmux",
            "-2",
            "new-session",
            "-t",
            session.name,
            "-s",
            f"_{session.name}-{os.getpid()}",
        ],
    )


def choose(sessions: List[Session], always_select: bool) -> str:
    choices: List[Union[Session, str]] = [*sessions]
    if len(sessions) > 1 or always_select:
        choices.extend(("NEW", "SHELL"))
    if len(choices) == 1:
        return "0"

    width = min(120, max(64, shutil.get_terminal_size((100, 24)).columns - 6))
    print("\nByobu sessions — task | repository context\n")
    for index, item in enumerate(choices, 1):
        if isinstance(item, Session):
            label = session_label(item, width)
        elif item == "NEW":
            label = "Create a new Byobu session"
        else:
            label = f"Run a shell without Byobu ({os.environ.get('SHELL', '/bin/sh')})"
        print(f"  {index}. {label}")

    for _ in range(3):
        try:
            answer = input(f"\nChoose 1-{len(choices)} [1]: ").strip() or "1"
        except (EOFError, KeyboardInterrupt):
            print()
            raise SystemExit(0)
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return str(int(answer) - 1)
        print("\nERROR: Invalid input", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if os.environ.get("BYOBU_BACKEND", "tmux") != "tmux":
        os.execv("/usr/bin/byobu-select-session", ["byobu-select-session"])

    sessions = read_sessions()
    config_dir = os.path.expanduser(
        os.environ.get("BYOBU_CONFIG_DIR", "~/.byobu")
    )
    always_select = os.path.exists(os.path.join(config_dir, ".always-select"))
    if not sessions:
        os.execvp("byobu", ["byobu"])

    choices: List[Union[Session, str]] = [*sessions]
    if len(sessions) > 1 or always_select:
        choices.extend(("NEW", "SHELL"))
    selected = choices[int(choose(sessions, always_select))]
    if isinstance(selected, Session):
        attach(selected)
    if selected == "NEW":
        os.execvp("byobu", ["byobu", "new-session", os.environ.get("SHELL", "/bin/sh")])
    os.execvp(os.environ.get("SHELL", "/bin/sh"), [os.environ.get("SHELL", "/bin/sh")])


if __name__ == "__main__":
    main()
