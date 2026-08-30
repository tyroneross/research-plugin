---
description: Verify frozen external research-evaluation artifacts, queries, hashes, and independent audit records without changing them.
argument-hint: --root <evaluation-directory> [--require-query <id>] [--min-independent-audits <n>]
allowed-tools: Bash
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" eval-check $ARGUMENTS`.

The evaluation root must remain outside the plugin repository. Treat a missing file or hash, hash mismatch, control-file symlink, absent required query, malformed trial, unbound audit, duplicate audit identity/content, unexplained independence attestation, or insufficient distinct-auditor coverage as a failed evaluation. Do not repair or rewrite frozen artifacts during this check.
