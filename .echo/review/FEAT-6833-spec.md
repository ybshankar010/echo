# Critic re-check: FEAT-6833 spec (revised)

Verdict: no blocking gaps. All prior findings resolved.

- Blocker (recap): resolved. Req 5, Design, and Non-goals state recap is deterministic bin/echo-capture output and out of scope. No bin/ change implied.
- Em-dash AC: resolved. Criterion 8 scopes to added lines.
- Codex parity: resolved. Verified template mirrors are symlinks; echo-ship, echo-review, echo-address-review are real dirs; criterion 5 lists all three plus the new symlink.
- Commit/PR -m: resolved. Req 4 and Design match.
- Nits: resolved. smoke.sh template loop at ~lines 115-117 uses test -e; plugin.json is 0.6.0 so 0.7.0 is correct; criteria use grep -l.

Remaining nits (non-blocking):
1. Criterion 8 uses git diff, which omits untracked new files (skills/ste-writing/SKILL.md) unless staged. Run after git add, or use git diff HEAD plus a direct grep on the new file.
2. grep -c exits 1 when the count is 0; read the printed count, not the exit code.
