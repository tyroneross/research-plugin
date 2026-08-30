---
description: Deterministically calculate research fan-out timing, critical path, merge overhead, idle gap, and reported counters.
argument-hint: --run-id <id>
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" run-metrics $ARGUMENTS`.

The output derives only from append-only, artifact-bound stage events. It measures the worker interval union, internal worker gaps, launch spread, explicit worker-finish-to-merge-start gap, merge wall time, and declared-span overlap separately. Treat incomplete spans as incomplete telemetry. Declared span overlap is evidence of logged orchestration overlap, not independent proof of provider-side execution. `reported_metric_totals` includes only counters explicitly recorded by stage finish events; absent counters remain unknown.
