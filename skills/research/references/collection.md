# Collection Modes — Evidence Extraction Reference

Collection is the phase where raw sources become structured evidence. This file defines 4 modes optimized for different source types and failure modes, plus a deep research architecture overlay for deterministic intake/parsing and an active-project wiki overlay for durable project memory ingestion.

## Mode Selection

| Source Type | Mode | Why |
|-------------|------|-----|
| General web sources, mixed documents | **Standard** | Balanced depth, multi-source extraction |
| PDFs with tables, figures, technical specs | **Technical PDF** | Layout-aware extraction, completeness logging |
| Mixed binaries, spreadsheets, scans, visual-heavy decks, reusable source indexes | **Deep Research Architecture Overlay** | Parser routing, normalized evidence records, provenance, extraction confidence, search/fetch readiness |
| Quick decision support, time-constrained | **Concise** | Brevity filter, bullet-only, decision-relevance |
| 5+ sources, large document sets, literature | **Large Corpus** | Triage first, tiered depth, deduplication |
| Active project wiki ingestion, evolving research corpus | **Active Project Wiki Overlay** | Preserves chronology, contradictions, concepts, and decision relevance |

**Auto-selection:** Default to Standard. Switch when:
- User provides PDFs or mentions technical documents → Technical PDF
- Source set includes mixed file types, Excel/tables, scans, charts, visual-heavy slides, or future source indexing → apply the Deep Research Architecture Overlay before synthesis
- User asks for "quick", "brief", "just the key points" → Concise
- Source count exceeds 5 or user mentions "survey", "review", "all the literature" → Large Corpus
- User mentions active project wiki, project memory, chronology, evolving themes, contradictions, or wiki update recommendations → apply the Active Project Wiki Overlay after Standard or Large Corpus extraction

**User override:** Always accept explicit mode requests. If ambiguous, ask.

---

## Shared Rules (Apply to All Modes)

### Source-Faithful Extraction

Replace "verbatim extraction" with **source-faithful extraction**:

1. **Preserve meaning precisely** — Capture what the source actually says, not what you expect it to say
2. **Exact wording required** when the claim is:
   - Contentious or likely to be disputed
   - A precise technical specification
   - A direct quote attributed to a person
   - Mark with `[direct quote]`
3. **Quantitative data exactly** — Numbers, dates, versions, percentages, units. Never round, approximate, or convert without noting it
4. **Paraphrase for clarity** when meaning is preserved and wording is incidental — mark with `[paraphrased]`
5. **Never flatten** — Two distinct claims from the same source stay as two evidence items, even if thematically related

### Grouping Constraints

- Group evidence by source first, then by theme within source
- Never merge claims from different sources into a single evidence item
- If two sources make similar claims, record both separately — similarity is a finding, not a reason to merge

### Collector Notes

