---
name: research
description: Use when the user asks to research, investigate, evaluate, compare options, optimize a research question, extract findings, synthesize, analyze CSV/databases, or save to the research library. Frames the request as meta-questions and MECE section contracts before sourcing. Sourced, verified, persisted to ~/dev/research/. Not for rendering an existing audit's findings as a visual HTML dashboard; use `audit-dashboard` instead. Not for a repo-grounded pre-build decision packet tied to an active build-loop run; use the build-loop plugin's own research skill for that.
---

# Research

Structured research methodology for web and technical investigations. Produces cited, verified findings with confidence markers, persisted to a central knowledge base.

Phase 1 is **query optimization**: identify one or more meta-questions, decompose each into MECE sub-question groups that become the output's section headings, and carry them forward as section contracts. Supports four core workflows: **general research** (full 5-phase + persist), **collection** (source -> evidence), **synthesis** (evidence -> output), and **quantitative/database analysis** (data/schema -> generated Python analysis -> certainty-graded results). Use the **deep research architecture overlay** when sources need deterministic intake, parser routing, provenance, search/fetch-style evidence records, and claim QA. Use the **active-project ingestion overlay** when source materials need to become durable project wiki memory with chronology, contradictions, evolving themes, and decision relevance. Financial and operating-model questions route to the **`financial-research`** skill, which adds term authority, measurement records, an attribution ladder, and cost-bucket controls. All workflows end at Phase 6 (persist to `~/dev/research/`) when the output warrants keeping.

## Workflow Detection

Before selecting a workflow, apply `references/method-routing.md`: classify the task shape and research method in the host, then validate the contract with `research.py route --request-file <request.json> --json`. Explicit user overrides win. The CLI's keyword hints are tentative; domain labels alone do not select a method. Preserve depth, verification, source policy, computation and persistence as independent controls.

When findings combine financial, quantitative and qualitative evidence, use explicit source-backed claim connections from `../research-orchestrator/references/contracts.md`. Record relationship rationale and basis alignment; never infer causation from a graph link.

Every derived number in any workflow must be computed through an existing tool or a reviewed Python script, executed and validated. Load `references/quantitative-analysis.md` even when the parent task is a comparison, synthesis or review. A script's successful exit is execution evidence, not proof that the method or inputs are valid.

Use this language table as hints for selecting reference material:

| Trigger Language | Workflow | Reference |
|-----------------|----------|-----------|
| "research", "investigate", "evaluate", "compare", "look into", "what's better X or Y" | **General Research** | Phases 1-6 below |
| "optimize this prompt/question", "make this research-ready", vague or multi-part request, voice transcript | **Query Optimization** | `references/query-optimization.md` · `/research:optimize` |
| "margin", "cost of sales", "COGS", "gross/operating margin", "EBITDA", "working capital", "unit economics", "cost bucket", "P&L", "financial model input", "comparable companies", "filings", "10-K", "earnings call" | **Financial Research** | `financial-research` skill |
| "section contracts", "query ledger", "source register", "claim register", "reconcile sources", multi-section deep run | **Deep Research Orchestration** | `references/deep-orchestration.md` |
| "parallel research agents", "follow links two or three levels", "audit trail", "dependency graph", "verify every calculation" | **Research Orchestrator** | Load the sibling `research-orchestrator` skill |
| "extract", "collect", "what does this say", "pull data from", "analyze this document", "key claims" | **Collection** | `references/collection.md` |
| "index credible sources", "source intake", "parser routing", "deep research architecture", "mixed files", "parse quality", "search/fetch evidence" | **Deep Research Architecture Overlay** | `references/deep-research-architecture.md` |
| "ingest into project wiki", "active project wiki", "project memory ingestion", "preserve chronology", "evolving themes", "contradictions over time" | **Active Project Ingestion Overlay** | `references/active-project-ingestion.md` |
| "synthesize", "summarize findings", "executive summary", "what should we do", "combine findings" | **Executive/Authorial Synthesis** | `references/synthesis.md` |
| "calculate", "quantitative", "analyze this CSV", "database", "SQL", "table", "schema", "metrics", "what does the data show" | **Quantitative / Database Analysis** | `references/quantitative-analysis.md` |
| "save research", "add to research library", "record this" | **Persist existing findings** | `references/persistence.md` |

