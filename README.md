# research

Personal research plugin for Claude Code and Codex. Keeps a central, searchable, lifecycle-managed knowledge base of everything you research, with project-linked views so research stays visible alongside code.

## Install

### Claude Code

```
/plugin marketplace add tyroneross/research-plugin
/plugin install research@research-plugin
```

Then install the Python dependency:

```bash
pip install pyyaml            # required
pip install sympy             # optional (v0.2 symbolic verification)
```

Restart Claude Code. The `/research:*` slash commands should autocomplete; the `research` skill activates on phrases like "research X", "investigate Y", "what's the current state of Z".

### Codex

Install from a configured Codex marketplace that points at this repository:

```bash
codex plugin add research@ross-labs-local
```

Codex loads the same plugin root: `.codex-plugin/plugin.json`, `commands/`, `skills/`, `hooks/`, `data/`, `vendor/omniparse/`, and `research.py`. Commands and skills resolve the runtime root from `RESEARCH_PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, or `CODEX_PLUGIN_ROOT`.

## First run

By default, any `/research ...` session writes its markdown corpus to `~/dev/research/` and keeps its SQLite index there too. Or bootstrap explicitly:

```bash
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" init
```

## Roots

The plugin now supports separate roots for content and derived index/state:

- `RESEARCH_CONTENT_DIR` — canonical markdown corpus, generated markdown views, archive, inbox, project symlinks
- `RESEARCH_INDEX_DIR` — SQLite DB, linked-project registry, verifier logs, extract cache
- `RESEARCH_BASE_DIR` — legacy compatibility alias; if the new vars are unset, both roots fall back here

Default behavior:

- content root: `~/dev/research/`
- index root: `~/dev/research/`

## Layout

Content root:

- `<content-root>/topics/<topic-tree>/<slug>.md` — canonical entries
- `<content-root>/indices/<topic>.md` — auto-generated Maps of Content
- `<content-root>/index.md`, `by-topic.md`, `by-project.md`, `review-due.md`, `PORTFOLIO.md` — auto-generated dashboards
- `<content-root>/archive/` — archived entries (never deleted, redirect stubs left behind)
- `<content-root>/inbox/` — fleeting notes / files queued via `/research:ingest --inbox`
- `<content-root>/projects/` — project symlink views

Index root:

- `<index-root>/.db.sqlite3` — FTS5 index, domain scores, verifier state
- `<index-root>/.linked-projects.json` — linked external project registry
- `<index-root>/verifier-log/` — verification artifacts
- `<index-root>/.extract-cache/` — Omniparse extract cache

## Per-project research

Two mechanisms, depending on who authored the research.

**Plugin-authored entries** — when an entry's frontmatter includes `projects: [foo]` and a project directory exists, `/research:save` maintains a symlink at `<content-root>/projects/foo/<slug>.md` pointing to the canonical entry under `<content-root>/topics/`. The project directory is not modified. Pass `--with-project-index` if you also want a `<project>/RossLabs-Research.md` index file written into the project (opt-in).

**Pre-existing project research** — for directories like `~/dev/git-folder/SpeakSavvy-iOS/docs/research/` that predate this plugin and should not be restructured, use `/research:link-project <name> <path>`. The plugin walks the directory recursively for `*.md` files, extracts a title and a 1-line summary from each, records the registration in `<index-root>/.linked-projects.json`, and creates symlinks at `<content-root>/projects/<name>/<filename>`. The source directory is never modified.

Both mechanisms surface in `<content-root>/PORTFOLIO.md` under separate sections ("Plugin-managed projects" and "Linked external research directories"). `/research:index` refreshes both.

Legacy v0.3.0 artifacts (`<project>/research/` file copies, `<project>/research/.live/` symlinks, `<project>/RossLabs-Research.md`) are preserved as-is — v0.3.1 does not write to these paths by default, but also does not delete them. A one-time note is printed when the plugin touches a project that still has them.

## Subcommands

| Command | Purpose |
|---|---|
| `/research:init` | Bootstrap the configured content and index roots |
| `/research:save <file>` | Persist an entry (Phase 6 entry point); writes canonical + project symlink, regenerates portfolio. `--with-project-index` to also write `<project>/RossLabs-Research.md` |
| `/research:ingest <path>` | Bulk-ingest existing markdown files; `--inbox` to park, `--save` to persist drafts |
| `/research:search <query>` | FTS5-ranked plain-text search across canonical entries and linked external project files. Use `--fts-query` for raw FTS5 syntax or `--entries-only` to exclude linked files |
| `/research:depth <query>` | Classify a request as light, standard, or deep before sourcing |
| `/research:list [N]` | Recent entries |
| `/research:link <slug>` | Retroactive project symlink for a saved entry |
| `/research:link-project <name> <path>` | Register an existing external research directory (plugin does not modify it) |
| `/research:sync` | Rebuild SQLite from canonical topic markdown; use `--prune-missing` after moves or migrations |
| `/research:index` | Rebuild central indexes, refresh plugin-managed symlinks, re-scan linked external projects, and rewrite `PORTFOLIO.md` |
| `/research:recategorize` | Suggest splits for top-level topics that have grown too large (read-only) |
| `/research:archive <slug>` | Move to archive, leave redirect stub |
| `/research:score <url>` | Inspect or set source tier for a domain |
| `/research:verify <slug>` | Run claim verification on an entry |
| `/research:table-profile <path>` | Profile CSV/TSV/JSON data before quantitative analysis |
| `/research:db-profile <path>` | Profile a SQLite database schema, row counts, indexes, and foreign keys |
| `/research:analyze-plan --input <path> --question "..."` | Generate a self-contained stdlib Python analysis plan/script |
| `/research:analyze-run --plan <analysis-plan.yaml>` | Run the generated analysis script and write results/audit artifacts |
| `/research:review` | Surface stale / review-due entries |
| `/research:compress <slug>` | Compact an entry's TL;DR and Raw sections |
| `/research:extract <path>` | Route PDF/Excel/PPTX/Python/dir through vendored Omniparse and capture source-intake metadata |
| `/research:optimize <request>` | Turn a raw request into a claim-safe research contract: decision card, meta-questions, MECE sub-question groups, section contracts, 0-24 readiness score |
| `/research:dashboard <audit.json> --out <file.html>` | Render a capability audit (subjects × dimensions with evidence, pipelines, recommended flow) into one self-contained HTML dashboard; `--validate-only` checks the payload. Skill: `skills/audit-dashboard/` |

## Search

`/research:search` defaults to safe plain-text search: punctuation-heavy terms such as `research-plugin` are quoted before they reach FTS5, and results include highlighted snippets. Canonical entries and linked external project files are searched together unless `--entries-only` is passed. Raw FTS5 syntax remains available with `--fts-query` for advanced queries.

## Research depth

`/research:depth` is a deterministic pre-flight classifier for choosing scope. It returns `light`, `standard`, or `deep`, plus source budget, coverage requirements, workflow, web requirement, persistence guidance, and rationale.

- `light` — quick answer, usually 0-2 sources, skip persistence unless reusable.
- `standard` — bounded research, usually 3-8 sources with a target of 5, persist when the answer becomes report-sized.
- `deep` — decision-grade or explicitly thorough/expansive research, usually 7-15 sources with a target of 10, verify and persist by default.

Standard and deep runs plan source coverage before fetching: primary/original sources, independent corroboration, counter-evidence, temporal/currentness checks, and explicit gaps. The goal is wider evidence coverage plus source-faithful extraction, not shallow source-count padding.

For expansive deep research, the skill now includes a deep research architecture overlay: deterministic intake, parser routing, normalized evidence records, search/fetch-style source access, and QA gates for claim support and citation precision. See `skills/research/references/deep-research-architecture.md`.

## Vendored dependencies

`/research:extract` routes document parsing (PDF, Excel, PPTX, Python, directories) through a self-contained, pre-built copy of `@tyroneross/omniparse` that ships with this plugin at `vendor/omniparse/`. All JS runtime deps are inlined — no `npm install` needed. Only `node >= 18` must be on PATH.

- Upstream: https://github.com/tyroneross/Omniparse (see `vendor/omniparse/.upstream` for the exact commit)
- License: FSL-1.1-MIT (copied verbatim to `vendor/omniparse/LICENSE`)
- Re-vendor: follow `vendor/omniparse/BUILD.md`

A user-installed `omniparse` on `PATH` will be preferred over the vendored copy when present.

## Philosophy

- **Non-LLM parsers first, LLM for judgment** — the host agent's WebFetch/Read tools and vendored parsers extract content; scripts compute what can be computed.
- **Parse first, reason second** — mixed files become normalized evidence with provenance and extraction confidence before synthesis.
- **Code does the math** — quantitative/database claims should go through profile → analysis plan → generated stdlib Python script → results/audit with High/Medium/Low certainty.
- **Deterministic over clever** — same URL always scores the same tier; same claim always routes to the same verifier.
- **Never delete** — archive + redirect stubs preserve all inbound links.
- **Three layers** — TL;DR (≤150 words, extractive), Notes (bolded key passages + citations), Raw (verbatim source excerpts for future verification).

## Plugin surface

The repository root is the package root for both hosts.

- Claude Code manifest: `.claude-plugin/plugin.json`
- Codex manifest: `.codex-plugin/plugin.json`
- Slash commands: `commands/*.md`
- Skill: `skills/research/SKILL.md`
- Advisory hook: `hooks/hooks.json`
- Runtime: `research.py`
