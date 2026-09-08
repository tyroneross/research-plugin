# Quantitative and Database Analysis

Use this workflow when research requires calculations, table/database inspection, SQL reasoning, or quantitative claims that should not be computed mentally by the LLM.

## Core Rule

The LLM frames the analysis. Code performs the calculation. This applies to every derived number across all research methods, including percentages in prose, comparisons, forecasts, meta-analysis, simulations and financial models. Faithfully quoting a source number needs attribution; deriving a new number needs execution evidence.

Prefer the existing `research.py calculate --spec <spec.json>` for supported formulas with registered source observations. For tables and databases, use `table-profile` / `db-profile`, then `analyze-plan` and `analyze-run`. The generated script performs profiling only: customize a reviewed Python script for actual estimators, simulations, optimization or other complex calculations. Never describe the profiling scaffold as having answered the requested analytical question.

Keep the input provenance, formula/query, units, denominator, script/spec hash, command, exit status, output and validation checks together. Label results as quoted, computed and validated, computed but unvalidated, estimates, or inconclusive. Execution cannot turn an assumed input into an observed fact.

For complex calculations, validate with a known-answer case or an independent method; check units, denominators, bounds and reconciliation. Add sensitivity analysis, uncertainty estimates, convergence checks and fixed random seeds where the method requires them. Record failed checks rather than suppressing them. Do not call self-reported confidence a statistical confidence interval.

When data or computation is unavailable or forbidden, return the formula and missing inputs or an analysis plan. Do not fabricate a calculated result. Prefer stdlib; use preinstalled scientific libraries when their established algorithms materially reduce implementation risk, recording versions and the reason.

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

- `analysis-plan.yaml` — inputs, profiles, assumptions, metrics scaffold, validations, certainty rubric.
- `analysis.py` — self-contained stdlib Python script generated from the profile.

The generated script should be auditable and conservative. It should compute only generic profile summaries unless the analysis plan has explicit metric definitions.

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
- If a script is edited for custom metrics, review the diff and use `analyze-run --allow-modified-script` only after confirming the edit is intentional and within the authorized analysis. This flag acknowledges the hash change; it is not a sandbox or an automatic request for user permission.

If additional libraries are needed, first check the existing environment. Any new environment setup must follow the host permission policy and user constraints. Do not install packages automatically.

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