**When ambiguous:** Use available context and state a tentative route. Ask only when missing input changes the method or a consequential constraint. If they say "just research it," use General Research.

## Depth Detection

Before sourcing, classify the request as `light`, `standard`, or `deep`:

```bash
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" depth "<user request>"
```

Use the classifier as a transparent pre-flight, not as a hidden override. If the user explicitly asks for "quick", "light", "deep", "thorough", or "comprehensive", honor that language.

| Depth | Use when | Source budget | Persistence |
|-------|----------|---------------|-------------|
| **Light** | Definition, quick lookup, one-file summary, narrow factual answer | 0-2 sources | Skip unless reusable or user asks |
| **Standard** | Bounded multi-source question, current-state check, ordinary comparison | 3-8 sources; target 5 | Persist if more than a short answer |
| **Deep** | Decision-grade recommendation, architecture, strategy, risks, high-stakes domain, quantitative claims, large corpus, explicitly thorough/expansive request | 7-15 sources; target 10 | Persist by default; verify critical claims |

Depth controls effort, not quality. Even light research must be accurate, cite external sources when used, and mark uncertainty.

**Coverage requirements:** Standard and deep research must plan source breadth before fetching. Cover these lanes or explicitly explain why a lane is unavailable:
- **Primary/original** — official docs, original papers, primary datasets, source code, release notes, standards, or first-party records.
- **Independent corroboration** — academic, expert, industry, or reputable reporting that does not share the same upstream source.
- **Counter-evidence** — risks, criticism, failures, limitations, migration-away stories, negative cases, or credible alternatives.
- **Temporal/currentness** — source dates, changelogs, recent status, and superseded material when facts may have changed.
- **Gaps** — what no source answered and what evidence would change the conclusion.

**Sequential workflow:** For thorough research on a topic, the full pipeline is:

```text
optimize -> depth -> plan -> research -> reconcile -> synthesize -> persist
```

1. **Optimize** (Phase 1) — decision card, meta-questions, MECE sub-question groups, section contracts
2. **Depth** — classify light / standard / deep; the fork's quick / balanced / deep are aliases (quick = light, balanced = standard)
3. **Plan** (Phase 2) — section contracts become the source plan; build the coverage map and query ledger
4. **Research** (Phase 3) — gather evidence; maintain source and claim registers
5. **Reconcile** — compare sources on basis before value; expose contradictions; prevent scope and cost-bucket blending
6. **Synthesize** (Phase 4-5) — answer each section, then cross-section takeaways, then explicit unresolved gaps
7. **Persist** (Phase 6) — write the result into `~/dev/research/`

**Collection** (evidence extraction) inserts between steps 3 and 4 when the user already has sources; **Synthesis** modes can be invoked independently when the user already has evidence. Quantitative/database analysis inserts after collection whenever claims require calculations, SQL, joins, or schema inspection. For mixed-source intake apply `references/deep-research-architecture.md` before synthesis (source/intake register, parser routing, preserved raw output, extraction confidence); for project-wiki ingestion run Collection first, then `references/active-project-ingestion.md`, then persist durable outputs as separate wiki-ready entries.

---

## Credibility Framework

All workflows use the **two-dimensional credibility framework** from `references/credibility.md`:
- **Dimension 1 — Source Quality:** T1-T4 tiers (aligned with CLAUDE.md), each assignment requires brief rationale. For automated scoring, see `references/source_scoring.md`.
- **Dimension 2 — Claim Corroboration:** PRIMARY, SUPPORTED, SINGLE-SOURCE, CONTESTED, SPECULATIVE, CORRECTED
- **Independence test** required for all SUPPORTED claims

Quick reference:

| Tier | Sources | Trust |
|------|---------|-------|
| T1 | Official docs, research labs, peer-reviewed, standards | Cite directly |
| T2 | Well-cited papers (>50), recognized experts, official eng blogs | Cite with context |
| T3 | IEEE, ACM, reputable industry blogs, conference talks | Cross-ref T1/T2 |
| T4 | Forums, SO, personal blogs, SEO content | Leads only; verify up |

