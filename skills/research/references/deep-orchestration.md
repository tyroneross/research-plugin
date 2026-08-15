# Deep Research Orchestration Reference

How a multi-section research run is **driven**: carrying section contracts through execution, logging every query, keeping source and claim registers, reconciling conflicts, and synthesizing across sections without blending scopes.

**One owner per concept.** This file owns the *workflow* plane — contracts, ledger, registers, reconcile, cross-section synthesis, completion. `skills/research/references/deep-research-architecture.md` owns the *evidence* plane — file intake, parser routing, normalized element model, indexing, retrieval scoring, and QA gates. Read that file for how a PDF becomes evidence; read this one for how evidence becomes a sectioned answer. `skills/research/references/query-optimization.md` owns Phase 1, which produces the section contracts this file consumes.

Host-neutral: "host search tool", "host fetch tool", and "host file-read tool" mean whichever tools the running agent exposes. The plugin CLI is always:

```bash
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" <subcommand>
```

## Pipeline

```text
optimize -> depth -> plan -> research -> reconcile -> synthesize -> persist
```

Reconcile is a distinct step, not a synthesis sub-task. Merging them is how contradictions get smoothed away in the same pass that writes the conclusion.

## Depth vocabulary

This plugin's canonical depths are **light / standard / deep**, set by `research.py depth`. The work-machine fork uses quick / balanced / deep; treat those as aliases.

| Canonical | Alias | Source budget | Section contracts | Registers |
|---|---|---|---|---|
| `light` | `quick` | 0–2 | Optional; one contract at most | Inline citations sufficient |
| `standard` | `balanced` | 3–8, target 5 | Required when the output has sections | Source register required; claim register optional |
| `deep` | `deep` | 7–15, target 10 | Required, one table per meta-question | Source register **and** claim register required |

An alias never changes behavior; it only maps the user's word onto a canonical depth.

## Section contracts in execution

Phase 1 emits one contract table per meta-question:

| Section | Exact question | Evidence required | Expected output | Completion rule |
|---|---|---|---|---|
| `<theme>` | `<sub-question, verbatim>` | `<lanes, tiers, min count, recency>` | `<number / table / verdict>` | `<objectively checkable condition>` |

During execution:

1. **Work one section at a time until its completion rule is met or provably unmeetable.** A section that cannot be completed becomes a stated gap, never a quietly thinner section.
2. **Never let a finding satisfy two sections.** If it does, the themes were not mutually exclusive — fix the contract, do not double-count the evidence.
3. **Sections are independent for parallelism.** Fan out searches across sections where the host supports concurrency; keep the ledger single-writer so query attribution stays correct.
4. **Contract drift is a finding.** If the real question turns out to be different from the contract, amend the contract explicitly and note the amendment — do not answer a question the user did not ask and present it as the answer.

## Query ledger

Every search or fetch is logged, including the ones that returned nothing. Empty results are evidence about the evidence.

| query_id | query (verbatim) | section | lane | host tool | date | hits | kept | note |
|---|---|---|---|---|---|---|---|---|
| Q01 | `pgvector recall benchmark 200k documents` | Retrieval quality at scale | primary | host search tool | 2026-08-15 | 8 | 2 | Two vendor posts excluded as non-independent |
| Q02 | `pgvector migration regret postmortem` | Migration boundaries | counter-evidence | host search tool | 2026-08-15 | 3 | 0 | No credible negative case found — recorded as gap |

`lane` is one of the coverage lanes: `primary` · `independent` · `counter-evidence` · `temporal` · `gap-probe`.

Why it exists: without a ledger, "we searched for counter-evidence" is unfalsifiable. With one, an empty counter-evidence lane is visible as a row with `hits: 0` instead of an absence nobody notices.

## Source register

One row per source, assigned a stable `source_id` reused by every claim.

| source_id | title | date | path_or_url | tier | exact_locator | independence note |
|---|---|---|---|---|---|---|
| S01 | Official pgvector documentation | 2026-06-11 | `https://…` | T1 | Indexing section, HNSW parameters | Primary/original |
| S02 | Vendor benchmark post | 2026-03-02 | `https://…` | T3 | Table 2, recall@10 column | Restates S01's methodology — **not independent of S01** |

Rules:

