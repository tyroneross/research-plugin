---
description: Verify frozen external research-evaluation artifacts, queries, hashes, and independent audit records without changing them.
argument-hint: --root <evaluation-directory> [--require-query <id>] [--min-independent-audits <n>]
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" eval-check $ARGUMENTS`.

The evaluation root must remain outside the plugin repository. Treat a missing file, hash mismatch, absent required query, malformed trial, or insufficient independent-audit count as a failed evaluation. Do not repair or rewrite frozen artifacts during this check.
