# Agent Tab Title

English | [简体中文](README.zh-CN.md)

Stop guessing which terminal tab owns which coding task. Agent Tab Title keeps iTerm2 tabs understandable when you work through SSH with many Byobu/tmux windows and parallel coding-agent sessions.

```text
task title | repository:branch*
```

- Automatic task names from Codex CLI, with an opt-in experimental Trae CLI Next adapter.
- Repository, Git branch, and dirty state in the active pane context.
- Persistent manual labels for tabs that need a human-chosen name.
- Safe defaults: raw prompts are not used as titles unless explicitly enabled.

## Why this exists

A common remote-development setup is iTerm2 on macOS, several SSH tabs, and one Byobu/tmux session per tab. Once multiple agents and shells run in parallel, the default titles all look alike. After a context switch, finding the tab for a task becomes a memory exercise.

This project turns the tab title into a compact status line:

```text
fix-title-refresh | agent-tab-title:main*
```

The left side answers “what is this tab doing?” The right side answers “where is it doing it?” An asterisk means the Git worktree has changes.

## How it works

```text
Codex/Trae lifecycle hook -> task label -> tmux window name (#W)
zsh precmd              -> repo:branch* -> pane title (#T)
tmux set-titles         -> #W | #T      -> iTerm2 tab title
```

The agent hook updates the stable task label. A zsh `precmd` hook refreshes repository context whenever the prompt returns. tmux combines both values and forwards the result to the outer terminal, including through SSH and Byobu.

This is an independent community project. It is not affiliated with or endorsed by OpenAI, ByteDance, Trae, iTerm2, tmux, or Byobu.

## Supported adapters

| Adapter | Status | Notes |
| --- | --- | --- |
| Codex CLI | Supported | Uses public lifecycle hooks; optional task-title enrichment reads the local Codex state database read-only. |
| Trae CLI Next | Experimental | Enable explicitly with `--products trae-next`. This is not the same compatibility claim as the open-source `bytedance/trae-agent` project. |

The SQLite database is an implementation detail, not a stable API. When its path or schema changes, the hook still falls back to a generic session label.

## Requirements

- macOS iTerm2 connecting to a Linux development machine, or another terminal that honors tmux titles.
- zsh and Git on the development machine.
- Byobu/tmux using its default socket, or a valid `TMUX` environment variable.
- Python 3 with the standard-library `sqlite3` module.
- A Codex CLI version with `hooks.json` lifecycle hooks.

## Quick start

Clone the repository and run:

```bash
git clone https://github.com/cheng10/agent-tab-title.git
cd agent-tab-title
python3 install.py
exec zsh
tmux source-file ~/.byobu/.tmux.conf
```

The default installation enables only Codex and does not derive a title directly from raw prompt text.

To enable the experimental Trae CLI Next adapter as well:

```bash
python3 install.py --products codex,trae-next
```

To allow sanitized prompt text as a fallback title, opt in explicitly:

```bash
python3 install.py --title-source prompt
```

To replace Byobu's numeric-only login session list with task and repository titles:

```bash
python3 install.py --byobu-picker
```

This installs a PATH-level `byobu-select-session` wrapper under `~/.local/bin`. It changes only how sessions are displayed and selected; it does not rename sessions or modify Byobu session groups.

The installer:

1. Installs files under `~/.local/bin` and `~/.config/agent-tab-title`.
2. Adds marked `source` lines to `~/.zshrc` and `~/.byobu/.tmux.conf`.
3. Merges its hook into existing hook files without deleting unrelated hooks.
4. Creates timestamped backups before modifying existing files.
5. Can be run repeatedly without duplicating configuration.

## Use

```bash
ctx                       # show the current label and auto/manual mode
ctx investigate-cache     # set a persistent manual label
ctx --auto                # return to automatic agent titles
```