Collector notes capture observations *about* the evidence, not interpretations of it:
- "Source focuses heavily on performance but doesn't mention security" — valid
- "This suggests the team prioritized speed over safety" — **not valid** (that's interpretation, save for synthesis)
- "Table on page 12 appears to have inconsistent units" — valid
- "Author seems biased toward their own product" — valid (observation about source, not claim)

### Source Register

Before synthesis, maintain a source register for standard and deep collection:
- **Source**: Name + URL/path
- **Tier**: T1-T4 with short rationale
- **Date**: Publication/update date plus access date when relevant
- **Coverage role**: Primary/original, independent corroboration, counter-evidence, temporal/currentness, or gap lead
- **Independence note**: Whether it shares authorship, dataset, benchmark, citation chain, press release, or vendor origin with another source
- **Disposition**: Deep-read, standard extract, skimmed for unique claim, or skipped with reason
- **Extraction status/confidence**: success/partial/failed/skipped/cached plus high/medium/low confidence when the source came through a parser
- **Parser/provenance**: tool, flags, content hash/cache key, and the strongest available location granularity

The register is part of the evidence package. A missing coverage lane is recorded as a gap, not hidden.

### Evidence Item Fields

Every evidence item must have:
- **ID**: Sequential within the collection (E1, E2, E3...)
- **Claim**: The extracted finding
- **Source**: Name + identifier (URL, page number, section)
- **Tier**: T1-T4 with brief rationale
- **Corroboration**: Status from credibility framework
- **Date**: Publication or access date
- **Context**: Where in the source this appears (section, page, paragraph)
- **Extraction type**: `[direct quote]` | `[paraphrased]` | `[quantitative]`
- **Extraction confidence**: high, medium, or low when parser quality matters
- **Provenance**: page, slide, sheet, cell range, section, line, or bounding-box reference when known
- **Parse notes**: OCR/layout/table/chart/formula limitations that affect confidence

---

## Deep Research Architecture Overlay

Use `deep-research-architecture.md` when the collection must support expansive future research, reusable source indexing, mixed-file intake, or high-confidence citation binding.

### Required Additions

1. **Intake manifest** — one row per source with `source_id`, location, source type, permissions, content hash, parser, capture date, extraction status, extraction confidence, raw reference, and parse notes.
2. **Parser routing** — explicitly choose WebFetch, Read, `/research:extract`, table profile, database profile, or generated analysis before extracting claims.
3. **Normalized evidence elements** — preserve element type (`paragraph`, `table`, `chart`, `image`, `formula`, `note`, `code`), structured data when available, and provenance.
4. **Search/fetch readiness** — record enough metadata that a future search result can be fetched back to the exact source element.
5. **QA gates** — before synthesis, check source authority, retrieval coverage, parse confidence, contradiction status, and citation support.

### When to Escalate

Escalate from ordinary collection to this overlay when any of these are true:

- The source set is intended to seed a reusable index of credible/helpful sources.
- A file has tables, charts, formulas, OCR, scans, hidden sheets, or slide visuals that may be lost in plain text.
- A final answer needs claim-level citations with high confidence.
- The user asks for "deep research", "more expansive", "more thorough", "index sources", "ingest and parse", or "future use".
- The output will become a persistent corpus rather than a one-time summary.

### Fail-Closed Rule

If parser quality is uncertain, the evidence item can still be saved, but synthesis must mark the claim as low confidence, partial, or unsupported until a better extraction path verifies it.

---

## Standard Mode

Default for general multi-source research.

### Workflow

1. **Coverage map** — Identify primary/original, independent, counter-evidence, temporal/currentness, and gap lanes for the question
2. **Source register** — List all sources to be collected from, with tier, date, coverage role, independence note, and disposition
3. **Sequential extraction** — For each source:
   a. Read/fetch the full source
   b. Identify all relevant claims, data points, and findings
   c. Extract each as a separate evidence item with full fields
   d. Note what the source does NOT address (gaps are evidence)
4. **Cross-source notes** — After all sources collected:
   a. Flag where sources agree (potential SUPPORTED)
   b. Flag where sources disagree (potential CONTESTED)
   c. Note independence relationships between sources
   d. Identify the strongest counter-evidence and whether it changes the answer
5. **Package** — Assemble into evidence package format (see `output-contracts.md`)

### Depth Target
- 4-10 evidence items per substantial source
- Fewer for brief sources, more for dense ones
- Every claim that answers or informs the research question gets extracted

---

## Technical PDF Mode

Optimized for PDFs with structured data: tables, figures, methodology sections, appendices.

### Additional Extraction Templates

#### Table Extraction
For each relevant table:
- **Table ID**: T1, T2... (within this collection)
- **Location**: Page number, section
- **Caption/Title**: Exact caption
- **Structure**: Rows x Columns, headers
- **Key data points**: Extract the specific cells relevant to research question
- **Units**: Note all units; flag inconsistencies
- **Notes**: Footnotes, caveats, methodology notes attached to the table

#### Figure Extraction
For each relevant figure:
- **Figure ID**: F1, F2...
- **Location**: Page number, section
- **Caption/Title**: Exact caption
- **Type**: Chart, diagram, photograph, schematic
- **Key observations**: What the figure shows relevant to research question
- **Axis/labels**: For charts — axes, units, scale
- **Limitations**: What the figure doesn't show or may obscure

#### Methodology Extraction
When the source describes a methodology:
- **Design**: Study type, sample size, duration
- **Variables**: What was measured, what was controlled
- **Limitations**: Stated limitations (and any obvious unstated ones — mark as collector note)
- **Reproducibility**: Could someone replicate this? What's missing?

### Completeness Logging

After extracting from a PDF, log:
- Sections reviewed vs. sections skipped (with reason for skipping)
- Tables/figures found vs. extracted (with reason for skipping any)
- **Layout gaps**: Areas where PDF formatting may have caused extraction errors (multi-column text, embedded images breaking text flow, scanned pages)

---

## Concise Mode

Optimized for brevity and decision-relevance. Used when the user needs quick answers, not comprehensive evidence packages.

### Format Rules

- **Bullet-only** — No prose paragraphs in evidence items
- **One claim per bullet** — Never compound bullets
- **Decision-relevance filter** — Before including an evidence item, ask: "Would this change a decision?" If no, skip it
- **Max 3-5 evidence items per source** — Extract only the most decision-relevant

### Simplified Confidence Tags

Replace the full two-dimensional credibility assessment with shorthand:

| Tag | Meaning | Maps To |
|-----|---------|---------|
| `HIGH` | T1/T2 + PRIMARY or SUPPORTED | Authoritative or Strong |
| `MEDIUM` | T1/T2 + SINGLE-SOURCE, or T3 + SUPPORTED | Credible but unverified, or Corroborated low-tier |
| `LOW` | T3/T4 + SINGLE-SOURCE | Weak |
| `CONTESTED` | Any + CONTESTED | Disputed — note briefly |
| `SPECULATIVE` | Any + SPECULATIVE | TAG:INFERRED |

### Cross-Source Notes (Concise)

After collection, one section with:
- **Agreements**: Bullet list of claims where sources align
- **Conflicts**: Bullet list of contradictions with brief context
- **Gaps**: What wasn't addressed by any source

---

## Large Corpus Mode

Optimized for 5+ sources. Prevents drowning in low-value extraction by triaging first.

### Phase 1: Source Triage

Before extracting anything, scan all sources and classify. Deep research usually targets 10 sources and may triage up to 15 when the topic is broad, high-stakes, or contradictory.

| Priority | Criteria | Extraction Depth |
|----------|----------|-----------------|
| **Deep** | T1/T2, directly addresses research question, original data | Full extraction — all relevant evidence items |
| **Standard** | T2/T3, partially relevant, derivative but adds context | Key claims only — 3-5 evidence items |
| **Light** | T3/T4, tangential, redundant with higher-priority sources | Skim for unique claims not found elsewhere — 0-2 items |
| **Skip** | Irrelevant, superseded, or clearly unreliable | Document reason for skipping, extract nothing |

Record the triage decision and rationale for each source.

### Phase 2: Tiered Extraction

Extract in priority order (Deep first). After each priority tier, check:
- Is the research question adequately answered?
- Are there gaps that lower-priority sources might fill?
- Stop when diminishing returns are clear.

### Phase 3: Deduplication

After extraction, identify duplicate or near-duplicate claims:
1. **Exact duplicates**: Same claim from multiple sources → Keep the highest-tier version, note others as corroboration
2. **Near-duplicates**: Similar claims with different specifics → Keep both, note the difference
3. **Derivative claims**: Source B clearly restates Source A → Note the dependency, keep only if B adds context

### Phase 4: Independence Verification

For all claims marked SUPPORTED, verify independence:
- Check citation chains — do the sources cite each other?
- Check upstream — do they reference the same original data?
- Document the independence assessment for each SUPPORTED claim

### Appendix: Light-Reviewed Sources

Sources classified as "Light" or "Skip" go into an appendix:
- Source name and URL
- Triage classification and rationale
- Any unique claims extracted (for Light)
- Reason for exclusion (for Skip)

This preserves the research trail without cluttering the main evidence package.

---

## Active Project Wiki Overlay

Use `active-project-ingestion.md` when the source set should update durable project memory, not just answer the immediate question. This overlay usually rides on Standard mode for small source sets and Large Corpus mode for bigger source sets.

The overlay adds these outputs after source-level extraction:

- source register before synthesis
- document-level extractions with assumptions, risks, stakeholders, decisions, and open questions
- cross-document theme discovery from repeated observations
- timeline of theme evolution
- concept map and relationship table
- contradictions and tensions
- active project implications
- wiki entry recommendations and draft entries
- decision support brief

Persist durable outputs as separate plugin entries when useful. Do not save one giant ingestion package unless the user explicitly asks for a single archival report.