Full framework with anti-patterns: `references/credibility.md`
Deterministic scoring pipeline: `references/source_scoring.md`

---

## Collection Workflow

When the user has sources and needs structured evidence extraction.

**Modes:** Standard, Technical PDF, Concise, Large Corpus — auto-selected by source type, user-overridable. Add the Deep Research Architecture Overlay when the source set includes mixed binaries, spreadsheets, visual-heavy docs, parser-confidence risk, or reusable evidence indexing. Add the Active Project Wiki Overlay when the user wants project memory ingestion, chronology, contradictions, concepts, or wiki update recommendations.

**Core principle:** Source-faithful extraction. Preserve meaning precisely, capture quantitative data exactly, never flatten distinct claims.

**Output:** Evidence package with typed items (claim, source, tier, corroboration, date, extraction type).

Full collection methodology and mode details: `references/collection.md`
Deep research intake, parsing, search/fetch, and QA gates: `references/deep-research-architecture.md`
Active project wiki ingestion overlay: `references/active-project-ingestion.md`
Output format specification: `references/output-contracts.md`

---

## Synthesis Workflow

When the user has collected evidence and needs structured output.

**Modes:**
- **Authorial** — Faithful account of what sources say. No interpretation. Use when: "what does the research say?"
- **Executive** — Three-layer decision support (Findings → Implications → Open Questions). Use when: "what should we do?"

**Sequential recommendation:** Run authorial first for ground truth, then executive for implications.

**MECE requirement:** Before drafting, choose ONE organizing dimension (Chronological / Structural / Stakeholder / Thematic) and validate no finding belongs in 2+ sections.

Full synthesis methodology and mode details: `references/synthesis.md`
Output format specification: `references/output-contracts.md`

---

## Quantitative / Database Analysis Workflow

When research requires math, metrics, table analysis, SQL, or database reasoning.

**Core rule:** The LLM frames the analysis; Python performs the calculation.

Use this workflow before making quantitative claims from data:
1. **Assess** — Define the question, input type, grain, schema, formulas, denominators, joins, and assumptions.
2. **Profile** — Run `research.py table-profile <file>` for CSV/TSV/JSON or `research.py db-profile <db>` for SQLite.
3. **Plan** — Run `research.py analyze-plan --input <path> --question "..."` to create `analysis-plan.yaml`, profiles, and a self-contained `analysis.py`.
4. **Run** — Run `research.py analyze-run --plan <analysis-plan.yaml>` to produce `results.json` and `audit.md`.
5. **Report** — State every quantitative finding with formula/query, validation status, limitations, and **High / Medium / Low** certainty.

Certainty rubric:
- **High** — Structured data, schema understood, deterministic formula/SQL, validation passes, no major assumptions.
- **Medium** — Usable data with assumptions, partial schema ambiguity, missing values handled, or manual mapping.
- **Low** — OCR/PDF extraction, ambiguous grain/denominator, uncertain joins, failed validations, or missing critical data.

Default generated scripts are stdlib-only, local, and self-contained. Do not install packages or download code during analysis unless the user explicitly approves the environment change.

Full methodology and safety rules: `references/quantitative-analysis.md`

---

## General Research Workflow

### Phase 1: Frame the Question

Framing is query optimization. Full protocol: `references/query-optimization.md`; command surface: `/research:optimize`.

**Never force distinct questions into one.** A request has as many meta-questions as it has decisions, and they stay distinct through planning, execution, and synthesis. Collapsing them hides coverage gaps behind a tidy restatement.

Before searching:

