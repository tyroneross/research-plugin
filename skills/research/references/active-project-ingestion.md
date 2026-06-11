# Active Project Research Ingestion

Use this workflow when research materials need to become durable project memory for an active wiki, not just a short summary. It is an overlay on collection and synthesis: observe each source first, then cluster repeated evidence, then derive themes, project implications, and wiki updates.

Do not use this workflow for routine bulk import, a single lightweight note, or sources that only need to be searchable. Use `/research:ingest --inbox` or the normal collection flow for those cases.

## Trigger Conditions

Use this workflow when the user asks to:

- ingest research reports into an active project wiki
- preserve chronology, contradictions, assumptions, or decision relevance
- update existing project memory from multiple documents
- merge new reports with prior wiki context
- identify themes across sources over time
- produce wiki entry recommendations, concept maps, or decision support from a source set

If the user provides both source files and active decision questions, treat the request as `deep` unless they explicitly ask for a quick pass.

## Inputs

Capture these fields when available:

| Field | Purpose |
|---|---|
| `PROJECT_NAME` | Project identity for `projects:` frontmatter and wiki links |
| `PROJECT_OBJECTIVE` | Decision context for relevance filtering |
| `CURRENT_DECISION_QUESTIONS` | Active decisions, hypotheses, or workstreams |
| `KNOWN_STAKEHOLDERS` | People, teams, customers, competitors, partners, executives |
| `SOURCE_DOCUMENTS` | Reports, PDFs, slides, transcripts, memos, datasets |
| `EXISTING_WIKI_CONTEXT` | Relevant prior entries or project memory |
| `TIME_RANGE` | Source timeline, event timeline, or data period |
| `OUTPUT_MODE` | New ingestion, update existing wiki, or merge with prior ingestion |
| `CITATION_FORMAT` | Prefer source title plus page, slide, section, or URL |

If key inputs are missing, continue with explicit `MISSING` labels instead of inventing context.

## Required Labels

Use these labels on factual and interpretive material:

| Label | Meaning | Plugin Mapping |
|---|---|---|
| `SOURCE-SUPPORTED` | Directly stated or clearly evidenced | `PRIMARY`, `SUPPORTED`, or `SINGLE-SOURCE` |
| `INFERRED` | Reasonable synthesis, not directly stated | `SPECULATIVE` or `confidence: inferred` |
| `UNVERIFIED` | Plausible but insufficiently supported | `SPECULATIVE` or `confidence: partial` |
| `CONTRADICTED` | Sources disagree | `CONTESTED` |
| `OUTDATED` | Newer evidence changes older evidence | `CORRECTED` or timeline note |
| `SUPERSEDED` | Older claim replaced by newer evidence | `CORRECTED`, `status: archived`, or superseded note |
| `MISSING` | Needed evidence is absent | Gap or open question |

Separate source observation from synthesis. The required reasoning path is:

```text
source observation -> repeated pattern -> theme/concept -> project implication -> wiki update
```

## Claim Type Taxonomy

Classify important material as one of:

- fact
- metric / data point
- author interpretation
- forecast
- assumption
- recommendation
- risk
- open question
- decision
- stakeholder position
- market signal
- customer signal
- competitive signal
- technical signal
- financial signal
- regulatory / policy signal

For each important item, capture source date, event date if different, data collection period when available, and whether the item is current, historical, projected, or superseded.

## Workflow

### 1. Source Inventory

Create the source register before synthesis.

| Source ID | Title | Type | Author / Org | Date | Data Period | Scope | Methodology | Relevance | Status | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|

Status values: `Current`, `Historical`, `Draft`, `Final`, `Superseded`, `Unknown`.

Confidence values:

- `High`: clear source, strong method, recent, directly relevant
- `Medium`: relevant but partial, dated, or method-limited
- `Low`: unclear source, weak method, anecdotal, or hard to verify

### 2. Document-Level Extraction

For each source, extract before cross-source synthesis.

```markdown
## Source: [Source ID] - [Title]

### One-Sentence Source Thesis
[One sentence, source-grounded.]

### Executive Takeaways
| Takeaway | Evidence | Source Location | Confidence | Project Relevance |
|---|---|---|---|---|

### Key Concepts
| Concept | Definition / Meaning | Evidence | Related Concepts | Wiki Entry Needed? |
|---|---|---|---|---|

### Key Data and Metrics
| Metric / Data Point | Value | Unit | Time Period | Segment / Geography | Source Location | Caveats |
|---|---:|---|---|---|---|---|

### Claims and Evidence
| Claim | Evidence Provided | Claim Type | Confidence | Caveats |
|---|---|---|---|---|

### Assumptions
| Assumption | Explicit or Inferred | Why It Matters | Risk If Wrong | Evidence |
|---|---|---|---|---|

### Risks, Constraints, and Watchouts
| Risk / Constraint | Source Evidence | Impact | Likelihood | Mitigation / Follow-Up |
|---|---|---|---|---|

### Stakeholders, Entities, and Relationships
| Entity | Type | Role in Source | Relationship | Evidence | Wiki Link Needed? |
|---|---|---|---|---|---|

### Decisions or Implied Decisions
| Decision / Recommendation | Who | When | Evidence | Rationale | Open Dependency |
|---|---|---|---|---|---|

### Open Questions
| Question | Why It Matters | Evidence Gap | Suggested Owner / Next Source |
|---|---|---|---|
```

### 3. Cross-Document Theme Discovery

