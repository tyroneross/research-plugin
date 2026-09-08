# Research paths selected by intended outcome

Implementation follow-up: the route contract and method profiles are now implemented; execution tools remain capability-dependent. See [method routing](../../skills/research/references/method-routing.md). The assessment below records the evidence and proposal at research time.

Status: proposed architecture; runtime routing is unchanged. Assessed 2026-09-07.

Follow-up: [Discipline-informed research methods](2026-09-07-discipline-research-methods.md) expands this proposal. The five paths remain task shapes; method-specific contracts and an explicit propose–evaluate–revise execution loop address empirical and formal research.

## Decision

Use **five base research paths, three execution structures, and composable verification/domain overlays**. Select the path from the requested outcome and evidence dependencies. Select depth and parallelism separately. Preserve explicit user choices and explain automatic choices.

This is a design recommendation, not a benchmark-proven optimum. The immediate implementation should extend the existing research skill and deterministic contracts, using the host agent for semantic classification and `research.py` for validation. No new agent framework, model API, or retrieval service is needed.

## Assessment of the supplied framework

Keep task-shape routing, shared comparison schemas, per-cell evidence, dependent-step verification, one synthesis owner, and escalation against an observable gap. Revise these claims before turning them into rules:

| Supplied rule or claim | Assessment | Design consequence |
|---|---|---|
| Six mutually distinct archetypes | Disagreement is an evidence condition; it can occur in any of the other five. Entity count alone does not distinguish comparison from collection. | Five base paths plus adjudication overlay. Expose “verify a disputed claim” as a user-facing alias. |
| Comparisons require multiple agents; surveys require large teams | Anthropic presents effort heuristics, not universal minima. Its token and improvement figures describe its own evaluation. [S1] | Start with one owner; allow bounded workers for independent evidence tasks. |
| Large swarms establish general research efficiency | The cited study concerns vulnerability discovery. Swarms explored a wider scope; the authors report comparable token efficiency when restricting scope. [S2] | Do not use the headline ratios to size research teams. |
| Debate earns its overhead on contested topics | The cited debate evaluation reports no reliable superiority over simpler prompting alternatives without tuning. [S3] | Start with evidence reconciliation and counter-evidence search; make debate experimental. |
| Wide collection must use one dedicated subagent | The supplied brief gives no primary source establishing this as a universal rule. Consistent schema ownership does not require serial fetching. | One schema owner; serial batches or disjoint row partitions under the same contract. |
| Deep synthesis must never offload context | This is an unsupported absolute. Coherence requires preserved dependencies, evidence, and assumptions, not every raw page in active context. | Keep a compact dependency ledger; store full evidence outside active context. |
| RAG names are interchangeable runtime modes | Self-RAG trains reflection-token behavior; FLARE uses predicted text and token confidence. A prompt instruction is not an implementation of either method. [S4, S5] | Describe retrieval behaviors directly and record available capabilities. |
| Context editing yields all quoted gains | The cited engineering article is the wrong attribution. A later report distinguishes editing alone, editing plus memory, and a separate long-search token evaluation. [S6] | Treat savings as workload-specific; do not promise them locally. |
| Single agents always minimize latency | Parallel acquisition can shorten elapsed time despite coordination overhead. [S1, S7] | Measure wall time separately from total tokens and tool calls. |
| Token usage explaining variance makes spending causal | An observational relationship does not isolate the effect of spending more tokens. | Tune against quality and cost together, with matched tasks. |

The remaining compression, caching, judge, and benchmark percentages in the supplied document were not audited individually. They are not adopted as routing constants. Mandatory human checks are appropriate only where the actual use case or user requires them; a generic contested-topic label should not block ordinary research.

## Base paths

Each path defines an evidence contract, execution pattern, artifact, and completion rule. Counts such as “2–5” and “10+” can inform estimated effort, but are not classification boundaries.

