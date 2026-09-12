#!/usr/bin/env bash
# codex-install.sh - install echo's Codex artifacts into your user-global Codex dirs.
#
# It creates PER-ENTRY symlinks (never a whole-directory link) into real directories,
# so echo's skills and agents coexist with any other Codex skills/agents you already have:
#   echo skills   -> ~/.agents/skills/echo-<name>   and   ~/.agents/skills/<template>
#   echo agents   -> ~/.codex/agents/<name>.toml
#
# Idempotent (re-running is safe), reversible (--uninstall), and non-destructive: it never
# overwrites a file or a symlink it did not create.
#
# Usage:
#   ./codex-install.sh                install the symlinks
#   ./codex-install.sh --dry-run      show what would change, write nothing
#   ./codex-install.sh --uninstall    remove only the symlinks that point back into this repo
#   ./codex-install.sh --enable-agents  also add "[agents] enabled = true" to ~/.codex/config.toml
#   ./codex-install.sh -h | --help
#
# Overrides (env): AGENTS_SKILLS_DIR, CODEX_AGENTS_DIR, CODEX_CONFIG.
#
# Note: echo is a Claude Code plugin first; this script only writes under your Codex dirs and
# never modifies the echo repo. The Codex surface is unverified in a live Codex session - see
# .agents/skills/README.md for the known limitations (advisory gates, prose-driven orchestration).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ECHO_ROOT="$SCRIPT_DIR"

SKILLS_SRC="$ECHO_ROOT/.agents/skills"
AGENTS_SRC="$ECHO_ROOT/.codex/agents"
TEMPLATES_SRC="$ECHO_ROOT/skills"

SKILLS_DST="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
AGENTS_DST="${CODEX_AGENTS_DIR:-$HOME/.codex/agents}"
CFG="${CODEX_CONFIG:-$HOME/.codex/config.toml}"

TEMPLATES="intent-template plan-template research-template spec-template"

DRY_RUN=0
UNINSTALL=0
ENABLE_AGENTS=0

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --enable-agents) ENABLE_AGENTS=1 ;;
    -h|--help) usage 0 ;;
    *) echo "codex-install: unknown option '$arg'" >&2; usage 1 >&2 ;;
  esac
done

log() { printf '%s\n' "$*"; }

# link_entry SRC DST - create DST as a symlink to SRC, safely.
link_entry() {
  local src="$1" dst="$2"
  if [ ! -e "$src" ]; then log "MISSING source, skipping: $src"; return; fi
  if [ -L "$dst" ]; then
    local cur; cur="$(readlink "$dst")"
    if [ "$cur" = "$src" ]; then log "ok (already linked): $dst"; return; fi
    log "relink: $dst  (was -> $cur)"
    [ "$DRY_RUN" -eq 1 ] || ln -sfn "$src" "$dst"
    return
  fi
  if [ -e "$dst" ]; then log "SKIP (exists, not ours): $dst"; return; fi
  log "link: $dst -> $src"
  [ "$DRY_RUN" -eq 1 ] || ln -s "$src" "$dst"
}

# unlink_entry DST - remove DST only if it is a symlink pointing back into this repo.
unlink_entry() {
  local dst="$1"
  [ -L "$dst" ] || return 0
  local cur; cur="$(readlink "$dst")"
  case "$cur" in
    "$ECHO_ROOT"/*) log "unlink: $dst"; [ "$DRY_RUN" -eq 1 ] || rm "$dst" ;;
    *) log "skip (not an echo link): $dst -> $cur" ;;
  esac
}

apply() { # apply <link|unlink>
  local op="$1" name
  # command skills: .agents/skills/echo-*
  for d in "$SKILLS_SRC"/echo-*; do
    [ -e "$d" ] || continue
    name="$(basename "$d")"
    if [ "$op" = link ]; then link_entry "$d" "$SKILLS_DST/$name"; else unlink_entry "$SKILLS_DST/$name"; fi
  done
  # template skills: link straight to the real skills/<t> (avoids a symlink-to-symlink hop)
  for t in $TEMPLATES; do
    if [ "$op" = link ]; then link_entry "$TEMPLATES_SRC/$t" "$SKILLS_DST/$t"; else unlink_entry "$SKILLS_DST/$t"; fi
  done
  # agent tomls: .codex/agents/*.toml
  for f in "$AGENTS_SRC"/*.toml; do
    [ -e "$f" ] || continue
    name="$(basename "$f")"
    if [ "$op" = link ]; then link_entry "$f" "$AGENTS_DST/$name"; else unlink_entry "$AGENTS_DST/$name"; fi
  done
}

if [ "$UNINSTALL" -eq 1 ]; then
  log "== echo Codex uninstall${DRY_RUN:+ (dry-run)} =="
  apply unlink
  log ""
  log "Left your Codex dirs and any non-echo skills untouched. Done."
  exit 0
fi

log "== echo Codex install${DRY_RUN:+ (dry-run)} =="
log "repo:    $ECHO_ROOT"
log "skills-> $SKILLS_DST"
log "agents-> $AGENTS_DST"
log ""
[ "$DRY_RUN" -eq 1 ] || { mkdir -p "$SKILLS_DST" "$AGENTS_DST"; }
apply link

if [ "$ENABLE_AGENTS" -eq 1 ]; then
  log ""
  if [ -f "$CFG" ] && grep -q '^\[agents\]' "$CFG" 2>/dev/null; then
    log "[agents] already present in $CFG - left as is"
  else
    log "append [agents] enabled = true to $CFG"
    if [ "$DRY_RUN" -ne 1 ]; then
      mkdir -p "$(dirname "$CFG")"
      printf '\n[agents]\nenabled = true\n' >> "$CFG"
    fi
  fi
fi

log ""
log "Next steps:"
log "  1. Put echo's CLIs on PATH:  export PATH=\"$ECHO_ROOT/bin:\$PATH\""
[ "$ENABLE_AGENTS" -eq 1 ] || log "  2. Enable subagents:  add [agents]\\n enabled = true to $CFG (or re-run with --enable-agents)"
log "  3. Run 'codex' and '/skills' to confirm the echo-* skills are discovered."
log "  Limitations (advisory gates, prose orchestration, unverified): $SKILLS_DST/README.md or $SKILLS_SRC/README.md"
log ""
log "These are symlinks into this repo: keep it checked out on the branch that has .agents/.codex."