1. **Classify the input** into four registers, kept separate for the whole run: USER-PROVIDED FACTS · WORKING HYPOTHESES · REQUESTED TESTS · UNSUPPORTED ASSUMPTIONS. Facts are not re-derived; hypotheses are tested, not assumed; assumptions are named or scoped out.
2. **Decision card** — fill it before drafting anything: decision this research informs · what we must know by the end · flagship question(s) · required scope (entity/segment/geography/product/period) · required basis (unit + denominator) · minimum useful answer · what changes depending on the answer · the output format the user asked for.
3. **Identify the meta-question(s)** — one per decision. Split test: could the two parts be answered by different evidence, and could one be true while the other is false? If yes, they are separate meta-questions.
4. **Decompose each into MECE sub-question groups** — themes named after the **decision components**; these become the output's section headings. Scope, direct answer, drivers, boundaries, and confidence are evidence checks applied *inside* each theme, never the headings themselves.
5. **Emit section contracts** — per meta-question, a table of `Section | Exact question | Evidence required | Expected output | Completion rule`. Completion rules must be objectively checkable ("two independent T1/T2 sources dated within 12 months, or the gap is stated"), never "answered".
6. **Score readiness 0–24** across decision, scope, time/period, definitions, evidence expectations, metrics/basis, comparisons, output requirements. ≥18 proceed · 12–17 proceed with assumptions stated in the contract · <12 ask at most three targeted questions, or state assumptions and proceed if the user said "just research it".
7. **Research type** — Determines strategy and output format:
   - **Current state** — What's the latest on X? (pricing, versions, features, status)
   - **Comparison** — X vs Y across defined criteria
   - **Evaluation** — Should we use X? (fit assessment against requirements)
   - **Deep dive** — How does X work? (architecture, internals, patterns)
   - **Survey** — What options exist for X? (landscape scan)
8. **Scope constraints** — Time budget, depth needed, output format
9. **Known context** — What the user already knows (avoid re-researching)

Per-sub-question standard: **one ask · short · concrete · basis-defined · neutral first · evidence-seeking · decision-linked**. Optimization levels Q0 (light cleanup) → Q4 (full research contract) set how much of the above to apply: `light` → Q0-Q1, `standard` → Q2-Q3, `deep` → Q4. Any financial or operating-model question is Q4 and routes to the `financial-research` skill.

### Phase 2: Source Strategy

Select sources based on research type. Always prefer higher-tier sources.

**The section contracts from Phase 1 are the source plan.** Work one section at a time against its `Evidence required` column until its completion rule is met or provably unmeetable. A section that cannot be completed becomes a stated gap, never a quietly thinner section. No finding may satisfy two sections — if one does, the themes were not mutually exclusive and the contract is fixed rather than the evidence double-counted.

Before searching, create a **coverage map**:
1. Name the required source lanes for this query: primary/original, independent, counter-evidence, temporal/currentness, and gaps.
2. Assign a source-count target from the depth profile. Standard targets 5 sources; deep targets 10.
3. State what counts as independent for this topic. Two articles that repeat the same announcement, paper, benchmark, or vendor claim are not independent.
4. Identify likely counter-evidence queries before searching, not after a preferred answer emerges.
5. If a lane cannot be filled, keep it as an explicit gap instead of smoothing it away.

**Source strategy by research type:**

| Type | Primary sources | Verification |
|------|----------------|--------------|
| Current state | Official docs, release notes, changelogs | Check dates, verify against 2+ sources |
| Comparison | Official docs for each option, benchmarks | Cross-validate claims, check methodology |
| Evaluation | Official docs, production case studies, GitHub issues | Test claims where possible |
| Deep dive | Source code, architecture docs, design docs | Trace through implementation |
| Survey | Ecosystem roundups, awesome-lists, official registries | Verify each candidate independently |

**Minimum verification:**
- 2-source minimum for statistics, competitor claims, disputed facts
- Date-check all sources — reject anything stale without flagging it
- No T1/T2 available → mark finding as TAG:INFERRED
- Deep research minimum: at least 2 primary/original sources when available, 3 independent sources, 2 counter-evidence sources, and a dated source register.

### Phase 3: Execute Research

Run searches and fetches in parallel where independent. Minimize sequential round-trips.

For a multi-agent run, bounded second-/third-level traversal, append-only run/source history, or strict quantitative receipts, load the sibling `research-orchestrator` skill. Keep its JSON contract and deterministic merge checks around this research flow; do not replace the evidence, credibility, synthesis, or persistence phases.

