# Agent Tab Title

Keep iTerm2 tabs understandable when you work through SSH with many Byobu/tmux windows and parallel coding-agent sessions.

```text
task title | repository:branch*
```

- The stable tmux window name comes from a Codex CLI task title or a manual `ctx` label.
- The active pane title shows the repository, Git branch, and dirty state.
- Manual labels survive later agent hooks until you run `ctx --auto`.

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

## Install

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
