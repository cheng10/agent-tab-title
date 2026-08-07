# Agent Tab Title

[English](README.md) | 简体中文

不再靠记忆猜测每个终端标签页对应哪项开发任务。Agent Tab Title 面向 iTerm2 + SSH + Byobu/tmux 的远程开发场景，让多个并行运行的 Codex CLI、Trae CLI Next 和 Shell 标签页始终清晰可辨。

```text
任务名称 | 仓库:分支*
```

- 自动获取 Codex CLI 的任务名称，并提供可选的 Trae CLI Next 实验性适配。
- 展示当前活动 pane 所在的仓库、Git 分支及未提交状态。
- 支持为特殊标签页设置持久的手动名称。
- 默认保护隐私：除非主动开启，否则不会直接使用原始 prompt 作为标题。

## 为什么需要它

一种常见的远程开发方式是：在 macOS 上使用 iTerm2，打开多个 SSH 标签页，每个标签页连接一个 Byobu/tmux session。当多个 Agent 和 Shell 并行工作时，默认标题往往几乎一模一样。稍微切换一下上下文，再想找到某项任务，就只能依赖记忆逐个翻看。

这个项目把标签页标题变成一条紧凑的状态信息：

```text
fix-title-refresh | agent-tab-title:main*
```

左侧回答“这个标签页在做什么”，右侧回答“它在哪里工作”。末尾的 `*` 表示 Git 工作区存在未提交变更。

## 工作原理

```text
Codex/Trae 生命周期 hook -> 任务名称 -> tmux window name（#W）
zsh precmd               -> 仓库:分支* -> pane title（#T）
tmux set-titles          -> #W | #T    -> iTerm2 标签页标题
```

Agent hook 负责更新相对稳定的任务名称；zsh `precmd` hook 在每次返回命令提示符时刷新仓库上下文；tmux 将两部分组合后传递给外层终端，因此经过 SSH 和 Byobu 后依然有效。

这是一个独立的社区项目，与 OpenAI、ByteDance、Trae、iTerm2、tmux 或 Byobu 没有隶属或背书关系。

## 支持情况

| 适配器 | 状态 | 说明 |
| --- | --- | --- |
| Codex CLI | 支持 | 使用公开的生命周期 hook；可选的任务名增强功能只读访问本地 Codex 状态数据库。 |
| Trae CLI Next | 实验性 | 需要通过 `--products trae-next` 显式启用；这不等同于兼容开源项目 `bytedance/trae-agent`。 |

SQLite 数据库属于实现细节，并非稳定 API。如果路径或表结构发生变化，hook 仍会回退为通用 session 名称。

## 环境要求

- macOS iTerm2 连接 Linux 开发机，或其他支持 tmux 标题的终端。
- 开发机安装 zsh 和 Git。
- Byobu/tmux 使用默认 socket，或环境中存在有效的 `TMUX` 变量。
- Python 3，并包含标准库 `sqlite3` 模块。
- Codex CLI 版本支持 `hooks.json` 生命周期 hook。

## 快速开始

克隆仓库并执行安装：

```bash
git clone https://github.com/cheng10/agent-tab-title.git
cd agent-tab-title
python3 install.py
exec zsh
tmux source-file ~/.byobu/.tmux.conf
```

默认只启用 Codex，而且不会直接从原始 prompt 生成标题。

同时启用实验性的 Trae CLI Next 适配：

```bash
python3 install.py --products codex,trae-next
```

如果确实需要将清洗后的 prompt 作为兜底标题，可显式开启：

```bash
python3 install.py --title-source prompt
```

安装器会：

1. 将文件安装到 `~/.local/bin` 和 `~/.config/agent-tab-title`。
2. 向 `~/.zshrc` 和 `~/.byobu/.tmux.conf` 添加带标记的 `source` 配置。
3. 将自身 hook 合并到已有 hook 文件，不删除无关配置。
4. 修改已有文件前创建带时间戳的备份。
5. 支持重复运行，不会重复写入配置。

## 日常使用

```bash
ctx                       # 查看当前标题和 auto/manual 模式
ctx investigate-cache     # 设置持久的手动标题
ctx --auto                # 恢复自动获取 Agent 任务名称
```

