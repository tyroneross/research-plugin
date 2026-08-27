---
description: Verify a quantitative research claim with a deterministic local calculation receipt.
argument-hint: "--spec /absolute/path/calculation.json"
allowed-tools: Bash
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" calculate $ARGUMENTS`. Accept the claim as quantitative fact only when the command returns zero and the receipt status is `passed`.
