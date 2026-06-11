---
description: Deep active-project wiki ingestion for source-grounded research corpora
argument-hint: <source-path-or-topic> [--project foo] [--update-existing] [--merge-prior]
allowed-tools: Bash, Read, Write, WebFetch
---

Run the active-project research ingestion workflow when sources need to become durable project wiki memory.

Use `skills/research/references/active-project-ingestion.md` as the controlling reference. This command is for source-dense, decision-relevant project ingestion where chronology, contradictions, assumptions, concepts, and wiki update recommendations need to survive future retrieval.

**Workflow**

1. Inventory the provided source path or topic and identify source type, date, scope, methodology, status, and confidence.
2. Extract each source before synthesis. Preserve claims, metrics, assumptions, risks, stakeholders, decisions, and open questions with source locations.
3. Cluster repeated observations into themes only after document-level extraction.
4. Build theme evolution, concept maps, contradictions, project implications, wiki entry recommendations, and a decision support brief.
5. Persist durable outputs through the normal `/research:save` flow as separate entries when useful. Do not save one giant package unless the user explicitly asks for that.

**Persistence rule**

Project-specific saved entries should include `projects: [<project>]`, `workflow: collection` or `workflow: synthesis`, source-backed `Notes`, and `Raw` excerpts sufficient for future verification.

If the request is only bulk markdown import, use `/research:ingest` instead. If the request is only parking files for later review, use `/research:ingest --inbox`.
