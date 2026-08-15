# Query Optimization Reference

Turns a loose, voice-transcribed, or multi-part request into a **claim-safe research contract** before any sourcing happens. This is Phase 1 of the general research workflow and the body of the `/research:optimize` command.

Host-neutral: every tool reference below means the **host search tool**, **host fetch tool**, or **host file-read tool** — whichever the running agent exposes. The plugin CLI is always invoked as:

```bash
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" <subcommand>
```

## Prime directive

**Preserve the user's intent, hypotheses, uncertainties, and requested output.** Optimization sharpens the specification; it never trades away what was asked for.

**Never force distinct questions into one.** If the request contains two decisions, it has two meta-questions and the output has two contract blocks. Merging them is the single most damaging failure mode of this phase — it hides coverage gaps behind a tidy-looking restatement.

## Step 1 — Classify the input

Split everything the user said into four registers. Keep them separate for the whole run; they carry different evidence obligations.

| Register | Definition | Obligation |
|---|---|---|
| **USER-PROVIDED FACTS** | Stated as known: internal numbers, prior decisions, environment details, "we already run X" | Do not re-derive. Do not silently contradict. If a source disagrees, surface the conflict as a finding. |
| **WORKING HYPOTHESES** | The user's belief being carried into the research: "I think X is cheaper", "presumably Y scales" | Must be tested, not assumed. Report confirmed / contradicted / untestable. |
| **REQUESTED TESTS** | Explicit checks the user asked for: "verify Z still holds", "check whether the API changed" | Each becomes its own section contract with a completion rule. |
| **UNSUPPORTED ASSUMPTIONS** | Premises the request depends on that nobody has evidenced — often unstated | Name them. Either evidence them, scope them out, or flag them as a limitation. |

An unsupported assumption promoted silently into a fact is how a research output becomes confidently wrong.

## Step 2 — Fill the decision card

```text
Decision this research will inform:
By the end we need to know:
Flagship question(s):
Required scope:            entity / segment / geography / product / period
Required basis:            unit, denominator, definition
Minimum useful answer:     number or range + two drivers + one exception + confidence
What changes depending on the answer:
Output the user asked for: format, length, audience
```

Rules:

- If the answer would not change an action, assumption, prioritization, or recommendation, it is not a must-answer question. Move it to context.
- Define ambiguous terms before sourcing: margin vs markup, cost vs price, user vs account, latency vs response time, supported vs recommended.
- State the basis for every number the answer will contain: unit **and** denominator.
- The minimum useful answer sets the evidence bar. A directional opinion may be enough to explore; it is not enough to change a model or a production default.

## Step 3 — Identify the meta-question(s)

A **meta-question** is one decision-bearing question. A request has as many meta-questions as it has decisions.

Test for splitting: *could the two parts be answered by different evidence, and could one be true while the other is false?* If yes, they are distinct meta-questions. Keep them distinct through planning, execution, synthesis, and the coverage summary.

Write each as: `MQ1: <one interrogative task, scope explicit, period explicit, basis defined>`.

## Step 4 — Decompose into MECE sub-question groups

For each meta-question, decompose into sub-questions and group them into **themes named after the decision components** — these become the output's section headings.

- Themes must be collectively exhaustive against the meta-question and mutually exclusive of each other. Validate: no sub-question belongs in two themes; nothing needed for the decision falls outside all themes.
- **Scope, direct answer, drivers, boundaries, and confidence are evidence checks applied *inside* each theme — never the section headings themselves.** Headings named "Scope" and "Confidence" produce a report about the research instead of a report about the decision.
- Each theme should produce at least a direct answer and a confidence statement; drivers and boundaries where the decision needs mechanism or edge behavior.

Per-sub-question standard:

| Check | Pass condition |
|---|---|
| One ask | One interrogative task, not a list joined by "and" |
| Short | Roughly 20 words or fewer |
| Concrete | Object, scope, and period explicit |
| Basis-defined | Numbers carry a unit and a denominator |
| Neutral first | Asked unaided before any proposed range or hypothesis is shown |
| Evidence-seeking | Answerable by a document, number, measurement, or observed case |
| Decision-linked | Maps back to a line on the decision card |

