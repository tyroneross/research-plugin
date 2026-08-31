# Deep Research Architecture Reference

This reference turns deep research into an explicit evidence pipeline for this plugin. It is based on:

- *Reference Architecture for a Deep Research Agent System* (local PDF, user-provided, reviewed 2026-07-08)
- User-provided notes on Deep Research source intake, file parsing, Deep Agents, and evidence QA
- OpenAI Deep Research, File Search, and MCP search/fetch documentation reviewed on 2026-07-08

OpenAI documents the broad Deep Research behavior and tool constraints, not its proprietary internal state machine. Treat this file as an implementation architecture for this plugin, not as a claim about private OpenAI internals.

## Bottom Line

Deep research should run as a governed evidence pipeline:

```text
clarify -> plan -> source -> parse -> normalize -> index -> search/fetch -> verify -> synthesize -> QA -> persist
```

The operating principle is:

```text
parse deterministically, retrieve selectively, reason agentically, verify mechanically
```

Agents are useful for planning, search pivots, evidence selection, synthesis, and caveat judgment. They are not the right layer to guarantee that PDFs, spreadsheets, charts, slides, or scanned files were faithfully converted into evidence.

## Core Design Rules

1. **Intake is a typed service, not a free-form research agent.** File classification, extraction, normalization, hashing, and parse-quality scoring should be deterministic where possible.
2. **Every source becomes evidence records.** Preserve source identity, content hash, parser/tool, extraction confidence, source tier, provenance, and raw reference.
3. **Research agents query evidence through search/fetch.** A deep research-compatible tool should expose searchable/fetchable records, not arbitrary backend file processing.
4. **Claims are separate from sources.** A claim is only shippable when it is bound to supporting evidence and a citation location.
5. **Unsupported claims fail closed.** If a claim is insufficiently supported, retrieve more, qualify it, or remove it.
6. **Contradictions are first-class findings.** Do not smooth conflicts away; record the disagreeing sources and their tiers.

## Planes

| Plane | Role | Agentic? | Output |
|---|---|---|---|
| Intake | Detect source type, permissions, hash, parser route, extraction result, quality score | Mostly no | Normalized source/evidence records |
| Evidence | Store raw files, normalized elements, FTS/BM25 index, table outputs, source registry | No | Searchable and fetchable evidence |
| Research | Decompose question, search, fetch, compare, pivot, synthesize | Yes | Evidence-backed findings and claim table |
| Assurance | Claim-source alignment, contradiction scan, freshness check, numerical verification, citation QA | Semi-agentic with hard gates | Pass/fail/qualified report |

## Intake Pipeline

Use this path whenever the source set includes PDFs, Office files, spreadsheets, structured data, directories, or visual-heavy material:

```text
file/source arrives
-> intake manifest
-> source/type/permission classifier
-> parser router
-> normalized document elements
-> quality scoring and provenance capture
-> raw storage plus FTS/table/index records
-> research search/fetch
-> claim verification and synthesis
```

Minimum intake manifest:

| Field | Meaning |
|---|---|
| `source_id` | Stable ID for this source in the run or corpus |
| `source_location` | URL, local path, linked project path, or app/file reference |
| `source_type` | web, pdf, docx, pptx, xlsx, csv, code, markdown, image, directory, database |
| `content_hash` | SHA-256 when local content is available |
| `permissions` | public, uploaded, local, connected app, private, unknown |
| `captured_at` | Fetch/extract date |
| `parser` | WebFetch, Read, omniparse, table-profile, db-profile, manual, or other |
| `parser_version` | Tool version or plugin version when known |
| `extraction_status` | success, partial, failed, skipped, cached |
| `extraction_confidence` | high, medium, low |
| `parse_notes` | What may be missing: OCR, charts, formulas, hidden sheets, tables, layout |
| `raw_ref` | Path or section where raw output is preserved |

## Normalized Evidence Model

Represent extracted content as document elements. This keeps mixed sources searchable without flattening tables, figures, slides, or formulas into ambiguous prose.

```yaml
source_id: "S1"
file_hash: "sha256:..."
document_type: "pdf"
source_location: "/path/to/source.pdf"
captured_at: "2026-07-08"
parser: "omniparse"
parser_version: "..."
elements:
  - element_id: "S1.E1"
    element_type: "paragraph"   # title | paragraph | list | table | chart | image | formula | note | code | metadata
    text: "..."
    structured_data: null
    page: 4
    slide: null
    sheet: null
    cell_range: null
    bounding_box: null
    section_path: "2. Source Intake"
    extraction_confidence: "medium"
    structure_confidence: "high"
    provenance: "page 4, section 2"
    parse_notes: []
```