| Path | User outcome and detection | Research sequence | Required artifact and completion |
|---|---|---|---|
| `lookup` | Resolve a bounded fact, definition, status, or value | Identify entity/time → retrieve authoritative evidence → check applicability → answer | Answer with source and date/basis where relevant; uncertainty if the fact cannot be resolved |
| `compare` | Choose or contrast known alternatives on common criteria | Define criteria and units → collect comparable evidence → reconcile basis → compare or rank | Criteria matrix with grounded fields and unknowns; every requested option and criterion accounted for; ranking only when requested |
| `survey` | Discover an initially unknown set of options, themes, or explanations | Define inclusion/exclusion → explore distinct lanes → deduplicate → assess coverage → shortlist or map | Landscape plus search coverage and exclusions; stop when agreed coverage is met or bounded search is exhausted; no unqualified “complete” claim |
| `explain` | Understand a mechanism, trace a cause, evaluate a hypothesis, or derive a recommendation through dependent facts | Decompose dependencies → collect each prerequisite → test links and alternatives → synthesize | Evidence-linked explanation, assumptions, counterexamples, and unresolved dependencies; load-bearing links supported or explicitly qualified |
| `collect` | Produce records across entities and fields as the main deliverable | Fix entity/field schema → resolve identities → fetch in batches → validate cells → export | Typed table/dataset, source locators per populated factual cell, missingness reasons, completeness report; every requested cell accounted for |

“Compare 20 vendors and recommend three” is `compare`, potentially preceded by `collect`. “List the price and region of these three vendors” is `collect` if the dataset is the requested result. “Discover vendors, shortlist three, then compare” is a staged `survey → compare` plan. Split mixed requests into stages rather than averaging them into one label.

## Three execution structures

1. **Single loop:** one agent acquires evidence, checks it, and answers. Default for lookups and bounded work in every path. Independent tool calls may still run in parallel.
2. **Dependent pipeline:** tasks execute in dependency order, with checks before downstream claims use their outputs. One owner keeps the integrated explanation. Useful for causal analysis and survey-to-comparison sequences. Independent prerequisites may use bounded workers when authorized.
3. **Bounded fan-out and merge:** one coordinator defines disjoint evidence assignments and a shared schema; workers return evidence packets; deterministic checks precede one integrated synthesis. Useful for surveys, substantial comparisons, and partitionable collection.

Every structure shares the same evidence machinery. Agent count is execution metadata, never part of the path name. Choose concurrency from independent ready tasks, host slots, authorization, and remaining budget. A single-agent fallback must execute the same contracts serially.

Adjudication and review are stages that can run on these structures. They do not need separate orchestration engines. LangChain's report-writing experience supports retaining one integrated synthesis owner after independent research. [S7] Cognition's context critique supports making dependencies and implicit assumptions explicit at handoff. [S8]

## Orthogonal controls

| Control | Values or responsibility |
|---|---|
| Workflow | Preserve `general`, `collection`, `synthesis`, `quantitative`, and persistence-only entry points. This says which work the user needs now. |
| Path | `lookup`, `compare`, `survey`, `explain`, `collect`; per stage for mixed requests |
| Depth | Existing `light`, `standard`, `deep`; sets effort, not agent count or evidence truth |
| Verification | Ordinary grounding; enhanced checks for costly errors; adjudication for material disagreement |
| Domain | Financial terms/basis and existing financial skill; other domain-specific source requirements as applicable |
| Source policy | User-provided only, local corpus, public web, or mixed; freshness and explicit reuse rules |
| Computation | Enable existing profiling/calculation workflow when formulas, joins, denominators, or inference from data are required; a table alone does not imply computation |
| Execution | Single loop, dependent pipeline, bounded fan-out; capability and authorization constrained |
| Persistence | User override independently honored; otherwise existing reusable/deep-output policy |

For adjudication, compare source scope, date, definitions, methods, and independence before declaring a contradiction. Maintain claim → supporting evidence → opposing evidence → resolution or unresolved gap. Do not manufacture equal support for unequally supported positions. Add a bounded challenge pass only if a decision-relevant conflict remains; stop when no new evidence is found or the review budget is exhausted.

## Detection and user routing

The precedence is **explicit user selection → task contract → semantic inference → keyword hints**. Host permissions and source restrictions constrain execution throughout.

1. Extract explicit path, depth, sources, output, budget, persistence, and agent preferences, including negation. Quoted source text cannot set these controls.
2. Identify the requested artifact, known/unknown entities, fields, dependency relationships, evidence already supplied, freshness needs, and consequences of error.
3. Preserve separate decisions as separate section contracts. Select paths per stage if discovery must precede comparison or collection must precede analysis.
4. Select the base path from the outcome table. Add verification and domain overlays without replacing the path.
5. Use a transparent confidence category: `clear`, `tentative`, or `needs_input`, with matched signals and the strongest alternative. These are not calibrated probabilities.
6. For low-impact ambiguity, state a reasonable assumption and proceed. Ask one targeted question only when the answer materially changes scope, evidence access, or the useful artifact. Missing entity names required for a comparison are a genuine blocker for that stage.
7. Choose the simplest feasible execution structure. Fan-out requires independent work and authorization; a deep classification alone never grants delegation permission.
8. Emit a short route receipt: “Comparison · standard · current official sources · one researcher. I’ll compare the three named options using your criteria.”