按 `F8` 也可以设置手动 window 名称。`ctx <名称>` 和自带的 F8 绑定都会显式设置 `@ctx_manual=1`，Agent UI 发出的临时标题不会意外变成永久标题。

执行 `ctx --auto` 后，再提交一条 Agent prompt，即可触发下一次自动刷新。

## 命名规则

手动模式的优先级始终最高：使用 `ctx <名称>` 或 F8 设置标题后，Agent hook 不会覆盖它；`ctx --auto` 会清除这层保护。

自动模式按以下顺序确定任务名称：

1. Agent 生成的 rollout slug。
2. 已保存的任务标题。
3. 清洗后的 prompt 文本，仅在启用 `--title-source prompt` 时使用。
4. `codex-789abc` 这类通用名称。

任务名称最多 32 个字符；组合后的 pane 上下文最多 60 个字符。

## 验证安装

```bash
ctx
tmux show-options -w | grep '@ctx_'
tail -n 20 ~/.cache/agent-tab-title.log
python3 -m unittest discover -s tests -v
```

重点确认：

1. tmux window 名称会变成任务名称。
2. 终端标签页显示 `任务名称 | 仓库:分支*`。
3. 手动设置的 `ctx` 标题不会被自动覆盖。
4. `ctx --auto` 后，下一个 Agent hook 能够更新标题。

## 常见问题

**任务名称为空或长时间没有更新。** 运行 `ctx` 检查当前模式，再执行 `ctx --auto`。如果安装 hook 时 CLI 已经在运行，请重启 CLI 并重新提交一条 prompt。

**手动标题无法自动更新。** 这是预期行为。执行 `ctx --auto`，下一个 Agent 生命周期事件会刷新标题。

**Trae CLI 提示 `hooks.json` 已迁移。** 实验性适配器写入 `~/.trae/cli/hooks.json`。当前 Trae CLI Next 不再使用旧路径 `~/.trae/hooks.json`。

**tmux 中完全没有变化。** 确认环境中存在 `TMUX_PANE`，重新加载 `~/.byobu/.tmux.conf`，并查看 `~/.cache/agent-tab-title.log`。使用自定义 tmux socket 时，hook 进程需要获得有效的 `TMUX` 环境变量。

## 项目文件

| 文件 | 用途 |
| --- | --- |
| `install.py` | 幂等安装、配置备份和 hook 合并。 |
| `agent-tab-title.py` | 解析任务名称并更新 tmux。 |
| `zsh-context-title.zsh` | 添加仓库上下文和 `ctx` 命令。 |
| `tmux.conf` | 将稳定的任务名称与活动 pane 上下文组合。 |
| `tests/` | 覆盖隐私默认值、标题清洗和安装器幂等性。 |

## 隐私说明

终端标题可能出现在截图、屏幕共享、Shell 集成和终端遥测数据中。因此，安全模式是默认设置：它使用已有任务标题或自动生成的 slug，但不会回退到原始 prompt。

Prompt 模式会移除代码块、URL、邮箱地址、常见凭据标记、若干 token 格式和控制字符。这只能降低风险，无法保证识别任意敏感内容。当任务文字可能包含机密信息时，请勿启用 prompt 模式。

工具以只读方式访问本地 SQLite 状态，不会将数据库、对话记录或 prompt 上传到任何网络服务。

## 卸载

项目有意不提供破坏性的一键卸载命令。可以恢复安装时提示的时间戳备份，或者删除以下带标记的 source 配置，以及命令中包含 `agent-tab-title` 的 hook 条目：

```zsh
source "$HOME/.config/agent-tab-title/zsh-context-title.zsh"
```

```tmux
source-file ~/.config/agent-tab-title/tmux.conf
```

## 已知限制

- Agent hook 和 SQLite 格式可能随版本变化。
- 第一次触发 hook 时，自动语义名称可能尚未生成；安全模式会临时使用 `codex-<session 后缀>`。
- 当 hook 能获取 `TMUX` 时支持自定义 tmux socket；否则使用常规的 `/tmp/tmux-<uid>/default` socket。
- 标题是经过压缩的简短标签，可能与 Agent UI 中展示的任务标题不同。

## License

MIT，详见 [LICENSE](LICENSE)。