Current plugin persistence can store this in markdown frontmatter, `## Raw` headings, source registers, and evidence packages. Future runtime work can move the same shape into SQLite tables without changing the research workflow.

## Parser Routing

| Source type | Preferred route | Preserve | Main failure mode |
|---|---|---|---|
| HTML/public web | WebFetch or browser fetch | URL, capture date, page title, quoted passages | Dynamic pages, stale pages, paywalls |
| Short simple PDF | Host `Read` pages | Page numbers and raw text | Missed tables/figures |
| Long PDF/scanned/table-heavy PDF | `/research:extract`, then manual quality review | Page, section, table/figure references, layout gaps | OCR/layout/table loss |
| DOC/DOCX | Parser route before synthesis | Heading hierarchy, comments, tables, footnotes | Flattened sections |
| PPTX/deck | `/research:extract`; review notes/images | Slide number, title, bullets, speaker notes, embedded chart context | Missing visual meaning or notes |
| XLSX/Excel | `/research:extract --sheet` plus `table-profile`/analysis when quantitative | Sheets, named ranges, formulas, hidden sheets, charts, cell ranges | Treating formulas/tables as plain text |
| CSV/TSV/JSONL | `table-profile` and generated analysis for quantitative claims | Schema, units, nulls, grain, row counts | Embedding rows without schema context |
| Images/charts/scans | OCR or visual extraction outside synthesis; record confidence | Text, axes, labels, legend, bbox, source table if known | Hallucinated values from low-res images |
| Markdown/TXT/JSON/YAML | Host `Read` | Raw file path, headings, line references | Usually low risk |
| Code/Python | `/research:extract` or repo search/read | Symbols, AST structure, line refs | Losing execution context |
| SQLite/database | `db-profile`, then `analyze-plan`/`analyze-run` | Schema, row counts, indexes, query outputs | Unsupported joins or hidden assumptions |

If extraction confidence is low, do not let synthesis treat the source as fully reliable. Either rerun with a better route, restrict claims to what the parser captured, or mark the source as partial.

## Capture Sizing

**Retain condensed notes with short quoted fragments, not a verbatim dump of the source.** The content hash covers whatever you keep, so a 200-word note carrying the load-bearing sentences is exactly as claim-eligible as a 5,000-word transcription, and is more useful to the next reader.

| Rule | Why |
|---|---|
| Target roughly 100 to 500 words per capture | Enough to support several claims and to re-read later without refetching |
| At most one or two direct quotes, each under about 25 words | The quote carries the claim; the surrounding note carries the context |
| Never paste long verbatim passages of a copyrighted work | Reproduction at length serves no evidentiary purpose here, wastes worker context, and has been observed to trip model output filters mid-run, killing the worker before it registers anything |
| Record what the excerpt does NOT cover in `parse_notes` | A capture is a sample; say so when tables, figures, or later sections were skipped |

Register a capture with `scripts/register_source.py`, which hashes the file, writes a conforming manifest, calls `source-record`, and prints the `observation_id` to bind claims to. It warns above 500 words. Hand-authoring the manifest is where runs most often lose `content_hash`, `published_at`, or `locator` and fail the merge gate long after the fetch context is gone.

**Register as you go, not at the end.** A worker that fetches everything and registers in one final pass loses all of it if the turn ends early. Registration is cheap and idempotent per capture file.

## Indexing Strategy

The plugin's current stable index is SQLite FTS5 over markdown. Keep using it at personal scale, but index the right artifacts:

| Artifact | Current storage | Retrieval purpose |
|---|---|---|
| Source register | Evidence package / frontmatter | Authority, freshness, independence, role |
| Raw extracts | `## Raw` and archive raw files | Verifier and future re-reading |
| Evidence items | Evidence package and `## Notes` | Claim-level retrieval |
| Tables/profiles | Analysis artifacts and Raw refs | Exact numerical claims |
| Linked project files | Linked-project registry and FTS | Project-local prior research |

Do not add a vector database unless FTS5/BM25 demonstrably fails for the corpus. For future semantic retrieval, add it behind the same evidence schema rather than replacing source registers and provenance.

## Deep Research-Compatible Tool Interface

