---
description: Show where the active echo work item is — stage, gates, and the next action
---

Run the echo status command and report the result to me plainly.

```
python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" status
```

Then also show the plan's "Order of work" checklist and its done/total count:

```
python3 "${CLAUDE_PLUGIN_ROOT}/bin/echo-stage" checklist
```

This fails open: if there is no active item, no recorded plan, or no checkboxes it
prints `checklist: none`, so run it unconditionally.

Then, in one or two lines, tell me the active ticket, its current stage and gate,
the checklist progress, and exactly what command I should run next.
