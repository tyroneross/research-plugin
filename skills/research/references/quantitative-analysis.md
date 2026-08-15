# Quantitative and Database Analysis

Use this workflow when research requires calculations, table/database inspection, SQL reasoning, or quantitative claims that should not be computed mentally by the LLM.

## Core Rule

The LLM frames the analysis. Code performs the calculation.

For quantitative work, never rely on mental arithmetic when a local script can compute the result. The LLM should:

1. Assess the data and question.
2. Define the analysis plan, formulas, filters, joins, and assumptions.
3. Generate or use a deterministic Python script.
4. Run the script and inspect artifacts.
5. Report findings with High / Medium / Low certainty.

## Workflow

### Phase 1: Assess

Before writing code, identify:

- **Question** — the exact quantitative question.
- **Input type** — CSV/TSV/JSON/SQLite/database table/extracted table text.
- **Grain** — one row per what? User, session, account, day, transaction, etc.
- **Schema** — column names, types, nullable fields, primary keys, foreign keys when available.
- **Metric definitions** — formulas, denominators, filters, date windows, grouping dimensions.
- **Known risks** — OCR/table extraction, missing values, duplicate rows, unit mismatch, join cardinality, stale data.

If the grain, denominator, or join relationship is unknown, mark the analysis as Medium or Low certainty until resolved.

### Phase 2: Profile

Use `research.py table-profile` or `research.py db-profile` to produce a deterministic profile before analysis.

Profile output should include:

- Row counts.
- Column names.
- Inferred column types.
- Null/blank counts.
- Numeric min/max/mean where applicable.
- Distinct counts for low-cardinality columns.
- Sample rows.
- SQLite table names, schemas, row counts, foreign keys, and indexes for databases.

### Phase 3: Plan

Use `research.py analyze-plan --input <path> --question "..."` to create an analysis run directory with:

- `analysis-plan.yaml` — inputs, profiles, assumptions, metric specs, validations, certainty rubric.
- `analysis.py` — self-contained stdlib Python script generated from the profile.

The generated script is auditable and conservative: it computes exactly the aggregations declared in the plan's `metrics:` block and nothing else. Metric specs are data, never evaluated as code.

`analyze-plan` scaffolds `metrics:` from the question. It maps "per/by X" and "top N X" phrases to columns that exist in the profile, turns `p50`/`p90`/`median` into percentiles, "error rate" into a truthy-share rate, and "by week/day/month" into a time bucket. Phrases it cannot map to a real column are printed and recorded under `metric_inference.unmatched` rather than guessed at.

**Always read back the scaffolded metrics before trusting the run.** Inference cannot derive filters, joins, or custom denominators. When it misses part of the question — a scoped subset such as "per-mcp-server", a non-default denominator, a derived column — declare metrics explicitly with `--metrics` (inline JSON or a JSON/YAML file), which replaces inference:

```json
[{"name": "mcp_by_server",
  "group_by": ["subclass"],
  "filter": {"column": "surface", "op": "eq", "value": "mcp"},
  "aggregations": [{"name": "calls", "op": "count"},
                   {"name": "error_pct", "op": "rate", "column": "is_error"},
                   {"name": "p90_latency_ms", "op": "percentile", "column": "latency_ms", "q": 0.9}],
  "top_n": 15}]
```

Spec fields: `name`, `input`, `table` (SQLite), `group_by`, `bucket` (`{column, unit}`; unit ∈ hour/day/week/month/year), `filter` (`eq`/`ne`/`in`/`not_in`/`contains`/`gt`/`gte`/`lt`/`lte`/`blank`/`nonblank`), `aggregations` (`count`/`share`/`count_distinct`/`rate`/`sum`/`mean`/`min`/`max`/`median`/`percentile`), `sort_by`, `sort_desc`, `top_n`.

Semantics worth stating in any writeup: percentiles are nearest-rank (`rank = ceil(q × n)`, no interpolation) over rows whose value parses as a number, so `coverage` reports the denominator; `rate` counts truthy values over all rows in the group unless `"denominator": "nonblank"` is set; `share` is the group's share of scoped rows.

Prefer `--metrics` over hand-editing `analysis.py`. A hand-edit invalidates `script_sha256`, forces `analyze-run --allow-modified-script`, and leaves `metrics:` describing something the script no longer does — the plan stops being an accurate record of the analysis.

Use `--no-infer-metrics` when a profiling-only pass is genuinely what you want.

### Phase 4: Run

Use `research.py analyze-run --plan <analysis-plan.yaml>` to execute the script.

The run writes:

- `results.json` — machine-readable calculations and validation status.
- `audit.md` — human-readable summary with certainty assessment.

### Phase 5: Synthesize

Every quantitative finding must include:

- The number.
- Formula or SQL query used.
- Source input path/table.
- Validation outcome.
- Certainty: High / Medium / Low.
- Limitations.

Do not upgrade a quantitative claim above the certainty of its weakest required input.

## Certainty Rubric

| Certainty | Use When |
|---|---|
| High | Structured source data; schema understood; deterministic formula or SQL; row counts reconcile; validations pass; no major assumptions. |
| Medium | Structured data but some assumptions remain; partial schema ambiguity; missing values handled; manual column mapping; validation is partial. |
| Low | OCR/PDF/table extraction; ambiguous grain or denominator; uncertain joins; important missing values; unvalidated transformations; source is weak or stale. |

## Python Safety Rules

Generated analysis scripts must be local, self-contained, and stdlib-only by default.

- Do not install packages automatically.
- Do not download code.
- Do not call external network APIs.
- Do not read files outside the declared inputs.
- Do not write outside the run directory.
- Run with a timeout.
- Store script, plan, result, and audit artifacts together for inspection.
- Record and verify the generated script hash before execution.
- If a script is edited for custom metrics, review the diff and require an explicit override before running.

If non-stdlib libraries are genuinely needed, state the reason and require an explicit user-approved environment setup. Prefer preinstalled, well-known libraries only when they materially reduce risk or complexity.

## Database / SQL Rules

For databases:

1. Profile schema before querying.
2. List tables, columns, primary keys, indexes, row counts, and foreign keys.
3. Define join keys and expected cardinality before joining.
4. Use read-only connections for analysis.
5. Prefer SQL for filtering/grouping/aggregation, Python for result validation and formatting.
6. Include every query used in `audit.md`.

Certainty should be downgraded when joins are inferred, tables lack primary keys, or row counts change between profile and run.

## Output Pattern

```markdown
## Quantitative Finding

**Finding:** [metric and value]
**Formula / SQL:** [calculation]
**Input:** [path/table]
**Validation:** [passed / partial / failed]
**Certainty:** [High / Medium / Low] — [reason]
**Limitations:** [open risks]
```