- `exact_locator` is mandatory and specific: page, section, table, heading, timestamp, cell range. "The docs" is not a locator.
- The independence note is where corroboration theater dies. Two sources repeating one upstream announcement, benchmark, or vendor claim count as **one** source.
- Sources that only pointed you somewhere else are `discovery lead` and can never corroborate a claim by themselves.
- For file-based sources, the intake manifest fields (content hash, parser, extraction confidence, parse notes) come from `skills/research/references/deep-research-architecture.md` and hang off the same `source_id`.

## Claim register

One row per claim that will appear in the output. A claim without a register row does not ship.

| claim_id | statement | source_ids | corroboration class | confidence | basis |
|---|---|---|---|---|---|
| C01 | HNSW index build on 200k docs takes ~X minutes on a 4-vCPU instance | S01, S05 | SUPPORTED | ✅ | Two independent measurements; unit = minutes, denominator = 200k docs / 4 vCPU |

- **Corroboration class**: `PRIMARY` · `SUPPORTED` · `SINGLE-SOURCE` · `CONTESTED` · `SPECULATIVE` · `CORRECTED` (defined in `skills/research/references/credibility.md`).
- **Confidence**: ✅ verified (2+ independent T1/T2) · ⚠️ single source or untested · ❓ inferred/uncertain.
- **Basis**: the unit and denominator the number is measured on, plus scope. A claim whose basis cannot be written is not yet a claim.
- Evidence strength must be proportional to claim precision. A directional source cannot support a two-decimal number.

## Reconcile

Run after research, before synthesis, over the claim register.

1. **Group claims that answer the same question.** Different `claim_id`s answering one contract row are a reconciliation group.
2. **Compare on basis before comparing on value.** Most apparent contradictions are basis mismatches: different periods, different denominators, reported vs adjusted, consolidated vs segment, one scope vs another. Reconcile the basis first; a real disagreement is what survives that.
3. **Never blend scopes or buckets to make numbers agree.** Combining a parent-company figure with a consolidated one, or two differently-defined cost buckets, manufactures a number that no source supports.
4. **Classify each group**: `agreement` · `basis mismatch (resolved)` · `genuine contradiction` · `insufficient evidence`.
5. **Genuine contradictions are first-class output.** Record both sides with their tiers, dates, and locators, state which one the conclusion leans on and why, and carry the disagreement into the confidence marker. Do not average conflicting sources.
6. **Downgrade, do not delete.** A claim that fails reconciliation is requalified (SINGLE-SOURCE, CONTESTED) or removed with a note — never silently kept.

Reconcile output block:

```text
Reconciliation group: <contract row>
  Claims: C03 (S02, T3, FY2025, consolidated) vs C07 (S04, T1, FY2025, parent-only)
  Classification: basis mismatch (resolved)
  Resolution: different scopes; C07 is parent-only and cannot stand in for consolidated.
  Effect on conclusion: the consolidated figure C03 carries the section; C07 is reported as a scope note.
```

## Cross-section synthesis

1. Answer each section against its own contract first, in the contract's expected-output shape.
2. **Then** write the cross-section takeaways: what the sections say *together* that none says alone. Every takeaway cites the `claim_id`s underneath it.
3. Keep meta-questions separate through the conclusion. Two meta-questions produce two verdicts, even when they point the same direction.
4. Close with an explicit **unresolved gaps** block — not a hedge, a list: what no source answered, which ledger rows came back empty, which completion rules went unmet, and what evidence would change the conclusion.
5. Every section's confidence marker traces to its claim register rows. A section cannot be more confident than its weakest load-bearing claim.

## Completion

A deep run is complete when, for each meta-question:

- [ ] Every section contract is met or recorded as an unmet gap with a reason.
- [ ] The query ledger shows at least one row per required coverage lane, including empty results.
- [ ] Every shipped claim has a claim-register row with source_ids, corroboration class, confidence, and basis.
- [ ] Every source has a tier and an exact locator, and non-independent sources are marked.
- [ ] Reconcile has classified every group; no genuine contradiction is unstated.
- [ ] Cross-section takeaways cite claim_ids; unresolved gaps are listed explicitly.
- [ ] QA gates from `skills/research/references/deep-research-architecture.md` pass for decision-grade runs.

Research is complete when the contracts are met, not when the sources are exhausted.