Explicit “use the survey path” wins over automatic comparison inference. If an override conflicts with another user requirement, surface that conflict and preserve both requirements pending resolution; never silently change the selected path. A request for “quick” limits effort while retaining mandatory source checks. A request for “do not save” disables persistence without reducing depth.

User-facing natural language is sufficient initially. Proposed future syntax, **not yet supported**:

```text
/research:research --path compare --depth standard <question>
/research:research --path explain --verify adjudicate <claim>
python3 research.py route --request-file request.json --json
```

The CLI should validate and compile a host-produced classification. It should not call an LLM API. Raw-text heuristics may produce a provisional route, but must not pretend to understand entities, negation, and dependencies reliably.

## Minimal data structures

Extend existing contracts rather than creating a second evidence store:

| Structure | Minimal fields | Role |
|---|---|---|
| Request profile | question, workflow, outcome, entities, fields, scope, freshness, dependencies, explicit overrides | Separate user intent from classifier inference |
| Route decision | schema version, selected path/stages, origin, confidence category, reasons, alternatives, overlays | Explain and replay the selection |
| Execution plan | structure, tasks/depends_on, owners, budgets, capabilities, stop and escalation rules | Define feasible work and limits |
| Evidence packet | existing claims, observation IDs, locators, dates, contradictions, calculation receipts; optional entity/field keys | Reuse current provenance and deterministic merge |
| Completion report | criteria met/partial/unmet, missing cells, unresolved links/conflicts, actual usage, termination reason | Prove useful coverage and distinguish partial results |

Examples of cell states: `supported`, `not_found`, `not_applicable`, `conflicting`, `inaccessible`. Use null values with explicit state and reason for unresolved cells. Do not conflate “unknown” with “not applicable.” Derived cells also require formula/basis and a calculation receipt. Existing observations can be reused if freshness is acceptable and cross-run reuse is declared; same-session web URLs are not the only legitimate evidence.

Budgets distinguish wall time, tool calls, pages/bytes, model tokens when observable, workers, and review passes. Unknown token usage stays unknown. Stop on completion, explicit budget exhaustion, inaccessible required evidence, or a bounded no-progress check. Preserve completed work and identify the unmet criterion.

Escalation changes the mechanism implicated by evidence: missing coverage → new search lane; weak provenance → primary-source retrieval; broken dependency → repair that prerequisite; conflicting comparable claims → adjudication; independent backlog plus time pressure → bounded fan-out if permitted. Log the trigger, old/new route, remaining budget, and affected tasks. Do not mutate an initialized contract in place; bind a new stage or successor contract to it.

## Fit with the current plugin

Live inspection found keyword workflow routing in `skills/research/SKILL.md`, a score-based depth function at `research.py::_research_depth_profile`, and existing dependency/evidence contracts in `skills/research-orchestrator/references/contracts.md`.

The depth function currently combines request length, domain, freshness, computation terms, and persistence language in one score. In particular, “do not save” subtracts effort points and deep results still set persistence true. Its generic quantitative detection also precedes collection/synthesis. These are design coupling risks visible in code, not results from a new runtime regression test.

The current strict run validator requires hypotheses and a nonempty domain allowlist. Do not route every simple local lookup through that heavy contract. Keep a lightweight route receipt for ordinary research; use strict orchestration contracts for runs requiring their controls. Schema evolution must explicitly version any relaxed requirements.

Implementation sequence:

1. Add a path reference document and route receipt instructions to the research skill; align the main command and query optimization contract around one routing decision.
2. Add a read-only `research.py route` compiler/validator and fixtures. Keep existing `depth` output compatible; separate explicit persistence and effort precedence with regression coverage.
3. Bind route decisions to strict run contracts where applicable; reuse existing tasks, source observations, calculation receipts, merge, and metrics. Add dependency-cycle rejection if not already enforced elsewhere.
4. Add route-specific completion checks and replay cases. Keep parallel execution optional until matched local trials show value.

Greenfield target: one typed task graph with path-specific evidence and completion contracts. Best fit here: a small routing layer over existing workflows and CLI controls. The difference is migration work, not a need for another runtime. This proposal is the first deliverable; implementation follows the agreed structural design.

## Routing acceptance cases

These are proposed expected behaviors, not executed tests.

