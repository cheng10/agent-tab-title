# Project context for the active pane. The stable task name is tmux #W.
autoload -Uz add-zsh-hook

_ctx_repo_name() {
    local root
    root=$(git rev-parse --show-toplevel 2>/dev/null) || {
        print -r -- "${PWD:t}"
        return
    }
    print -r -- "${root:t}"
}

_ctx_git_state() {
    local branch dirty
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || return
    branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null) || \
        branch=$(git rev-parse --short HEAD 2>/dev/null)
    if [[ -n $(git status --porcelain=v1 --untracked-files=normal 2>/dev/null | head -n 1) ]]; then
        dirty='*'
    fi
    print -r -- "${branch}${dirty}"
}

_ctx_set_pane_title() {
    local suffix="$1" repo state title
    repo=$(_ctx_repo_name)
    state=$(_ctx_git_state)
    title="$repo"
    [[ -n "$state" ]] && title="${title}:${state}"
    [[ -n "$suffix" ]] && title="${title} | ${suffix}"
    title=${title//$'\e'/}
    title=${title//$'\a'/}
    title=${title//$'\r'/ }
    title=${title//$'\n'/ }
    title=${title[1,60]}
    printf '\e]2;%s\a' "$title"
}

_ctx_precmd() {
    _ctx_set_pane_title
}

ctx() {
    if [[ -z "$TMUX" ]]; then
        echo 'ctx must be run inside Byobu/tmux'
        return 1
    fi
    if [[ "$1" == "--auto" ]]; then
        tmux set-window-option -u -t "$TMUX_PANE" @ctx_manual 2>/dev/null || true
        tmux set-window-option -t "$TMUX_PANE" @ctx_auto_owned 1
        tmux set-window-option -t "$TMUX_PANE" @ctx_auto_title \
            "$(tmux display-message -p -t "$TMUX_PANE" '#W')"
        echo 'automatic agent task titles enabled for this window'
        return
    fi
    if (( $# == 0 )); then
        local mode='auto'
        [[ "$(tmux display-message -p -t "$TMUX_PANE" '#{@ctx_manual}')" == 1 ]] && mode='manual'
        printf '%s (%s)\n' "$(tmux display-message -p -t "$TMUX_PANE" '#W')" "$mode"
        return
    fi
    local name="$*"
    name=${name//$'\r'/ }
    name=${name//$'\n'/ }
    name=${name[1,32]}
    tmux set-window-option -t "$TMUX_PANE" @ctx_manual 1
    tmux set-window-option -u -t "$TMUX_PANE" @ctx_auto_owned 2>/dev/null || true
    tmux set-window-option -u -t "$TMUX_PANE" @ctx_auto_title 2>/dev/null || true
    tmux rename-window -t "$TMUX_PANE" "$name"
}

add-zsh-hook precmd _ctx_precmd