**Host tool routing:**
- Start technical and codebase research with the coding agent's local file, shell, and repository tools. Do not send local source code through a web connector.
- On Codex, use the on-device in-app Browser for public HTML source reading and exact-page capture when it is available. Use the host's structured web search/open connector (`web__run`) as the backup for discovery or when Browser cannot retrieve a public page.
- On Claude Code, use native `WebSearch` for discovery and `WebFetch` for public HTML source reading.
- On other hosts, prefer the host's local/on-device browser or purpose-built connector, then its structured web search/fetch tool.
- Invoke connectors through their published structured schema. Never construct or evaluate a hand-written wrapper around a connector call.
- If the backup connector rejects a request, retry once with the smallest valid request containing only the required operation and query or URL. Treat an empty result as a valid result, but treat schema or invocation errors as connector failures and fall back to Browser or a known official URL.

**For web research:**
1. Start with targeted web searches across the coverage lanes: primary, independent, counter-evidence, and temporal/currentness
2. Open the most promising results with the host-appropriate source-reading tool above and capture the relevant source text for the Raw layer
3. Build a source register with URL, source tier, date, role in the coverage map, and independence notes
4. Extract specific data points, not general impressions
5. Track source URL and date for every finding

**For non-HTML sources** (PDFs, Excel, PowerPoint, Python source, whole docs directories):
Use `/research:extract <path>` — routes everything through `@tyroneross/omniparse` (user-authored, MIT) with a content-hash cache.
- Handles PDF, `.xlsx/.xls/.csv/.tsv/.ods/.xlsb`, `.pptx`, `.py`, and directories (`-r`).
- Short PDFs (≤10 pages, simple text) are often better served by the host agent's native `Read` with `pages=` — no extraction needed.
- HTML URLs are rejected with a pointer to the host's Browser or native web fetch tool. Plain text formats (`.md`/`.txt`/`.json`/`.yaml`) are rejected with a pointer to `Read`.
- For mixed, visual-heavy, table-heavy, or reusable source sets, follow `references/deep-research-architecture.md`: preserve an intake manifest, parse notes, extraction confidence, and provenance before making claims.
- See `references/persistence.md` for the full decision table and cache behavior.

**For technical/codebase research:**
1. Start with official documentation (fetch docs URLs directly)
2. Check GitHub repos — stars, last commit, open issues, release cadence
3. Search source code for implementation details (search by pattern, read files, find by name)
4. Check package registries for download stats, version history

**For comparison research:**
1. Define criteria BEFORE searching (avoid cherry-picking)
2. Research each option independently first
3. Fill comparison matrix with cited data
4. Note gaps — missing data is a finding

**Research discipline:**
- Record what each source actually says, not what you expected
- Preserve failure evidence — if a promising lead was wrong, note it
- When sources conflict, present both with their tiers
- Never extrapolate version numbers, dates, or pricing from memory
- **Preserve the raw extracted text** (Browser/native web-fetch output, `Read` PDF text) for the Raw layer in Phase 6

### Phase 4: Synthesize

Compile findings into structured output. Use the appropriate template from `references/templates.md`.

**Every finding must have:**
- The claim or data point
- Source (URL or file path)
- Confidence marker: ✅ Verified (2+ T1/T2 sources) · ⚠️ Single source · ❓ Inferred/uncertain
- Date context if time-sensitive

**Synthesis rules:**
- Lead with the answer, then evidence
- Separate facts from interpretation
- Flag stale data explicitly
- Include a **coverage summary that checks off the Phase 1 section contracts** — one line per sub-question, marked met / partially met / unmet with the reason. Then lanes covered, lanes missing, and strongest counter-evidence
- Keep meta-questions separate through the conclusion: two meta-questions produce two verdicts, even when they point the same direction
- For multi-section or deep runs, run the **reconcile** step before writing conclusions — see `references/deep-orchestration.md`
- Include a "Limitations" section for what couldn't be verified
- End with actionable next steps or recommendations

For deeper synthesis (authorial or executive modes), see `references/synthesis.md`.

### Phase 5: Deliver

Present findings inline in the conversation. For anything the user will want to refer back to — proceed to Phase 6.

Always include:
1. **Coverage summary** — every Phase 1 sub-question checked off as met / partially met / unmet
2. **Confidence summary** — Overall confidence in findings
3. **Open questions / unresolved gaps** — what no source answered, which completion rules went unmet, and what evidence would change the conclusion
4. **Sources list** — All URLs/paths consulted