| Input | Expected routing | Failure to catch |
|---|---|---|
| “What is FTS5?” | lookup, light, single loop | Unnecessary orchestration |
| “What is this product's current price?” | lookup + freshness | Stale reuse |
| “Compare A and B on hosting and portability” | compare, common criteria | Independent fields interpreted differently |
| “List addresses and URLs for these three companies” | collect | Small count incorrectly forces comparison |
| “Compare these 20 vendors and recommend three” | compare; collection stage if needed | Large count erases decision objective |
| “What approaches exist for local document search?” | survey | Premature narrowing to known favorites |
| “Explain why ingestion duplicates survive retries” | explain, dependent pipeline, repo evidence first | Parallelizing dependent reasoning |
| “Is the vendor's claimed cost saving supported?” | explain + adjudication where disagreement is material | Debate without new evidence |
| “Summarize only these supplied notes; no web” | synthesis, supplied-only policy | Unrequested fresh search |
| “Analyze this CSV's margin by segment” | quantitative workflow + financial overlay | Guessing math or financial definitions |
| “Quick comparison; do not save” | compare, light, persistence false | Save preference changes effort or gets ignored |
| “Discover options, then compare the best three” | survey → compare | Lost stage dependencies |
| “Use survey mode for A and B” | explicit survey override | Heuristics override user |
| “Research architecture thoroughly, one agent only” | explain/deep, serial execution | Depth triggers unauthorized workers |
| “Research this” with no referent | needs_input | Invented scope |

Additional execution fixtures should inject duplicate observations, schema drift, unavailable cells, source disagreement, cycles, and budget exhaustion. Assert that unsupported cells remain null, contradictions survive merge, dependencies block premature synthesis, and unmet criteria produce a partial report.

Measure route correctness against adjudicated examples, override adherence, path-specific quality, wall time, tool calls, observed tokens, duplicated retrieval, and unresolved requirements. Compare serial and parallel execution on the same tasks and evidence constraints. Use repeated paired trials before claiming a stable gain. Model review supports evidence checks; it cannot independently establish truth by agreeing with the writer.

## Coverage and confidence

| Question | Status |
|---|---|
| Which framework claims change the architecture decision? | Met for the material claims above; full numerical audit remains out of scope |
| Which structures should the plugin use? | Met: five paths, three execution structures, composable controls |
| How should automatic and user routing work? | Met: precedence, confidence, ambiguity, mixed stages, and examples specified |
| How does this fit current implementation? | Met through live inspection of skill, depth classifier, command, and run validator |
| Does the proposed router improve outcomes? | Unmet: requires implementation and local evaluation |

Primary sources, independent organizations, counter-evidence, publication dates, and local implementation were examined. Vendor reports remain self-reported evidence; the proposed taxonomy has not been independently validated. Overall confidence: moderate in the structural recommendation; no measured performance claim.

## Source register

All sources accessed 2026-09-07. Tier reflects suitability for the cited statement, not proof that the vendor's conclusions generalize.

- S1 — [Anthropic research system](https://www.anthropic.com/engineering/multi-agent-research-system), 2025-06-13. T1 primary engineering account; self-reported system evaluation.
- S2 — [Anthropic multiagent systems](https://www.anthropic.com/research/multiagent-systems), 2026-08-13. T1 primary experiment; same organization as S1; scope caveat supplies counter-evidence.
- S3 — [Should we be going MAD?](https://arxiv.org/abs/2311.17371), revised 2024-07-18. T1 original research; independent debate evaluation; counter-evidence to universal debate gains.
- S4 — [Self-RAG](https://arxiv.org/abs/2310.11511), 2023-10-17. T1 original method; abstract checked for mechanism, not a replication.
- S5 — [Active Retrieval Augmented Generation](https://arxiv.org/abs/2305.06983), revised 2023-10-22. T1 original FLARE method; abstract checked for mechanism.
- S6 — [Managing context](https://claude.com/blog/context-management), 2025-09-29. T1 product experiment account; shares Anthropic lineage; separate evaluations must stay separate.
- S7 — [LangChain Open Deep Research](https://www.langchain.com/blog/open-deep-research), 2025-07-16. T1 first-party implementation lessons; independent organization, but some discussion cites S1/S8.
- S8 — [Cognition context engineering](https://cognition.com/blog/dont-build-multi-agents), 2025-06-12. T2 practitioner argument; independent organization; context/coordination counter-evidence.
- Local: `AGENTS.md`, `commands/research.md`, `skills/research/SKILL.md`, `skills/research-orchestrator/references/contracts.md`, `research.py`, and `docs/proposals/2026-08-27-deterministic-pipeline-and-stratagem-assessment.md`.
