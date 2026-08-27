# Deterministic research pipeline and Stratagem assessment

## Recommendation

Use scripts for evidence mechanics and the host agent for semantic judgment. Borrow Stratagem's bounded process patterns, but do not add Stratagem or any model-provider SDK as a dependency.

The highest-leverage next work is reuse-first retrieval, content-addressed acquisition, claim-to-citation binding, and deterministic synthesis packets. These reduce tokens because the model receives a small verified packet instead of rediscovering structure from raw pages.

## Current capability assessment

| Stage | Current deterministic support | Remaining gap | Priority |
|---|---|---|---|
| Frame | Typed run contract, source policy, hypotheses/falsifiers, section ownership, hard traversal budgets | Decision-card quality is structurally validated, not semantically judged | Keep host judgment |
| Reuse/search | SQLite FTS5/BM25 over entries and source ledger indexes | Field-weighted claim/source retrieval, query ledger, result diversification, cache-hit metrics | Next |
| Acquire | Canonical URLs, source observations, SHA-256 identity, revision links | Conditional HTTP validation, raw blob store, response metadata | Next |
| Traverse | Recorded depth/domain/page/byte/time/robots decisions | Host must resolve DNS and recheck redirects; no automatic priority queue | Next before autonomous traversal |
| Parse | Vendored Omniparse, native host reads, Apple Vision OCR adapter | One neutral extraction router, layout-preserving table evidence, benchmark harness | Next |
| Deduplicate | Canonical URL and exact content hashes | DOI/canonical-link identity, title-author-date keys, blocked shingle Jaccard | Next |
| Verify citations | Observation IDs and locators | Exact quote/prefix/suffix/position binding and deterministic entailment-presence check | Highest |
| Verify math | Restricted AST, Decimal, units/denominator/grain, source-linked receipts, assertions, whole-receipt integrity | SQL receipt mode, rounding policy, formula-fitness review remains semantic | Strong foundation |
| Detect changes | Source revision edges and discrepancy records | Basis-aware contradiction candidates, corrections/retractions ingestion, cross-run claim equivalence | Next |
| Synthesize | Deterministic packet and merge schemas | Section packet generator with best snippets, gaps, contradictions, dates, receipts, and token budgets | Highest |
| Trust | Dated topic-scoped component observations | Opportunity-to-correct denominator, formula versioning, minimum sample policy | Defer composite score |

## Script-first target flow

1. Validate an immutable research contract and emit disjoint task packets.
2. Query prior entries, observations, claims, and calculations before external search.
3. Score the frontier with a versioned formula: relevance + source-role fit + scoped trust + freshness + novelty - cost - depth - duplicate risk.
4. Capture immutable representations and reuse them by content hash or HTTP conditional validation.
5. Route extraction through native text, deterministic parser, local OCR fast, local OCR accurate, then host vision only when required.
6. Bind each atomic claim to an exact captured evidence selector and locator.
7. Require passing deterministic receipts for every derived quantitative claim.
8. Generate compact section packets from validated claims, contradictions, timeline events, calculations, caveats, and uncovered requirements.
9. Let one coordinator interpret and write from those packets; preserve unresolved disagreements.

SQLite FTS5 already provides BM25, phrase, prefix, NEAR, column-filtered queries, and snippets. At this corpus size, blocked word-shingle Jaccard is simpler and more inspectable than MinHash. Add embeddings or a vector database only if replay metrics demonstrate a recall gap that deterministic retrieval cannot close.

## Screenshot and OCR decision

A screenshot is not the default cheaper parser. Native DOM, accessibility, or embedded document text preserves links, structure, and table semantics and should run first. Screenshot/OCR is appropriate for image-only scans, canvas-rendered pages, and inaccessible visual documents.

The local smoke test proves only that the Apple Vision adapter runs on this Mac. Fast mode was materially less accurate on the synthetic number fixture; accurate mode preserved it. A 30-page labeled benchmark must measure wall time, character/word error, numeric exactness, table-cell retention, memory, host tokens avoided, and escalation rate before claiming lower cost.

## Stratagem

The relevant RossLabs Stratagem is useful as a process reference:

- deterministic light/standard/deep effort envelopes;
- capped agent count, parallel tasks, and validation passes;
- parallelism only across independent lanes;
- file handoffs that keep raw extraction out of conversational context;
- required plan and review gates;
- after-action learning with explicit promotion rules.

Do not adopt its control plane. The inspected local implementation requires `claude-agent-sdk` and names specific models in orchestration code. Its MCP tool surface is more host-neutral, but this plugin should keep JSON/YAML contracts and CLI stdin/stdout authoritative, with optional host adapters. Avoid static model roles, twelve-agent default fan-out, five-minute argument-only caching, LLM-compressed authoritative memory, and non-independent quality agents.

## Vendor-neutral orchestration boundary

The deterministic runtime must not import a provider SDK or call an external model API. Codex, Claude Code, a local runtime, or a single-agent fallback may execute the same task packet. Provider/model/runtime/version/prompt-template hash belong in provenance, not in control logic.

Local model adapters should remain optional and limited to bounded classifications such as relevance, ambiguous entity resolution, and contradiction classification. Retrieval, hashing, calculations, citation binding, and scoring remain deterministic.

## Evidence standards used

- SQLite FTS5: https://www.sqlite.org/fts5.html
- W3C PROV-O: https://www.w3.org/TR/prov-o/
- W3C Web Annotation: https://www.w3.org/TR/annotation-model/
- RFC 9309 robots policy: https://www.rfc-editor.org/rfc/rfc9309.html
- RFC 9111 HTTP caching: https://www.rfc-editor.org/rfc/rfc9111.html
- Crossref versioning: https://www.crossref.org/documentation/principles-practices/best-practices/versioning/
- Maximal Marginal Relevance: https://aclanthology.org/X98-1025/
- Entity-resolution blocking survey: https://arxiv.org/abs/1905.06167
- Stratagem architecture: https://rosslabs.ai/projects/stratagem/