## Step 5 — Emit section contracts

The deliverable of optimization is a table per meta-question. Phase 2 consumes it as the source plan; Phase 4/5 checks it off as the coverage summary.

| Section | Exact question | Evidence required | Expected output | Completion rule |
|---|---|---|---|---|
| `<theme name>` | `<one sub-question, verbatim as it will be answered>` | `<source lanes, tiers, minimum count, recency bound>` | `<number / range / table / verdict / list>` | `<what makes this section done>` |

Completion rules are objective and checkable: "two independent T1/T2 sources dated within 12 months, or the gap is stated explicitly." "Answered" is not a completion rule.

## Optimization levels

Apply the lowest level that makes the request claim-safe. Over-optimizing a simple lookup wastes the user's turn.

| Level | Name | What it does | Apply when |
|---|---|---|---|
| **Q0** | Light cleanup | Fix transcription noise, punctuation, obvious typos. Intent untouched. | The request is already specific, single-decision, and low-stakes. |
| **Q1** | Disambiguation | Q0 + define ambiguous terms, pin scope and period. | One meta-question; a term or timeframe could be read two ways. |
| **Q2** | Basis specification | Q1 + fix units, denominators, and comparison groups; classify the four input registers. | The answer contains numbers, comparisons, or rankings. |
| **Q3** | Decomposition | Q2 + decision card, meta-question identification, MECE sub-question groups. | Multi-part request, more than one decision, or a report-shaped output. |
| **Q4** | Full research contract | Q3 + section contracts with evidence requirements and completion rules, source-lane plan, and explicit non-goals. | Decision-grade, high-stakes, financial/operating-model, or `deep` depth. |

Selection rules:

1. Start from the depth classifier (`research.py depth`). `light` → Q0–Q1, `standard` → Q2–Q3, `deep` → Q4.
2. Raise one level if the request contains more than one decision, a quantitative claim that would enter a model, or a term with a contested definition.
3. Raise to Q4 for any financial or operating-model question — see `../../financial-research/references/financial-controls.md`.
4. Never lower a level the user explicitly asked for.

## Readiness score (0–24)

Eight dimensions, each scored 0–3. Score before optimizing and after; report the delta.

| # | Dimension | 0 | 1 | 2 | 3 |
|---|---|---|---|---|---|
| 1 | **Decision** | No decision named | Topic only | Decision implied | Decision named + what changes with the answer |
| 2 | **Scope** | Unbounded | Entity named | Entity + segment | Entity, segment, geography, product all bounded |
| 3 | **Time / period** | Absent | "Recent" | Period named | Period named + recency bound for sources |
| 4 | **Definitions** | Key terms undefined | Terms named, undefined | Most terms defined | Every contested term defined and located |
| 5 | **Evidence expectations** | None | "Find sources" | Tier or type named | Lanes, tiers, minimum counts, independence rule |
| 6 | **Metrics / basis** | No metric | Metric named | Metric + unit | Metric + unit + denominator + reported-vs-adjusted |
| 7 | **Comparisons** | None implied | Comparison implied | Comparison group named | Comparison group named + like-for-like basis fixed |
| 8 | **Output requirements** | Unstated | Format hinted | Format + length | Format, length, audience, section structure |

| Total | Action |
|---|---|
| **≥ 18** | Proceed. Emit contracts and start sourcing. |
| **12–17** | Proceed **with stated assumptions**. Write each assumption into the contract as an explicit line the user can correct mid-run. |
| **< 12** | Ask **at most three** targeted questions, each closing the lowest-scoring dimension. If the user has said "just research it", do not ask — state the assumptions explicitly and proceed. |

Never block on a low score when the user asked for autonomy. State assumptions and move.

## Worked example — two meta-questions

**Raw request:** *"we're on Postgres full-text and I keep hearing pgvector is the move, can you look into whether we should switch and also is the hybrid search thing people talk about actually better than just BM25, we have maybe 200k docs"*

