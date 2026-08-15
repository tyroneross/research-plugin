---
description: Run the full research flow on a topic — frame, source, execute, synthesize, deliver, persist to ~/dev/research/
argument-hint: <topic-or-question>
allowed-tools: Bash, WebSearch, WebFetch, Read, Write
---

Run the full structured research flow on `$ARGUMENTS`.

First classify scope:

```bash
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" depth "$ARGUMENTS"
```

Use `light` for quick answers, `standard` for bounded multi-source work, and `deep` for decision-grade or explicitly thorough/expansive research that needs verification and persistence. If the user explicitly asks for a depth, that explicit request wins.

Load the `research` skill from this plugin and follow the phases appropriate to the depth:

1. **Frame** — clarify scope, success criteria, decision the research informs
2. **Source** — map primary/original, independent, counter-evidence, temporal/currentness, and gap lanes before fetching
3. **Execute** — use local coding tools first for codebase evidence. On Codex, use the on-device Browser for public HTML and the structured `web__run` search/open connector as backup; on Claude Code, use WebSearch / WebFetch. Keep a source register with tier, date, role, independence notes, and extraction/provenance notes when parsing files. Invoke backup connectors through their published schema, retry one minimal valid request after an invocation error, and never build an ad-hoc connector wrapper.
4. **Synthesize** — extract findings with citations; flag conflicts, missing lanes, and strongest counter-evidence
5. **Deliver** — concise actionable summary with confidence levels
6. **Persist** — write three-layer entry (TL;DR / Notes / Raw) and call `research.py save`

If no topic was given, ask the user what they want researched.

For non-HTML sources (PDF, Excel, PPTX, Python, directories), use `/research:extract <path>` to populate the Raw section. For expansive deep research, mixed files, or reusable source indexing, also apply `skills/research/references/deep-research-architecture.md` so the run captures parser routing, normalized evidence records, search/fetch readiness, and QA gates before synthesis.

Other subcommands available: `/research:save`, `/research:search`, `/research:depth`, `/research:list`, `/research:link`, `/research:link-project`, `/research:sync`, `/research:index`, `/research:archive`, `/research:score`, `/research:verify`, `/research:table-profile`, `/research:db-profile`, `/research:analyze-plan`, `/research:analyze-run`, `/research:review`, `/research:compress`, `/research:extract`.