OpenAI Deep Research MCP guidance expects a search/fetch shape. Use this as the target interface for any future source index:

```text
search(query, filters) -> ranked evidence records
fetch(id) -> full source element with provenance
```

`search` should return enough metadata for triage:

```yaml
id: "S1.E4"
title: "..."
snippet: "..."
source_id: "S1"
source_type: "pdf"
tier: "T1"
role: "primary/original"
published_at: "2026-01-15"
captured_at: "2026-07-08"
score:
  final: 0.82
  authority: 0.90
  lexical: 0.74
  semantic: null
  evidence_density: 0.80
  recency: 0.70
extraction_confidence: "medium"
provenance: "page 8, table 2"
```

`fetch` should return the full element, surrounding context, raw reference, parse notes, and all citation/provenance fields. The research agent should not need to parse the original file again unless `fetch` reveals low confidence.

## Scoring

Use deterministic source scoring for authority, then add retrieval and extraction confidence.

Practical weighted retrieval score for deep runs:

| Component | Weight | Meaning |
|---|---:|---|
| Authority/source tier | 0.30 | T1/T2 sources should dominate when relevant |
| Lexical/BM25 match | 0.25 | Exact names, dates, model IDs, numbers |
| Semantic fit | 0.20 | Conceptual relevance if semantic index exists |
| Evidence density | 0.15 | Passage contains a concrete supportable claim |
| Recency/version fitness | 0.10 | Current enough for the question |

When no semantic index exists, redistribute the semantic weight across lexical match, authority, and evidence density. Never use score alone as proof; score is a triage signal.

## QA Gates

Use these gates for deep, decision-grade, or high-stakes research:

| Gate | Target | Failure action |
|---|---:|---|
| Authority ratio | >= 60% of core sources are T1/T2 when available | Search primary/official sources |
| Retrieval coverage | >= 3 distinct high-quality sources per major subquestion when available | Loop to source strategy |
| Rerank relevance | >= 0.65 for used evidence, if scored | Drop weak hits or search again |
| Atomic factual support | >= 90% of factual claims supportable | Verify, qualify, or remove claims |
| Citation precision | >= 90% of citations actually support nearby text | Rebind citations |
| Citation recall | >= 85% of factual paragraphs cited | Add citations or remove unsupported text |
| Unresolved contradictions | 0 for final answer; otherwise explicit conflict section | Surface conflict and confidence impact |
| Duplicate rate | <= 10% near-duplicate sources in core set | Deduplicate and prefer origin |
| Schema validity | 100% for saved evidence packages | Fix before persistence |

## Assurance Workflow

For each important claim:

```text
candidate claim
-> find supporting evidence element
-> check source authority and independence
-> check parse confidence
-> check contradiction/counter-evidence
-> bind citation location
-> mark supported, contradicted, insufficient, or qualified
```

Unsupported or low-confidence claims should not silently survive into the final report. The synthesis should either remove them or label them as inferred/uncertain.

## Plugin Application Checklist

Use this checklist when improving or running the research plugin:

- [ ] Source set has an intake manifest or source register before synthesis.
- [ ] Binary/mixed files go through `/research:extract`, `table-profile`, `db-profile`, or another explicit parser route before claims are made.
- [ ] Raw parser output is saved under `## Raw`, inbox, archive, or a linked raw reference.
- [ ] Evidence items include source, location, extraction type, extraction confidence, and parse notes when relevant.
- [ ] Tables/spreadsheets use quantitative analysis before numerical claims.
- [ ] Visual-heavy documents are marked partial unless charts/images were explicitly extracted or described with confidence.
- [ ] Search/fetch-style evidence records are preferred over asking a research agent to re-open arbitrary files.
- [ ] Final synthesis has claim-level citations, contradiction handling, source coverage, and limitations.

## References

- Local PDF: *Reference Architecture for a Deep Research Agent System* (user-provided, reviewed 2026-07-08)
- OpenAI Deep Research API: `https://developers.openai.com/api/docs/guides/deep-research`
- OpenAI Deep Research in ChatGPT: `https://help.openai.com/en/articles/10500283-deep-research-in-chatgpt`
- OpenAI File Search: `https://platform.openai.com/docs/assistants/tools/file-search`
- OpenAI MCP search/fetch cookbook: `https://developers.openai.com/cookbook/examples/deep_research_api/how_to_build_a_deep_research_mcp_server/readme`
