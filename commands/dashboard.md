---
description: Render a capability audit JSON file as a self-contained HTML dashboard
argument-hint: <audit.json> [--out path] [--serve [--port N]]
allowed-tools: Bash
---

Render `$ARGUMENTS` with the `audit-dashboard` skill.

Treat the first positional argument as the audit JSON path. If `--out` is not
provided, derive `<audit-stem>.html` beside the input. Preserve `--serve` and
`--port` when supplied.

Resolve the plugin root on either host:

```bash
PLUGIN_ROOT="${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}"
```

Validate first:

```bash
python3 "$PLUGIN_ROOT/skills/audit-dashboard/scripts/render_dashboard.py" \
  "<audit.json>" --validate-only
```

Then render with the resolved paths:

```bash
python3 "$PLUGIN_ROOT/skills/audit-dashboard/scripts/render_dashboard.py" \
  "<audit.json>" --out "<output.html>"
```

If validation fails, report the precise JSON path and do not render. On success,
return the output path. Do not add remote assets or rewrite audit claims while
rendering.
