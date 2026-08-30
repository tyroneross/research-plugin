---
description: Append a timed, vendor-neutral orchestration stage event to a research run.
argument-hint: --run-id <id> --span-id <id> --stage <name> --action start|finish [--worker-id <id> --task-id <id> --receipt-path <finished-output>] [--metrics <json>]
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" run-stage $ARGUMENTS`.

Use one unique `--span-id` for each stage attempt and pass identical stage, worker, task, and model identity fields to its start and finish events. A worker stage must name a task declared by the initialized run contract. Its finish must include `--receipt-path` for the completed worker artifact; the command records that artifact's SHA-256. Pass only measured counters in `--metrics`; omit unknown token, tool, cost, or energy values instead of estimating them.