### Phase 6: Persist

**When to run:** Honor explicit no-save or save settings in the route first. Otherwise use the depth classifier. Persist deep research by default, persist standard research when it produces a report-sized or reusable result, and skip light research unless the user asks to archive it.

**See `references/persistence.md` for the full contract.** Summary:

1. **Derive slug** — Dendron-style dot-hierarchy from the topic tree.
   Examples: `prompting.chain-of-thought`, `db.postgres.pgvector`, `design.calm-precision.forms`.
   Filename: `<slug>.md` inside `~/dev/research/topics/<top-level-topic>/`.

2. **Detect project** — If `cwd` is under `~/dev/git-folder/<name>/`, set `projects: [<name>]`. Otherwise `projects: []`.

3. **Write three-layer markdown file** with YAML frontmatter:
   - Frontmatter schema: see `references/persistence.md`.
   - `## TL;DR` (≤150 words, extractive — use bolded phrases from Notes).
   - `## Notes` (body with **bolded** key passages, `[[backlinks]]`, inline `[T1: url]` citations).
   - `## Raw` (verbatim source extracts from Browser/native web-fetch/`Read` outputs, each tagged with URL + capture date).

4. **Source tiers** — v0.1: tag manually using the T1–T4 framework. v0.2+: `python research.py score --auto` fills tiers deterministically from `domain_scores` cache → rules → LLM residue.

5. **Persist** — Invoke:
   ```bash
   python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" save --file <path-to-entry>
   ```
   The script upserts into SQLite, creates project symlink + INDEX.md line when `projects[]` is non-empty, and the PostToolUse hook regenerates `~/dev/research/index.md`, `by-topic.md`, `by-project.md`, and per-topic MOCs.

6. **Verify (v0.2+)** — For entries with numeric, citation, symbolic, or code claims:
   ```bash
   python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" verify <slug>
   ```
   Updates `verification.*` frontmatter and writes per-atom artifacts to `~/dev/research/verifier-log/<slug>/`.

7. **Announce** — Report the canonical path, project symlink path (if any), corroboration count, and verification summary.

## Important

- Never claim information is current without checking. Today's date matters.
- For dates, version numbers, pricing, and status: search or fetch — never guess.
- If a search returns nothing useful, say so. Empty findings are valid findings.
- Prefer source-faithful extraction over source-count theater. Be expansive by covering the necessary lanes, then go deep on the sources that carry the decision.
- Research is complete when the question is answered, not when all sources are exhausted.
- **Phase 6 honors persistence** — an explicit no-save setting wins at every depth; deep persists by default; standard persists when reusable; light stays inline unless the user asks to save it.

## Additional Resources

For detailed methodology and output formats, consult:
- **`references/query-optimization.md`** — Phase 1 contract: input registers, decision card, meta-questions, MECE groups, section contracts, Q0-Q4 levels, 0-24 readiness score
- **`references/deep-orchestration.md`** — Section contracts in execution, query ledger, source and claim registers, reconcile step, cross-section synthesis, completion rules
- **`references/credibility.md`** — Two-dimensional credibility framework (source quality + claim corroboration)
- **`references/source_scoring.md`** — Deterministic tier scoring pipeline (domain cache → rules → LLM residue)
- **`references/collection.md`** — 4 collection modes (standard, technical PDF, concise, large corpus)
- **`references/deep-research-architecture.md`** — Intake, parser routing, normalized evidence, search/fetch interface, and QA gates for expansive deep research
- **`references/synthesis.md`** — 2 synthesis modes (authorial, executive) with MECE operationalization
- **`references/quantitative-analysis.md`** — Quantitative/database workflow with generated Python analysis scripts and certainty rubric
- **`references/output-contracts.md`** — Evidence package and synthesis output format specifications
- **`references/templates.md`** — Output templates for each general research type
- **`references/methodology.md`** — Extended methodology notes, anti-patterns, and research quality checklist
- **`references/persistence.md`** — Phase 6 save contract, three-layer template, frontmatter schema, slug rules
- **`references/verification.md`** — Claim decomposition and verifier routing (v0.2)
- **`references/lifecycle.md`** — Staleness, archival, compression (v0.3)
