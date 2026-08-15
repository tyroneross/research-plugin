---
description: Extract PDF / Excel / PPTX / Python / directory into clean markdown via @tyroneross/omniparse, with source-intake metadata (content-hash cached)
argument-hint: <path> [--no-cache] [-r] [-f markdown|text|json] [--sheet NAME] [--no-notes] [-o file]
allowed-tools: Bash
---

Extract structured content from local files through the user's own `@tyroneross/omniparse` CLI. Use this when the host agent's built-in tools fall short or when a source needs reusable intake metadata before research.

**Router:**

| Source | Tool |
|---|---|
| HTML URL | `WebFetch` (this command rejects URLs) |
| Short PDF (≤10 pages, simple text) | Host `Read` with `pages=` — no extract needed |
| Any PDF | Omniparse |
| Excel (`.xlsx/.xls/.csv/.tsv/.ods/.xlsb`) | Omniparse (`--sheet NAME` for a single sheet) |
| PowerPoint (`.pptx`) | Omniparse (`--no-notes` to strip speaker notes) |
| Python source (`.py`) | Omniparse (AST-level structured markdown) |
| Directory | Omniparse (`-r` to recurse) |
| Markdown / txt / JSON / YAML | Host `Read` tool directly |

**Intake rule:** extraction is source intake, not synthesis. Before using extracted output as evidence, record:

- source path or URL
- content hash or cache key
- parser/tool and flags
- capture date
- extraction status: success, partial, failed, skipped, or cached
- extraction confidence: high, medium, or low
- parse notes: OCR/layout/table/formula/chart/hidden-sheet risks
- provenance granularity: page, slide, sheet, cell range, section, line, or unknown

For mixed, visual-heavy, table-heavy, or reusable source sets, use `skills/research/references/deep-research-architecture.md` as the controlling reference. Treat the result as normalized evidence that later research should search/fetch, not as a polished report.

**Caching:** Every successful extract is cached at `~/dev/research/.extract-cache/<sha256>-<flags>.md` keyed by file content + flags. Re-reading the same file with the same flags is instant. `--no-cache` forces re-extraction.

```bash
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" extract $ARGUMENTS
```

Output is markdown to stdout by default. Paste into the `## Raw` section of the entry you're persisting in Phase 6, tagged with the source path, capture date, extraction method, cache key/hash, confidence, and parse notes. If the source is spreadsheet/database-shaped, run `/research:table-profile`, `/research:db-profile`, or the quantitative analysis workflow before making numerical claims.

Omniparse ships vendored at `${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/vendor/omniparse/dist/bin/omniparse.js` (self-contained, no install required). Only `node >= 18` must be on PATH. A user-installed `omniparse` on PATH will override the vendored copy when present. See `vendor/omniparse/BUILD.md` to re-vendor from upstream.

See `references/persistence.md` for the full decision table.