**Input classification**

- USER-PROVIDED FACTS: currently on PostgreSQL full-text search; corpus ≈ 200,000 documents.
- WORKING HYPOTHESES: pgvector is the better option; hybrid search beats BM25.
- REQUESTED TESTS: (a) should we switch; (b) is hybrid actually better than BM25.
- UNSUPPORTED ASSUMPTIONS: that retrieval quality is the current bottleneck; that 200k documents exceeds what FTS handles well; that "better" means relevance rather than latency or operational cost.

**Decision card (abridged)** — Decision: whether to change the retrieval stack this quarter. Basis: recall@10 and p95 query latency at 200k docs. Minimum useful answer: a verdict per option + two drivers + one exception + confidence. Changes: the Q3 roadmap item and the index-maintenance burden.

**Meta-questions — kept distinct**

- `MQ1: Should this 200k-document PostgreSQL FTS deployment migrate to pgvector for retrieval this quarter?`
- `MQ2: Does hybrid (lexical + vector) retrieval outperform BM25 alone on recall@10 at this corpus size?`

MQ2 is not a sub-question of MQ1: hybrid could win while the migration still loses on operational cost, and vice versa. Merging them would let a "yes" on one paper over a "no" on the other.

**Section contracts — MQ1**

| Section | Exact question | Evidence required | Expected output | Completion rule |
|---|---|---|---|---|
| Retrieval quality at scale | What recall@10 do FTS and pgvector achieve at ~200k documents? | 2+ benchmarks with published methodology and corpus size; primary lane | Two numbers + methodology note | Two independent measurements, or the gap is stated |
| Operational cost | What index build, storage, and maintenance cost does pgvector add on the same instance? | Official docs + 1 production account | Table: build time, storage delta, reindex cadence | Official doc figure plus one operator report |
| Migration boundaries | Under what conditions does the migration not pay off? | Counter-evidence lane: migration-away reports, limitations | 2–4 named conditions | At least one credible negative case, or stated absent |
| Verdict and confidence | Switch, stay, or stage? | Synthesis of the three sections above | Verdict + two drivers + one exception + confidence | Every driver traces to a cited section finding |

**Section contracts — MQ2**

| Section | Exact question | Evidence required | Expected output | Completion rule |
|---|---|---|---|---|
| Head-to-head measurement | What recall@10 delta does hybrid show over BM25 on comparable corpora? | 2+ evaluations that report BM25 as a baseline; primary lane | Delta with corpus size and dataset named | Two independent evaluations, or the gap is stated |
| Where the delta comes from | Which query types drive the delta? | Per-query-class breakdown from any evaluation above | Ranked list of query classes | Mechanism identified or explicitly unresolved |
| Where hybrid loses | On what workloads does BM25 match or beat hybrid? | Counter-evidence lane | 2–4 named conditions | One credible counter-case, or stated absent |
| Verdict and confidence | Is hybrid better for this corpus? | Synthesis above + the 200k-doc constraint | Verdict + confidence + basis | Verdict states the denominator it is measured on |

**Readiness:** before 9/24 (decision 1, scope 2, time 0, definitions 1, evidence 0, metrics 1, comparisons 2, output 2) → 12–17 band would apply after Q1; after Q4 optimization 21/24, with the remaining gap being an unstated latency budget, carried as an explicit assumption.

**Assumptions carried forward (user did not specify):** "better" is scored as recall@10 first, p95 latency second; the evaluation window is sources published within 18 months; no budget for a managed vector service.

## Anti-patterns

- Restating two questions as one "clear question." This is the defect this reference exists to prevent.
- Naming sections "Scope", "Drivers", "Confidence". Those are checks inside a theme, not decision components.
- Promoting a working hypothesis into the framing so the research can only confirm it.
- Asking clarifying questions after the user said "just research it".
- Emitting a contract with a completion rule of "answered" or "enough sources".
- Dropping the user's requested output format during optimization.
