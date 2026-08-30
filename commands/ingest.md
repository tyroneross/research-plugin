---
description: Bulk-ingest existing markdown files into ~/dev/research/ as draft entries
argument-hint: <path> [--project foo] [--topics a,b,c] [--inbox] [--save]
allowed-tools: Bash, Read, Write
---

Walk a file or directory of `.md` files and produce draft entries. The Python layer is purely deterministic (slug from filename, title from first H1, body wrapped into TL;DR/Notes/Raw skeleton). Anything semantic — picking topics, tagging sources by tier, pruning the body — is for you (the LLM) to do after seeing the drafts.

This command is for markdown intake only. For PDFs, Office files, spreadsheets, directories of mixed binaries, scans, charts, or visual-heavy decks, run `/research:extract` first and use `skills/research/references/deep-research-architecture.md` to record parser route, raw reference, extraction confidence, and provenance.

```bash
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" ingest $ARGUMENTS
```

**Modes**

- No flags: print drafts to stdout, do not save. Inspect, fill in topics/tags, then call `/research:save` per file.
- `--save`: persist each draft via the normal save flow (creates canonical file, project copy, symlink, indexes).
- `--inbox`: copy raw files to `~/dev/research/inbox/` without any drafting or DB write. Use this to "park" sources you want to review later.
- `--project foo`: auto-tag drafts with the named project (must match a directory under `~/dev/git-folder/`).
- `--topics a,b,c`: comma-separated topic list applied to every draft.

**Source-intake fields to preserve when known**

- `source_location`
- `source_type`
- `content_hash`
- `captured_at`
- `parser` / `parser_version`
- `extraction_status`
- `extraction_confidence`
- `parse_notes`
- `raw_ref`
- page, slide, sheet, cell range, section, or line provenance

**Recommended LLM-assisted flow (slash command):**

1. Run `/research:ingest <path>` (no `--save`) to see the drafts.
2. For each draft, decide on topics, tags, source tiers, and slug refinements.
3. Edit the draft text in your head (or in a tmp file), then call `/research:save <tmp.md>` for that one entry.

**Active project wiki ingestion**

If the user asks to ingest research into an active project wiki, preserve chronology, track evolving themes, flag contradictions, or produce wiki update recommendations, do not treat this as routine bulk import. Run `research.py active-ingest` per `skills/research/references/active-project-ingestion.md`, then persist durable outputs through `/research:save` as separate collection or synthesis entries when useful.

For a fully automated dump (e.g. importing 50 old notes that you trust as-is), pass `--save` directly. Drafts are marked `confidence: inferred` and `status: fleeting` so the next `research.py review` pass surfaces them for proper synthesis.
