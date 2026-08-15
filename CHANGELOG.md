# Changelog

All notable changes to the research plugin.

## [0.6.0] — 2026-08-15

Ports three capabilities from the work-machine fork (shared release 0.5.3, canonical source on the work machine and **not present on this machine**). This is a **re-authoring from the fork's documented contract**, not a copy: the implementation was written against the fork's documented capability card, a private question-design guide, and real financial-research output exemplars (all read-only, none in this repo). Reconciliation against the actual fork source (audit suggestion #12) is **still open** — a line-level diff has not been performed, so behavioral parity with 0.5.3 is unverified.

### Added

- **`/research:optimize` and `skills/research/references/query-optimization.md`** — claim-safe query optimization. Classifies input into USER-PROVIDED FACTS / WORKING HYPOTHESES / REQUESTED TESTS / UNSUPPORTED ASSUMPTIONS; fills a decision card; identifies one or more **meta-questions** and keeps them distinct; decomposes each into MECE sub-question groups that become the output's section headings; emits section contracts (`Section | Exact question | Evidence required | Expected output | Completion rule`). Optimization levels Q0–Q4 and a 0–24 readiness score across eight dimensions with a ≥18 / 12–17 / <12 threshold table.
- **`skills/research/references/deep-orchestration.md`** — deep-research orchestration: section contracts in execution, query ledger (query · lane · host tool · date · hits · kept), source register (with exact locators and independence notes), claim register (statement · source_ids · corroboration class · confidence · basis), a distinct **reconcile** step that compares basis before value, cross-section synthesis, and per-section completion rules. Owns the workflow plane; `deep-research-architecture.md` continues to own the evidence plane (intake, parser routing, indexing, QA gates).
- **`skills/financial-research/`** — financial and operating-model research skill with `references/financial-controls.md` and `references/evidence-package-template.md`. Term authority before use, a measurement record per number (period · currency · numerator · denominator · scope · payer · beneficiary · P&L location · reported vs adjusted), a four-rung attribution ladder, cost-bucket and overlap groups, mechanism tests, margin-layer discipline, source-priority ordering (filings > expert transcripts > analyst research > AI auto-reports), duplicate control, scope-rule guardrails, a High/Medium/Low certainty rubric tied to `analyze-plan`/`analyze-run`, and an evidence-package deliverable shape ending in mandatory "Known evidence ceilings".
- **`pytest.ini` + `tests/test_contract_suites.py`** — closes audit suggestion #6. `python_files = *_check.py test_*.py` makes pytest discover the suites, and the wrapper runs each `main()` and asserts on its status. Collecting `main()` directly does **not** work: it signals failure by returning 1, and pytest passes a non-None return with only a warning — which would have turned a green no-op into a green false-pass. Proven red: with a deliberately broken contract, `pytest -q` exits 1.
- **`tests/query_optimization_contract_check.py`** and **`tests/financial_research_contract_check.py`** — deterministic contract checks: required sections and terms exist, frontmatter parses, the section-contract table carries all five columns, the readiness table carries all eight dimensions, and the new host-neutral files contain no host-specific tool names.

### Changed

- **`skills/research/SKILL.md` Phase 1 rewritten.** The prior instruction — "Research question — One clear question. Restate vague requests as specific questions." — collapsed multi-part requests into one and left no sub-question list to check coverage against (audit §3.7). Phase 1 now runs the decision card → meta-questions → MECE groups → section contracts sequence and **never merges distinct questions**. Scope, direct answer, drivers, boundaries, and confidence are evidence checks *inside* each theme, not section headings.
- Phase 2 consumes the section contracts as its source plan; Phase 4/5 check them off as the coverage summary.
- Sequential workflow is now `optimize → depth → plan → research → reconcile → synthesize → persist`.
- Workflow Detection routes query optimization, financial research, and deep orchestration.
- Depth vocabulary: this repo's `light` / `standard` / `deep` stays canonical; the fork's `quick` / `balanced` / `deep` are documented aliases (quick = light, balanced = standard).
- `CLAUDE.md`, `AGENTS.md`, `README.md` entry-point lists include `/research:optimize` and the `financial-research` skill.
- Version 0.5.2 → 0.6.0 in `package.json` / `package-lock.json` and git tag `v0.6.0`. Plugin manifests intentionally omit `version` (upstream `e970918`: auto-SHA updates; version is tracked via package.json + tag).

### Notes

- `commands/optimize.md` frontmatter carries `allowed-tools: "Bash, Read"`. Command frontmatter is a host shim and follows the convention of the 25 pre-existing commands; the command *body* and all six new markdown files are host-neutral and gated as such.

### Not changed

- `research.py` is untouched. `/research:optimize` and `/research:research` are agent command surfaces, not CLI subcommands — the boundary the fork states explicitly.

### Open

- **`skills/research/SKILL.md` is 346 lines**, over the 200-line progressive-disclosure budget. The overage is pre-existing (321 lines at 0.5.2); this release added the Phase 1 contract and pushed it further. Splitting the general-research phases into a reference is deferred.
- **Fork reconciliation (audit suggestion #12).** The work fork's `RESEARCH_CONTENT_DIR` / `RESEARCH_INDEX_DIR` split roots and its `deep_orchestration_contract_check.py` naming were not ported. A line-level diff against the fork, and a decision on the canonical lineage, remain outstanding.

## [0.5.2] — 2026-08-15

### Added

- Dual-host generalization (Claude Code + Codex). Root resolution through `RESEARCH_PLUGIN_ROOT` → `CLAUDE_PLUGIN_ROOT` → `CODEX_PLUGIN_ROOT`, with `CLAUDE_PROJECT_DIR` as the hook-path fallback.
- `PRIVACY.md`, `TERMS.md`, and Codex manifest website/privacy/terms URLs.
- `skills/research/references/deep-research-architecture.md` — deep-research evidence pipeline overlay.
- `tests/connector_policy_check.py` — asserts the host-neutral connector routing policy.

### Changed

- Command frontmatter `argument-hint` values quoted so both hosts parse them.
- `.claude/` de-tracked and gitignored.

## [0.5.1] and earlier

See git history.
