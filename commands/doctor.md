---
description: Audit event-chain integrity, disk/index parity, provenance coverage, malformed entries, and duplicate slugs.
argument-hint: "[--json]"
allowed-tools: Bash
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" doctor $ARGUMENTS` and report each finding without changing legacy data. Checks cover the event chain, run provenance snapshots, disk/index parity, frontmatter and duplicate slugs, source-history completeness, whole calculation-receipt integrity, and preserved merge-attempt/input hashes. Use `/research:doctor-plan` when the user wants a deterministic remediation sequence; do not infer authorization to apply it.
