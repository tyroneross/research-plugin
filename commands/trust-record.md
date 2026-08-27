---
description: Append dated, topic-scoped source or author trust observations without replacing prior assessments.
argument-hint: "--manifest /absolute/path/trust.json --run-id ID"
allowed-tools: Bash
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" trust-record $ARGUMENTS`. Record each trust dimension separately and cite the source observation that supports it when available.
