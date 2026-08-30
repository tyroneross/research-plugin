---
description: Append a timed, vendor-neutral orchestration stage event to a research run.
argument-hint: --run-id <id> --span-id <id> --stage <name> --action start|finish [--worker-id <id>] [--metrics <json>]
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" run-stage $ARGUMENTS`.

Use one unique `--span-id` for each stage attempt and pass the same value to its start and finish events. Record worker, task, and model identifiers when known. On finish, pass only measured counters in `--metrics`; omit unknown token, tool, cost, or energy values instead of estimating them.
