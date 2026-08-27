# Before/after research evaluation plan

## Decision

Replay a stratified sample of prior research questions after this build. Compare evidence integrity, quantitative reproducibility, coverage, cost, and latency against frozen pre-build entries. Keep all replay outputs under the configured research index root, not this repository.

## Sample

Recover and hash the exact original user prompt from host logs before each replay. Use the existing entry only as the frozen baseline answer. Start with these five prior entries because they cover distinct failure modes:

| Baseline slug | Research shape | Load-bearing test |
|---|---|---|
| `agents.integration-surfaces-mcp-vs-api-vs-cli` | Current standards and architecture decision | Source versions, vendor neutrality, counter-evidence, changing facts |
| `database.postgres.atomize-query-hotspots` | Quantitative local-data diagnosis | Formula, denominator, grain, local input hashes, failed prior verification |
| `llm.local-vlm-applicability-2026-08` | Model, license, hardware, and OCR recommendation | Currentness, local benchmark, vendor claims versus measured results |
| `connectors.pipedream-planner-temporal-overlay-2026-08` | Multi-provider temporal synthesis | Cross-source identity, source observations, changes over time, coverage receipts |
| `adhd.executive-function.prioritization-evidence-2026-08` | Large medical literature corpus | Primary-source breadth, corrections, uncertainty, opinion/framing, citation precision |

Use three entries for the first pilot: PostgreSQL hotspots, local VLM applicability, and MCP/API/CLI. Expand to all five only after the harness produces complete records.

## Freeze procedure

For each query:

1. Copy the exact prompt, baseline entry, source list, verifier artifacts, and relevant host tool trace into `<index-root>/evaluations/<evaluation-id>/baseline/`.
2. Record SHA-256 for every copied artifact. Do not edit baseline files.
3. Record plugin commit, host, session, model when available, local runtime versions, start/end time, and coverage gaps.
4. Run the candidate through `research-orchestrator` with the same question and decision outcome. Permit newer sources, but record which answer differences come from new evidence versus pipeline behavior.
5. Store candidate contracts, task packets, source observations, receipts, worker results, merge result, and final entry under the evaluation directory.

## Deterministic metrics

Calculate these from artifacts, not model self-report:

- source identity coverage: sources with stable ID / all used sources;
- source date coverage: publication/update/capture fields present / all used sources;
- representation coverage: content hash and raw reference present / all used sources;
- claim grounding: claims with exact evidence observation and locator / all factual claims;
- quantitative receipt coverage: quantitative claims with passed, matching receipts / all quantitative claims;
- discrepancy preservation: identified contradictions retained with both evidence chains / all identified contradictions;
- correction/version coverage: changed or corrected sources linked to the prior observation / all changed sources;
- project/topic/global discoverability: all three generated indexes resolve the candidate entry;
- reuse: prior captures reused after hash or conditional validation / eligible prior captures;
- failures and recoveries: nonzero deterministic operations, retry count, and unresolved gaps;
- local wall time, host tool calls, and recorded token/cost fields. Mark unavailable fields unknown; never estimate them from prose.

Do not combine these into one score until weights and minimum sample rules are approved. Show the vector and any weighted experimental score separately.

## Independent quality audit

Give the independent auditor blinded `baseline` and `candidate` labels. Ask for evidence-cited judgments on:

- answer correctness against the captured sources;
- source quality and independence;
- uncertainty calibration;
- disclosed framing or bias;
- preservation of nuance and counter-evidence;
- formula/query fitness for every quantitative conclusion;
- whether the answer supports the intended decision;
- material omissions or unjustified certainty.

The auditor must not reward length, source count, or agreement with the earlier answer. It must cite artifact paths and exact claims. Resolve label identities only after the verdict is recorded.

## Local extraction benchmark

Build a labeled set of at least 30 representative pages outside this repository: native-text pages, image-only scans, tables, charts, handwriting, and formulas. Compare:

1. native extraction;
2. Apple Vision fast OCR when available;
3. Apple Vision accurate OCR when available;
4. the host's vision route for cases the local paths reject or fail.

Record end-to-end wall time, engine time, input/output hashes, character/word error against the labeled text, field-level numeric exactness, table structure retention, and monetary cost when reported by the host. Route by corpus results, not a general benchmark ranking.

The initial synthetic smoke test on 2026-08-27 showed the reason for the cascade: Apple Vision fast mode read `125.50 /` incorrectly with confidence `0.5`, while accurate mode preserved the string with confidence `1.0`. The Vision request took 33-91 ms in warmed fast runs and 213-235 ms in accurate runs on this machine; Swift process wall time was 0.44-0.63 seconds after warm-up. This one synthetic image proves the adapter runs. It does not establish corpus accuracy or a universal cost advantage.

## Stop conditions

- Stop and fix the pipeline if a candidate loses a baseline citation, contradiction, correction, or numerical caveat.
- Stop if generated research, captures, receipts, or private fixtures appear in plugin git status.
- Mark the comparison inconclusive when exact prior prompts, source snapshots, or cost records cannot be recovered.
- Do not ship an aggregate improvement claim until the three-query pilot passes and the independent auditor signs the evidence paths.
