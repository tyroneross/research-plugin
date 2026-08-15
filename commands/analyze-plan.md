---
description: Create a self-contained Python analysis plan and script for quantitative/database research
argument-hint: --input <path> --question "..."
allowed-tools: Bash
---

Create a quantitative analysis run directory.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" analyze-plan $ARGUMENTS
```

This profiles declared inputs and writes:

- `analysis-plan.yaml`
- `analysis-plan.json`
- one `*.profile.json` per input
- `analysis.py`

The generated script is stdlib-only and local by default. Do not install packages or download Python code unless the user explicitly approves the environment setup.

## Metrics

The plan's `metrics:` block drives the aggregations the generated script computes. By default it is scaffolded from `--question`: "per/by X" and "top N X" phrases map to real profiled columns, `p50`/`p90`/`median` become percentiles, "error rate" becomes a truthy-share rate, and "by week/day/month" becomes a time bucket. Only columns that exist in the profile are used; phrases that match nothing are printed as `unmatched question phrase` and recorded under `metric_inference`.

When inference misses part of the question (scoped subsets, joins, custom denominators), declare metrics explicitly — this overrides inference entirely:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" analyze-plan \
  --input calls.csv --question "..." \
  --metrics '[{"name":"mcp_by_server","group_by":["subclass"],
               "filter":{"column":"surface","op":"eq","value":"mcp"},
               "aggregations":[{"name":"calls","op":"count"},
                               {"name":"error_pct","op":"rate","column":"is_error"},
                               {"name":"p90_latency_ms","op":"percentile","column":"latency_ms","q":0.9}],
               "top_n":15}]'
```

`--metrics` also accepts a path to a JSON or YAML file. Spec fields: `name`, `input`, `table` (SQLite), `group_by`, `bucket` (`{column, unit}` where unit is hour/day/week/month/year), `filter` (`eq`/`ne`/`in`/`not_in`/`contains`/`gt`/`gte`/`lt`/`lte`/`blank`/`nonblank`), `aggregations` (`count`/`share`/`count_distinct`/`rate`/`sum`/`mean`/`min`/`max`/`median`/`percentile`), `sort_by`, `sort_desc`, `top_n`. Specs are data, never evaluated as code; an invalid op is rejected at plan time and a metric naming a missing column fails the run.

Pass `--no-infer-metrics` for profiling only.

Editing `analysis.py` by hand should be a last resort — it invalidates the plan's `script_sha256` and forces `analyze-run --allow-modified-script`, which leaves `metrics:` describing something the script no longer does. Prefer `--metrics`.

Next step:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" analyze-run --plan <analysis-plan.yaml>
```

