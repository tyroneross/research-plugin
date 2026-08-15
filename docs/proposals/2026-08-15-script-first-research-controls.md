# Proposal: script-first controls for the research flow

**Status:** proposed (not built) · **Origin:** follow-up to `docs/audits/2026-08-15-usage-audit.md` and a bounded literature pass on 2026-08-15 · **Principle:** the LLM frames, a stdlib script executes, the LLM narrates. Only mechanical, known-risk steps move to scripts.

## Why

- Intermediate hallucinations — especially in *planning* — propagate through every later search/summarize step and are invisible to end-to-end evaluation ([DeepHalluBench, arXiv 2601.22984](https://arxiv.org/abs/2601.22984)). A deterministic gate on the plan is the cheapest place to stop them.
- Deep-research agents produce citations that resolve (>94% link validity) but support the claim only 24–77% of the time ([arXiv 2605.06635](https://arxiv.org/html/2605.06635v1)). Link checking and span-level attribution are separable, mechanical checks.
- Executable-code actions outperform JSON/text tool calls by up to 20% success across 17 LLMs ([CodeAct, arXiv 2402.01030](https://arxiv.org/pdf/2402.01030)). This plugin already applies the pattern in `analyze-plan` / `analyze-run`; the audit found that path used once in four months.

## Scripts (host-neutral, stdlib, invoked by the skill at fixed points)

| Script | Runs at | Does | Replaces |
|---|---|---|---|
| `contract_check` | end of Phase 1 (after `optimize`) | Validates the section-contract table: every meta-question has ≥1 group; groups don't overlap; each contract has question · evidence · completion rule | LLM self-attesting the plan |
| `link_check` | Phase 3, on the source register | Resolves each URL, records status · fetch date · content hash · locator presence | "valid link" assumed |
| `atomize` + `entail` | inside `save` for entries with numeric/citation claims | Extracts atomic claims from Notes; maps each to a Raw-layer span; reports **attribution** (span found?) separately from **factuality** (LLM judges) | dormant `extract` + 39%-failing `verify` precondition |
| `coverage` | Phase 5 | Diffs section contracts vs delivered sections; emits the coverage summary | LLM writing coverage from memory |
| `dedupe` | `ingest` | Normalized-text hash on sources; flags same-text/different-binary pairs | manual duplicate control |
| `provenance` | `save` | Stamps host · agent · session · model into frontmatter | audit suggestion #2 |

## Also

- Persist the query ledger + per-phase decisions beside the entry (process-aware trajectory log).
- Deep profile: prefer ≤10 sources each with a Raw extract and exact locator over 7–15 skimmed.
- Golden-trajectory contract test: fixed multi-question prompt → recorded optimizer output must contain ≥2 meta-questions and a contract table (LLM-free structural check).

## Not proposed

Vector DB · new commands · `research.py` rewrite · LLM-judge as a quality gate.

## Acceptance

Each script ships with a `*_check.py`, is proven red by mutation (break the input, assert non-zero exit), and is called from the skill text at the named phase. Measure `verify` failure rate and citation-attribution rate before/after on ≥20 saved entries.
