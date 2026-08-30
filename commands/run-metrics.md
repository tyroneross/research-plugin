---
description: Deterministically calculate research fan-out timing, critical path, merge overhead, idle gap, and reported counters.
argument-hint: --run-id <id>
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" run-metrics $ARGUMENTS`.

The output derives only from append-only stage events. Treat incomplete spans as incomplete telemetry. `reported_metric_totals` includes only counters explicitly recorded by stage finish events; absent counters remain unknown.
