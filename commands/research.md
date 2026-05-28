---
description: Run the full research flow on a topic — frame, source, execute, synthesize, deliver, persist to ~/dev/research/
argument-hint: <topic-or-question>
---

Run the full structured research flow on `$ARGUMENTS`.

First classify scope:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" depth "$ARGUMENTS"
```

Use `light` for quick answers, `standard` for bounded multi-source work, and `deep` for decision-grade research that needs verification and persistence. If the user explicitly asks for a depth, that explicit request wins.

Load the `research` skill from this plugin and follow the phases appropriate to the depth:

1. **Frame** — clarify scope, success criteria, decision the research informs
2. **Source** — identify T1/T2 sources (official docs, peer-reviewed, recognized experts)
3. **Execute** — parallel WebFetch / WebSearch / Read for evidence collection
4. **Synthesize** — extract findings with citations; flag conflicts
5. **Deliver** — concise actionable summary with confidence levels
6. **Persist** — write three-layer entry (TL;DR / Notes / Raw) and call `research.py save`

If no topic was given, ask the user what they want researched.

For non-HTML sources (PDF, Excel, PPTX, Python, directories), use `/research:extract <path>` to populate the Raw section.

Other subcommands available: `/research:save`, `/research:search`, `/research:depth`, `/research:list`, `/research:link`, `/research:link-project`, `/research:sync`, `/research:index`, `/research:archive`, `/research:score`, `/research:verify`, `/research:table-profile`, `/research:db-profile`, `/research:analyze-plan`, `/research:analyze-run`, `/research:review`, `/research:compress`, `/research:extract`.
