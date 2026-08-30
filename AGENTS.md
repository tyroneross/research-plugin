# research plugin

Central, token-efficient research knowledge base. Persists findings to `~/dev/research/` with project-local symlinks, deterministic source tier scoring, and optional claim verification.

## Scope

- Single-user personal tool. Not published to any marketplace.
- Data lives at `~/dev/research/` (separate from this plugin dir so the plugin can be replaced without touching knowledge).
- One Python script (`research.py`) with subcommands handles all mutations.
- SQLite FTS5 (stdlib `sqlite3`) is the index. No external search service.
- Codex uses local coding tools first for repository evidence, the on-device in-app Browser for public HTML source reading, and the structured `web__run` search/open connector as backup. `Read` handles local text and supported documents; no Python HTML extraction library is needed.

## Entry point

- Slash commands (13, the highest-traffic workflows): `/research:research` (router — top-of-funnel, full research flow on a topic: frame, source, execute, synthesize, deliver, persist to `~/dev/research/`), `/research:feedback`, `/research:optimize` (turn a raw request into a claim-safe research contract), `/research:extract`, `/research:analyze-plan`, `/research:analyze-run`, `/research:save`, `/research:link-project`, `/research:index`, `/research:search`, `/research:ingest`, `/research:table-profile`, `/research:db-profile`
- Direct: `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" <subcommand>` — every other `research.py` subcommand (`init`, `depth`, `list`, `link`, `sync`, `archive`, `score`, `verify`, `calculate`, `doctor`, `doctor-plan`, `source-record`, `source-index`, `legacy-source-import`, `trust-record`, `graph-export`, `traversal-record`, `run-init`, `run-validate`, `run-merge`, `run-stage`, `run-metrics`, `eval-check`, `review`, `compress`, `recategorize`) lost its slash-command wrapper in a 2026-08 surface reduction but is unchanged and still fully callable this way; the `research` skill itself invokes these directly via Bash rather than through a slash command. `/research:dashboard` was also removed — that capability now lives entirely in the `audit-dashboard` skill (`skills/audit-dashboard/scripts/render_dashboard.py`), which has no `research.py` subcommand.
- Via skill: user language matching the `research` skill's description triggers the full-flow, which ends by persisting via Phase 6.
- Skills: `research` (general flow; Phase 1 = query optimization), `research-orchestrator` (vendor-neutral parallel evidence contracts, bounded deep-link traversal, deterministic merge), `financial-research` (margin, COGS, cost buckets, filings, operating-model analysis), and `audit-dashboard` (render a capability audit as a self-contained HTML dashboard).

## How research gets persisted

1. User asks Codex to research something.
2. `research` skill runs Phases 1-5 (optimize → source → execute → synthesize → deliver): Phase 1 produces a decision card, one or more meta-questions, MECE sub-question groups, and section contracts that Phase 2 executes and Phase 4/5 checks off as the coverage summary.
3. **Phase 6**: Codex writes a three-layer markdown entry (TL;DR / Notes / Raw) with rich frontmatter, then invokes `research.py save` which:
   - upserts into SQLite,
   - writes the canonical entry to `~/dev/research/topics/<top>/<slug>.md`,
   - for each project in `projects:`, maintains a symlink at `~/dev/research/projects/<project-name>/<slug>.md` pointing to the canonical entry (link-only; no writes into the project directory),
   - regenerates `~/dev/research/PORTFOLIO.md` (master corpus index across all projects),
   - triggers index rebuild for the central indexes via hook.

Pass `--no-index` to defer portfolio regen on a single save (run `/research:index` to flush). Pass `--with-project-index` to opt in to writing `<project>/RossLabs-Research.md` inside the project (default is to leave the project untouched).

## Linking existing project research

For project directories that already contain research markdown files the plugin did not author (for example `~/dev/git-folder/SpeakSavvy-iOS/docs/research/`), use `/research:link-project <name> <path>`. The plugin walks the directory recursively for `*.md` files, extracts a title (first `# H1`) and a 1-line summary (first paragraph, first sentence, truncated to 120 chars) from each, records the registration in `~/dev/research/.linked-projects.json`, and creates symlinks at `~/dev/research/projects/<name>/<filename>`. The source directory is never modified. Re-running the command refreshes the registration and symlinks (idempotent); `/research:index` also re-scans every registered linked project.

The portfolio has two project sections: "Plugin-managed projects" (from save's `projects:` tag) and "Linked external research directories" (from link-project). Cross-cutting entries (no project tag) appear below.

Legacy v0.3.0 artifacts — `<project>/research/` file copies, `<project>/research/.live/` symlinks, and `<project>/RossLabs-Research.md` — are preserved as-is. v0.3.1 no longer writes to these paths by default, but also never deletes them. A one-time informational note is printed when the plugin touches a project with such artifacts.

## Dependencies

- Required: `PyYAML` (frontmatter parsing).
- Optional (v0.2+): `sympy` for symbolic math verification. Graceful skip if absent.
- Optional (extraction): vendored `@tyroneross/omniparse` CLI (Node.js, user-authored, FSL-1.1-MIT) lives at `vendor/omniparse/dist/bin/omniparse.js` as a self-contained, pre-built bundle — all runtime deps (xlsx, sax, p-limit) are inlined, so no `npm install` is required. Resolved in order: `shutil.which("omniparse")` first (allows a global override), then the vendored copy via `node`. Re-vendor upstream changes by following `vendor/omniparse/BUILD.md`. `node` >= 18 must be on PATH.
- Everything else is Python stdlib or Codex built-in tools. No AGPL deps, no model-weight downloads, no external Python extraction libraries.

## Not to do

- Don't call external LLM APIs from scripts. Codex (this runtime) does any LLM work.
- Don't construct ad-hoc wrappers around connector calls. Use the connector's published structured schema; after an invocation error, retry one minimal valid request and then fall back to Browser or a known official URL.
- Don't add extraction libraries (trafilatura/pymupdf/etc.) — the host fetch and file-read tools cover it.
- Don't add a vector database. SQLite FTS5 with BM25 is sufficient at personal-scale corpora.
- Don't delete research files. Archive via redirect stub (`status: archived`) so inbound links still resolve.
- Don't write to the host's own config directory (`.codex/`, `.claude/`). Plugin data goes under its own `.<toolname>/` namespace per global AGENTS.md.