Pressing `F8` also sets a manual window label. Both `ctx <label>` and the supplied F8 binding explicitly set `@ctx_manual=1`; transient titles emitted by an agent UI do not become permanently sticky.

After `ctx --auto`, submit another agent prompt to trigger the next automatic refresh.

## Naming rules

Manual mode always wins: `ctx <label>` and the supplied `F8` binding prevent later agent hooks from overwriting the window name. `ctx --auto` clears that guard.

In automatic mode, task names are resolved in this order:

1. Agent-generated rollout slug.
2. Existing stored thread title.
3. Sanitized prompt text, only with `--title-source prompt`.
4. A generic label such as `codex-789abc`.

Task labels are limited to 32 characters; the combined pane context is limited to 60 characters.

## Verify

```bash
ctx
tmux show-options -w | grep '@ctx_'
tail -n 20 ~/.cache/agent-tab-title.log
python3 -m unittest discover -s tests -v
```

Verify that:

1. The tmux window name becomes the task label.
2. The terminal tab shows `task | repository:branch*`.
3. A manual `ctx` label is not overwritten.
4. `ctx --auto` allows the next agent hook to update the label.

## Troubleshooting

**The task name is empty or stale.** Run `ctx` to check the current mode, then run `ctx --auto`. If the CLI was already running when hooks were installed, restart that CLI and submit another prompt.

**A manual title will not update automatically.** This is intentional. Run `ctx --auto`; the next agent lifecycle event will refresh it.

**Trae CLI reports that `hooks.json` moved.** The experimental adapter writes `~/.trae/cli/hooks.json`. A legacy `~/.trae/hooks.json` is not used by current Trae CLI Next versions.

**Nothing changes in tmux.** Confirm that `TMUX_PANE` is present, reload `~/.byobu/.tmux.conf`, and inspect `~/.cache/agent-tab-title.log`. Custom tmux sockets require a valid `TMUX` environment variable in the hook process.

**The SSH login session list still shows only numbers.** Install the optional picker with `python3 install.py --byobu-picker`, start a new SSH login, and confirm that `command -v byobu-select-session` resolves to `~/.local/bin/byobu-select-session`.

## Project files

| File | Purpose |
| --- | --- |
| `install.py` | Idempotent installation, backups, and hook merging. |
| `agent-tab-title.py` | Resolves task labels and updates tmux. |
| `zsh-context-title.zsh` | Adds repository context and the `ctx` command. |
| `tmux.conf` | Combines the stable task label with active-pane context. |
| `byobu-session-picker.py` | Adds task and repository context to Byobu's login session list. |
| `tests/` | Covers privacy defaults, title cleanup, and installer idempotency. |

## Privacy

Terminal titles can appear in screenshots, screen shares, shell integrations, and terminal telemetry. Safe mode is therefore the default: it uses an existing task title or generated slug but does not fall back to the raw prompt.

Prompt mode removes code blocks, URLs, email addresses, common credential markers, several token formats, and control characters. This is risk reduction, not a guarantee that arbitrary sensitive text will be detected. Do not enable prompt mode when task text may contain confidential information.

The tool reads local SQLite state in read-only mode. It never copies the database, transcript, or prompt to a network service.

## Uninstall

There is intentionally no destructive one-command uninstaller. Restore the timestamped backups reported during installation, or remove these marked source lines and the hook entries whose command contains `agent-tab-title`:

```zsh
source "$HOME/.config/agent-tab-title/zsh-context-title.zsh"
```

```tmux
source-file ~/.config/agent-tab-title/tmux.conf
```

## Known limitations

- Agent hook and SQLite formats can change between releases.
- Automatic semantic names may not be ready at the first hook; safe mode temporarily uses `codex-<session suffix>`.
- Custom tmux sockets work when `TMUX` is available to the hook; otherwise the conventional `/tmp/tmux-<uid>/default` socket is used.
- The title is a compact label and may differ from the agent UI's displayed task title.

## License

MIT. See [LICENSE](LICENSE).
