# Changelog

## Unreleased

- Add validated research-method routing with independent depth, source, computation, execution and persistence controls; preserve tentative raw-query hints.
- Require executed scripts and meaningful validation for derived quantities; label the generated analysis scaffold as profiling-only.
- Update the README and method guidance; replace personal file examples and stop tracking local Build Loop snapshots.

## Unreleased

- Added append-only run and event history, normalized source observations, graph-ready entities and relationships, topic-scoped trust observations, and source/dependency index exports.
- Added deterministic calculation receipts. Quantitative claims now require source-linked inputs, units, denominator, grain, assumptions, hashes, local runtime metadata, and passing validation checks; ambiguity returns `inconclusive`.
- Added a vendor-neutral `research-orchestrator` skill for hypothesis/falsifier framing, bounded second-/third-level link traversal, host-native parallel task packets, and contradiction-preserving merge validation.
- Added bounded local hook status logging and a `doctor` command for chain integrity, disk/index parity, provenance coverage, malformed entries, and duplicate slugs.
- Added an optional macOS Apple Vision OCR adapter. The core runtime remains host- and vendor-neutral.
- Added a frozen-evaluation verifier for external historical trials and independent audit artifacts; repository fixtures remain synthetic.
- Added append-only orchestration stage telemetry with deterministic overlap, maximum concurrency, critical-path, merge, handoff/idle, and reported-counter calculations.
- Added a hashed, plan-only doctor remediation command that groups corpus defects and keeps every apply action review-gated.
- Normalized verifier and CLI argument contracts so `research.py` static analysis reports no errors without requiring optional SymPy at import time.

All notable changes to the research plugin.

## [0.6.1](https://github.com/tyroneross/research-plugin/compare/research-plugin-v0.6.0...research-plugin-v0.6.1) (2026-09-06)


### Features

* add auditable research orchestration ([deffb05](https://github.com/tyroneross/research-plugin/commit/deffb059281c4d77b79231dfb803e82b4ab00cd5))
* **dashboard:** v2 — recommended flow first, pipelines today, stage-grouped comparison with pop-out evidence ([690aefc](https://github.com/tyroneross/research-plugin/commit/690aefcc6481a3896a45abab64d3456f6557877b))
* **dashboard:** v2 payload + review fixes — coordinator framing, reference pipelines, per-stage optimal table ([7db776b](https://github.com/tyroneross/research-plugin/commit/7db776b1512fdf388ea0b46b5355b50411049314))
* **doctor:** emit deterministic remediation plans ([27b1c0a](https://github.com/tyroneross/research-plugin/commit/27b1c0a131d3698557c90a8ff7bafc5e2b25e865))
* **eval:** verify frozen external research trials ([f93a349](https://github.com/tyroneross/research-plugin/commit/f93a349f96fdc5c9243ca84656d2faeedc1cf3c9))
* **intake:** add register_source helper and capture-sizing rule ([67c58cd](https://github.com/tyroneross/research-plugin/commit/67c58cdf622cefee0866fad7deff8188377e181e))
* **plugin:** route feedback to GitHub Issues, drop the inbox ([ade65fa](https://github.com/tyroneross/research-plugin/commit/ade65fa8ced7110251d9db02deb593e9b325e5c0))
* **runs:** measure fanout execution stages ([a8a20f3](https://github.com/tyroneross/research-plugin/commit/a8a20f3af589caf53745a7950e700e404ad15195))
* **save:** add non-blocking provenance and topic-scatter guards ([4c7cc90](https://github.com/tyroneross/research-plugin/commit/4c7cc9030293759e3241530545c4a1637a889915))


### Bug Fixes

* **audit:** bind fanout and evaluation evidence ([d011006](https://github.com/tyroneross/research-plugin/commit/d0110065e53cd0e3c0b9730cef52cb4e7fe4f03f))
* **audit:** fail closed on ambiguous evidence ([e1e6fb5](https://github.com/tyroneross/research-plugin/commit/e1e6fb56269fed00b7829feb8b53b04b4b32e042))
* **ingest:** stop naming a research.py subcommand that does not exist ([6e5ff50](https://github.com/tyroneross/research-plugin/commit/6e5ff506cf798d40167f65a2a27678b108975b56))
* read last-release-sha by putting it where release-please looks ([2a890e0](https://github.com/tyroneross/research-plugin/commit/2a890e05729919dc810c7db9a4cf64240d9ec2d7))
* **skills:** front-load trigger and boundary in skill descriptions ([21a4a96](https://github.com/tyroneross/research-plugin/commit/21a4a960452782738c82f7c2a921ddaf9ddeb224))
* stop printing slash commands removed in the surface reduction ([ab02296](https://github.com/tyroneross/research-plugin/commit/ab02296ea7ba005c1a89baea89b3d1336677fc64))

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
