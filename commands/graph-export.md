---
description: Export source, observation, run, entry, claim, and calculation dependencies as Mermaid or JSON.
argument-hint: "[--run-id ID] [--format mermaid|json] [--output PATH]"
allowed-tools: Bash
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" graph-export $ARGUMENTS`. Generated graphs belong under the configured research content root unless the user explicitly supplies another output path.
