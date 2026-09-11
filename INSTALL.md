# Installing echo (local)

echo installs from a local single-plugin marketplace. No external hosting.

## Requirements
- Claude Code
- Python 3 (standard library only; no pip packages)
- For the Ship stage: `git` and the GitHub CLI `gh` (authenticated: `gh auth login`)

## Install
In Claude Code:
```
/plugin marketplace add <repo-root>
/plugin install echo@echo-local
```
Then restart Claude Code (or `/reload-plugins`). Verify with:
```
/echo:status
```

## Use it in a repo
From inside a git repository:
```
/echo:install-hooks          # optional: block ticketless commits at the git layer
/echo:intent FEAT-1234 <what you want to build>
```
echo creates a committed `.echo/` directory to hold its artifacts and state.

Need to gather facts before you even write the intent? Run
`/echo:research <topic or TICKET> <question>` first: the `researcher` subagent writes a
grounded `research.md` (a source on every claim) that `/echo:intent` will cite. It is
optional and changes no stage or gate.

Once the plan is approved and you reach the Build stage, run `/echo:build` to have the
`builder` subagent implement the plan with a maker-checker refine loop. See `README.md`
for the `build_driver` / `maker_checker` / `approve_review` config knobs.

Prefer one command over the stage-by-stage flow? `/echo:flow <TICKET> <goal>` drives the
whole loop, auto-approving stages whose check is clean and stopping only at the gates your
`autonomy` setting keeps (`checkpoint` by default: it pauses at `plan` and `ship`).

## Uninstall
```
/plugin uninstall echo@echo-local
```

## Notes
- All `bin/` scripts must remain executable (`chmod +x bin/*`) after cloning.
- State format is JSON (`.echo/state.json`); safe to inspect and diff in git.
