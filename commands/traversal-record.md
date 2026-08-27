---
description: Apply a research run's depth, domain, robots, page, byte, and time limits and append every accepted or rejected link decision.
argument-hint: "--manifest /absolute/path/links.json --run-id ID"
allowed-tools: Bash
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" traversal-record $ARGUMENTS`. Open only links returned as `queued`; after capture, record the child observation in a subsequent traversal manifest.
