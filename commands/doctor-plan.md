---
description: Create a deterministic, plan-only remediation sequence from current corpus audit findings.
argument-hint: "[--sample-limit <n>]"
allowed-tools: Bash
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" doctor-plan $ARGUMENTS`.

The command does not apply remediation actions. Report the plan hash, grouped action counts, and the distinction between safe dry-run commands and review-gated apply commands. Never run an `apply_command` unless the user separately authorizes the underlying corpus change.