Do not start with predefined themes. Derive themes from repeated evidence.

| Theme | Supporting Sources | Repeated Evidence | First Seen | Latest Evidence | Direction of Change | Confidence | Project Implication |
|---|---|---|---|---|---|---|---|

Direction values: `Emerging`, `Strengthening`, `Stable`, `Weakening`, `Contradicted`, `Reframed`, `Superseded`, `Unknown`.

### 4. Theme Evolution

Build a timeline of how research understanding changed.

| Date / Period | Source | Theme / Concept | What Changed | Why It Matters | Confidence |
|---|---|---|---|---|---|

Then summarize:

- Starting understanding
- Emerging pattern
- Shift or reframe
- Current best understanding
- Residual uncertainty

### 5. Concept Map

Use text-based concept maps for wiki-durable relationships.

```markdown
# Concept Map

## Core Concept: [Name]
- Definition:
- Why it matters:
- Source evidence:
- Related concepts:
  - [Concept A]: [relationship]
  - [Concept B]: [relationship]
- Related entities:
  - [Company / stakeholder / product / market]: [relationship]
- Open questions:
- Suggested wiki links:
```

Also produce:

| Entity / Concept A | Relationship | Entity / Concept B | Evidence | Confidence |
|---|---|---|---|---|

Relationship values can include: `drives`, `constrains`, `enables`, `competes with`, `depends on`, `replaces`, `reinforces`, `contradicts`, `is a subset of`, `is a use case of`, `is a risk to`, `is an input to`, `is an output of`.

### 6. Contradictions and Tensions

Flag tensions instead of smoothing them over.

| Tension / Contradiction | Source A | Source B | Conflict Type | Nature of Conflict | Possible Explanation | Decision Impact | Resolution Needed |
|---|---|---|---|---|---|---|---|

Conflict types: `data conflict`, `definition conflict`, `methodology conflict`, `time-period conflict`, `market interpretation conflict`, `strategic priority conflict`, `stakeholder perspective conflict`, `forecast uncertainty`, `scope mismatch`.

### 7. Active Project Implications

Translate evidence into decision-relevant implications.

| Implication | Type | Evidence Base | Affected Workstream | Stakeholders | Decision Relevance | Confidence | Next Action |
|---|---|---|---|---|---|---|---|

Implication types: `strategic`, `financial`, `product`, `GTM`, `customer`, `competitive`, `technical`, `operational`, `regulatory`, `organizational`, `risk / mitigation`, `research gap`.

### 8. Wiki Entry Recommendations

Recommend specific wiki mutations.

| Wiki Entry | Action | Reason | Source Evidence | Links Needed | Priority |
|---|---|---|---|---|---|

Actions: `create new entry`, `update existing entry`, `merge duplicate entries`, `add timeline note`, `add contradiction note`, `add source citation`, `add stakeholder relationship`, `add concept relationship`, `archive / mark superseded`, `needs human review`.

Draft major entries with this structure:

```markdown
# [Wiki Entry Title]

## Definition
[Concise, source-grounded definition.]

## Why It Matters
[Project-specific relevance.]

## Current Best Understanding
[What the evidence currently supports.]

## Evidence
- [Source ID, page/slide/section]: [Evidence summary]

## Timeline
- [Date]: [What changed or became known]

## Related Concepts
- [Concept]: [Relationship]

## Related Entities
- [Entity]: [Relationship]

## Open Questions
- [Question]

## Confidence
High / Medium / Low

## Tags
[project], [theme], [entity], [workstream], [status]
```

### 9. Decision Support Brief

End with a short decision brief:

```markdown
# Decision Support Brief

## Bottom Line
[1-3 sentence synthesis of what the research currently says.]

## What We Know
- [Source-supported point]

## What Is Changing
- [Theme or evidence shift over time]

## What Is Uncertain
- [Gap, contradiction, or unresolved issue]

## Strategic Implications
- [Implication]

## Recommended Next Moves
- [Action]

## Evidence Quality
High / Medium / Low, with rationale.
```

## Final Output Order

1. Source coverage summary
2. Source inventory table
3. Document-level extractions
4. Cross-document themes
5. Theme evolution over time
6. Research arc summary
7. Concept map
8. Entity and relationship table
9. Contradictions / tensions
10. Active project implications
11. Wiki entry recommendations
12. Draft wiki entries
13. Decision support brief
14. Open questions and missing evidence
15. Suggested next ingestion priorities

## Persistence Guidance

Do not persist the whole ingestion package as one giant entry by default. Persist durable outputs as separate plugin entries when they will be useful independently:

- project research arc
- evidence package
- key concept entries
- contradiction or tension notes
- decision support brief
- source-specific entries when a source is central enough to retrieve directly

Each persisted entry still follows the normal three-layer contract:

- frontmatter with `workflow: collection` or `workflow: synthesis`
- `projects: [<project-name>]` when project-specific
- concise `TL;DR`
- cited `Notes` with backlinks
- `Raw` source extracts needed for future verification

Skip generated indexes and derived dashboards during ingest. Durable inputs are substantive source documents and source-grounded wiki pages.

## Quality Gate

Before finalizing, verify:

- every factual claim has a source reference
- important dates are captured
- older and newer evidence are distinguished
- contradictions are flagged
- inferences are labeled
- key entities and concepts are linkable
- decision implications are separate from raw facts
- open questions are specific enough to guide follow-up research
- the synthesis reflects the full source set, not only the most recent or polished document
