---
description: Validate and deterministically order research worker results while preserving contradictions and quantitative receipt requirements.
argument-hint: "--contract CONTRACT --result RESULT [--result RESULT] [--output PATH]"
allowed-tools: Bash
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" run-merge $ARGUMENTS`. When conflicts were discovered, include `--reconciliation <path>`; the manifest must contain the initialized `run_id`, returned `contract_hash`, and the new reconciliation records. Treat a nonzero result as a blocked synthesis, not a partial success.
