---
description: Search the research library with safe FTS5/BM25 ranking and snippets
argument-hint: <query> [--tag X] [--topic Y] [--project Z] [--entries-only] [--fts-query] [-n 20]
allowed-tools: Bash
---

Search the research library. BM25-ranked across title, TL;DR, Notes, and Raw for canonical entries, plus linked external project markdown files registered through `/research:link-project`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" search $ARGUMENTS
```

Default mode treats the query as plain text and safely quotes tokens before sending them to FTS5, so terms like `research-plugin` work without special escaping. Results include highlighted snippets.

Use `--fts-query` when you want raw FTS5 syntax: phrase `"chain of thought"`, boolean `cot AND reasoning`, prefix `agent*`, column filter `title: prompting`. Use `--entries-only` to exclude linked external files.

Present the top results with kind, slug, title, confidence, reviewed date, and snippet. Offer to `cat` the most promising entry if the user wants the full content.
