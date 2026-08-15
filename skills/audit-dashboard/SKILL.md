---
name: audit-dashboard
description: Render an evidence-led capability audit as a self-contained HTML dashboard. Use when the user asks for a dashboard, capability matrix, render the audit, audit dashboard, or compare repos/tools visually.
---

# Audit Dashboard

Render an N-subject by M-dimension capability audit into one portable HTML file.
Keep the JSON as the source of truth and treat every payload string as untrusted.

## Use this skill

Use it for capability comparisons that include:

- dimensions with a shared numeric scale;
- per-cell evidence, citations, and verification marks;
- subject health, strengths, gaps, reuse candidates, and roles;
- overlaps, cross-subject gaps, findings, a recommendation, and confidence.

Do not use it for a single metric, a decorative chart, or an audit that has no
comparable dimensions.

## Prepare the input

Read [references/schema.md](references/schema.md) before authoring JSON. Use
`data/audit.schema.json` as editor guidance; the Python validator is
authoritative.

For an existing Markdown or HTML audit report:

1. Identify the title, date, source path, scale, dimensions, and subject roster.
2. Transcribe each score exactly. Preserve its evidence and `path:line` cite.
3. Map evidence marks to `verified`, `inferred`, or `unknown`. Never strengthen
   an inference or invent a missing score.
4. Transcribe subject health, strengths, gaps, reuse candidates, and role.
5. Transcribe overlaps, cross-subject gaps, finding dispositions, recommendation
   layers, next actions, and confidence language.
6. Validate before rendering. A missing dimension or cell fails with its JSON
   path so the source gap can be resolved.

Apply [references/design-contract.md](references/design-contract.md) when
reviewing the output. Do not copy names or claims from an unrelated dashboard.

## Render

Resolve the plugin root consistently on Claude Code and Codex:

```bash
PLUGIN_ROOT="${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}"
python3 "$PLUGIN_ROOT/skills/audit-dashboard/scripts/render_dashboard.py" \
  audit.json --out audit.html
```

Validate without writing HTML:

```bash
python3 "$PLUGIN_ROOT/skills/audit-dashboard/scripts/render_dashboard.py" \
  audit.json --validate-only
```

Optionally render and serve the file locally:

```bash
python3 "$PLUGIN_ROOT/skills/audit-dashboard/scripts/render_dashboard.py" \
  audit.json --out audit.html --serve --port 8000
```

The rendered HTML inlines local CSS, uses no remote assets, and needs no build
step or JavaScript runtime.

## Verify

1. Run `--validate-only` and resolve every reported JSON path.
2. Render the file and run `python3 tests/dashboard_check.py` from the plugin
   root when this repository is available.
3. Confirm the output has Overview, Matrix, Subjects, and Findings landmarks.
4. Confirm every example score is numeric plus text, evidence expands, and all
   status and verification states include text.
5. Search asset-bearing attributes and CSS imports for remote URLs; expect none.
6. Inspect desktop and mobile widths for table-contained overflow, focus
   visibility, readable hierarchy, and at least 44px interactive targets.
