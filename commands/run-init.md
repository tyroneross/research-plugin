---
description: Validate a vendor-neutral research contract and emit one immutable task packet per research section.
argument-hint: "--contract /absolute/path/contract.json"
allowed-tools: Bash
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" run-init $ARGUMENTS`. Use the host's native agent mechanism to execute the generated packets.
