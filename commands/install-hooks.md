---
description: Install the commit-msg git hook that blocks commits without a Jira ticket id
---

Install echo's deterministic git guardrail in the current repository.

```
python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-install-hooks"
```

Then tell me the result. This installs an idempotent, `# echo-managed` commit-msg
hook that blocks any commit whose message lacks a ticket id (`[A-Z]+-[0-9]+`), so
the organization's policy holds even when I commit outside Claude Code. It never
overwrites a hand-written hook.
