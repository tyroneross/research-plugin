---
description: Rebuild the overall source ledger and central per-project research indexes outside the plugin repository.
allowed-tools: Bash
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" source-index` and return the generated paths.
