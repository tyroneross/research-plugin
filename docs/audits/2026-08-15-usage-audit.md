# Research plugin usage audit — 2026-08-15

**Scope:** how the `research` plugin (v0.5.2) has actually been used across Codex, Claude Code, and other agents.
**Method:** static mining of local agent transcripts, the `~/dev/research/` store, routing config, and repo history. Read-only with respect to plugin code.
**Status markers:** ✅ verified (command re-executed by the report author) · ⚠️ untested/partial · ❓ uncertain.

---

## 1. Headline verdict

The plugin is real, working software that Codex uses and Claude Code effectively does not: **325 executed CLI invocations from Codex** across 33 sessions versus **17 from Claude Code** across the entire retained transcript corpus — a 19:1 split on a plugin that is installed and enabled in both hosts (✅). The cause is not quality but routing: the global `~/.claude/CLAUDE.md` research policy never names the plugin, so Claude Code's 881 WebSearch and 729 WebFetch calls bypassed a 187-entry knowledge base that no Claude Code session ever queried with `research:search` (✅).

Usage has also stopped. The last Codex invocation was **2026-07-31**, the last repo feature commit was **2026-06-10**, and the last commit of any kind was **2026-07-14** (✅). The store keeps growing — 100 of 187 indexed entries were created in July–August — but through direct file writes and Codex `save` calls rather than through the 23 documented command surfaces, **8 of which have never been invoked by any host, ever** (✅).

---

## 2. Usage summary

### 2.1 Evidence corpora and their limits

| Corpus | Size | Retention window | Command |
|---|---|---|---|
| Claude Code transcripts | 1,853 `.jsonl`, 147 project dirs, 1.8 GB | **Mar 20 · Apr 10 · Jul 1,099 · Aug 732 files** | `find ~/.claude/projects -name '*.jsonl' \| wc -l`; monthly via `stat -f '%Sm' -t '%Y-%m'` |
| Codex sessions | 2,207 `.jsonl`, 9.6 GB | Apr → Aug, continuous | `find ~/.codex/sessions -name '*.jsonl' \| wc -l`; `du -sh ~/.codex/sessions` |
| `~/dev/research/` store | 374 `.md` (217 canonical entries), 17 MB | Apr 17 → Aug 14 | `find ~/dev/research -name '*.md' -type f \| wc -l` |
| Shell history | 1,008 + 500 lines | to Aug 14 | `grep -c 'research.py' ~/.zsh_history ~/.bash_history` |

⚠️ **Claude Code May and June transcripts have been purged** — zero files with those mtimes. Every Claude Code number below is a lower bound covering Mar–Apr and Jul–Aug only. Codex retention is intact across the full period, so the host comparison is *conservative against Codex*: a complete Claude Code corpus would raise its count somewhat, but not by the order of magnitude the gap represents.

### 2.2 Command × host

Counts are **executed invocations**, not mentions. A surface appearing in a session's skill-roster system prompt is not usage; the roster block alone produced ~10,000 raw string hits against 6 real Skill calls.

| Surface | Codex (CLI) | Claude Code | Other agents | Human manual | Total | First → last |
|---|---|---|---|---|---|---|
| `save` | 88 | 9 | 0 | 0 | **97** | 2026-04-19 → 2026-08-14 |
| `search` | 85 | 1 (this audit) | 0 | 0 | **86** | 2026-04-19 → 2026-07-31 |
| `verify` | 36 | 0 | 0 | 0 | **36** | 2026-04 → 2026-07 |
| `depth` | 34 | 6 | 0 | 0 | **40** | 2026-04 → 2026-08-12 |
| `--help` | 29 | 2 | 0 | 0 | **31** | — |
| `sync` | 18 | 0 | 0 | 0 | **18** | 2026-04 → 2026-07 |
| `index` | 13 | 0 | 0 | 0 | **13** | 2026-04 → 2026-07 |
| `list` | 8 | 1 (this audit) | 0 | 0 | **9** | — |
| `init` | 4 | 1 | 0 | 0 | **5** | 2026-04 → 2026-07-14 |
| `score` | 3 | 0 | 0 | 0 | **3** | — |
| `link-project` | 3 | 0 | 0 | 0 | **3** | — |
| `ingest` | 2 | 0 | 0 | 0 | **2** | — |
| `table-profile` | 1 | 0 | 0 | 0 | **1** | — |
| `analyze-plan` | 1 | 0 | 0 | 0 | **1** | — |
| `db-profile` | 0 | 1 (this audit) | 0 | 0 | **1** | 2026-08-15 |
| `research` (skill/slash) | — | 12 | 0 | 0 | **12** | 2026-07-14 → 2026-08-14 |
| **CLI total** | **325** | **21** (17 excl. this audit) | **0** | **0** | — | 2026-04-19 → 2026-08-15 |

Claude Code's 12 skill/slash activations break down as 5 × `Skill(research:research)`, 1 × `Skill(research)` (bare), 3 × `/research`, 3 × `/research:research` (✅ `grep -oh '"skill":"[^"]*"'` and `grep -oh '<command-name>[^<]*</command-name>'` histograms over all 1,853 files).

### 2.3 Host verdicts

**Codex — WIRED and dominant.** `~/.codex/config.toml:41` registers `[plugins."research@ross-labs-local"] enabled = true`; line 613 enables the `post_tool_use` hook with a pinned trust hash. The cached install at `~/.codex/plugins/cache/ross-labs-local/research/local/research.py` is byte-identical to the repo file (`diff -q` exit 0). 325 invocations across 33 of 2,207 sessions (1.5%), monthly Apr 45 · May 66 · Jun 51 · Jul 163 · **Aug 0**. Top workdirs: ObsidianVault (71), build-loop (55), research-plugin (46, dev work), research (31), rosslabs-agent-harness (22), personal-llm-wiki (14), a private work-notes vault (12). ✅

**Claude Code — installed, enabled, effectively unrouted.** Symlinked at `~/.claude/plugins/research → <this repo checkout>` and enabled via `settings.json:531`. 17 non-audit CLI calls plus 12 skill/slash activations, against 881 WebSearch and 729 WebFetch calls in the same corpus (✅). Of 320 total Skill-tool calls, `build-loop:build-loop` took 138 and `research:research` took 5.

**Other agents — zero.** `~/.gemini`, `~/.cursor`, and `~/.opencode` all exist on disk; none references `research.py`, `research-plugin`, or `~/dev/research` (⚠️ existence and grep verified by subagent, not re-executed by the author).

**Human manual — zero.** `grep -c 'research.py'` returns 0 in both `~/.zsh_history` and `~/.bash_history` (✅). Every invocation on this machine came from an agent.

**build-loop automated — zero, and it built a competing store.** `scripts/research_trigger.py` is a pure classifier with no dispatch; `Skill("build-loop:research")` (a different, `user-invocable: false` skill) is what build-loop actually calls; and `scripts/reference_capture.py` writes captured findings to `build-loop-memory/projects/<project>/research/` — **124 files** in a corpus parallel to this plugin's 217 (⚠️ counted by subagent). Same facts land in both: the Groq model catalog exists as `~/dev/research/topics/infra/infra.llm.groq-provider-catalog.md` *and* `build-loop-memory/projects/build-loop/research/2026-08-07-reference-groq-model-catalog-and-production-selection.md`.

### 2.4 Top topics

By entry count in `topics/`: llm (30), design (16), agentic-systems (10), knowledge-graphs (9), product-dev (8), tools (7), projects (6), build-loop (5), agents (5), speech (4). By tagged project: unassigned (48), build-loop (15), atomize-ai (15), claude-code-personal (14), speaksavvy (11), rosslabs-agent-harness (9) (✅ `sqlite3 -readonly ~/dev/research/.db.sqlite3`).

### 2.5 Unused surfaces

**Never invoked by any host, in either corpus, across the full retention window (8 surfaces):**
`active-ingest` · `extract` · `review` · `link` · `archive` · `compress` · `recategorize` · `analyze-run`

**Invoked only by this audit (1):** `db-profile`.
**Invoked once or twice in four months (4):** `table-profile` (1), `analyze-plan` (1), `ingest` (2), `score` (3), `link-project` (3).

That is **9 of 23 surfaces at zero real usage and 5 more in the noise** — roughly 60% of the command surface has never earned its maintenance cost.

---

## 3. Friction points

### 3.1 The routing gap is the whole story (severity: critical)

`~/.claude/CLAUDE.md` contains **zero** occurrences of `research:`, `research-plugin`, or `dev/research` (✅ `grep -c` returns 0, 0, 0). Its Research section (lines 110–146) fires aggressively — "bias toward over-triggering" — and its action ladder routes to api-registry, then WebSearch, then WebFetch. The plugin is not a rung on that ladder.

The consequence is measurable: 1,610 WebSearch + WebFetch calls in the retained Claude Code corpus, and **not one `research:save` following them** to persist the result. Findings were fetched, used, and discarded. Meanwhile `ai-assistant`'s registry *does* route correctly (`"owner": "research", "invoked_as": "skill:research:research"`), which is why the 12 Claude Code skill activations exist at all — every one came through that path or an explicit user slash command, never through the global policy (⚠️ registry inspection by subagent).

### 3.2 Three `research` skills, three different files

| Path | md5 | Lines | mtime |
|---|---|---|---|
| `research-plugin/skills/research/SKILL.md` | `688bbb35…` | 321 | 2026-07-14 |
| `build-loop/skills/research/SKILL.md` | `b8a7a0b2…` | 117 | 2026-07-26 |
| `~/.claude/skills/research/SKILL.md` | `b40a03dc…` | 199 | **2026-03-16** |

Three distinct files, not symlinks (✅ `md5 -q`). The third is a **legacy personal copy predating the plugin by four months**, with 6 reference files against the plugin's 12 and no depth-classifier call. It still answers to "research", "investigate", "evaluate" — and one Claude Code invocation resolved to the bare `research` skill rather than `research:research`, which is exactly this collision firing. build-loop's copy is `user-invocable: false` so it cannot be reached by slash, but it competes for the same internal `Skill()` intent.

### 3.3 `verify` fails 39% of the time because `extract` is never run

Codex CLI calls correlated to their exit codes: **44 failures of 325 (13.5%)** (✅ call_id correlation across 989 files).

| Failing subcommand | Failures | Calls | Rate |
|---|---|---|---|
| `verify` | 14 | 36 | **38.9%** |
| `save` | 12 | 88 | 13.6% |
| `search` | 8 | 85 | 9.4% |
| `depth` | 6 | 34 | 17.6% |

Exit codes: 26 × exit 2, 10 × exit 1, 7 × exit 127, 1 × exit 128. Signatures: `ERROR:` 13, `Traceback` 10, `usage:` 10, `unrecognized arguments` 9, `command not found` 7, `Operation not permitted` 6.

The causal chain is legible: `verify` requires an atoms file produced by `extract`; `extract` has **zero recorded invocations on either host**; `verify` therefore dies on `ERROR: no atoms file at …/atoms.json. Extract atoms first`. A required precondition step that nobody knows to run is a workflow defect, not a user error.

Other recurring failures, each repeating across months rather than once:
- `zsh:1: command not found: python` (exit 127) — recurring 04-30, 05-28, 07-05. Fixed at HEAD by commit `c9ea7b8` "use python3 for plugin commands", but the agents kept typing `python`.
- `unrecognized arguments: --limit` on `search` (exit 2) — agents repeatedly assumed a flag the CLI does not have (05-28, 07-05).
- `Query error: no such column: plugin` — FTS5 parsed the hyphenated query `research-plugin` as column syntax (05-27, ×3). Unescaped user input reaching the FTS matcher.
- `Traceback … sys.exit(main())` at line 2483 (v0.3.1) and line 3699 (v0.5.1) — the same unguarded-exception shape surviving a version bump.

(⚠️ Individual snippets are quoted from the Codex mining subagent; the aggregate failure rate and per-subcommand breakdown were re-derived independently by the author.)

### 3.4 Data-store integrity

- **Index is stale by 14%.** 217 canonical entries on disk against **187 rows** in `~/dev/research/.db.sqlite3` — **30 entries unindexed and therefore invisible to `search`**, concentrated in May (✅). `sync` has not run since July.
- **Two dead decoy databases.** `index.db` (0 bytes, Jul 23) and `research.db` (0 bytes, Aug 7) sit beside the real `.db.sqlite3`. Neither is read by the CLI. Any human or agent inspecting the directory will reach for the wrong file — and one already did.
- **Provenance is not recorded.** No `host`, `agent`, `tool`, `model`, `client`, `generator`, or `session_id` frontmatter field exists on any entry (0 files each). `source_host` appears in 2 of 217; `created_by` in 2, holding an opaque `AGENT-REQ-001`. **Under 3% coverage across three incompatible ad hoc conventions.** This audit had to reconstruct host attribution from transcripts because the store itself cannot answer "who wrote this" — the single highest-leverage missing field.
- **Controlled vocabulary has drifted.** `status` holds 17 distinct values (evergreen 92, literature 37, actionable 12, complete 11, active 7, fleeting 6 … plus singletons `seedling`, `canonical`, `proposed`). `confidence` holds 16, most of them free prose: `"medium-high (article T2 recognized expert; corroborating stats T2-arXiv + T3/T4 industry)"` is a value in a field that should be an enum. `workflow` holds 12. Filtering and faceted search degrade accordingly (✅ `GROUP BY` queries).
- **Duplicates.** 5 titles appear twice under different slugs in different topic folders, confirmed as true content duplicates, e.g. `agentic-systems/agentic-systems.multi-peer-coordination-standalone-extraction-2026-05-20.md` vs `multi-peer-coordination-standalone-extraction/multi-peer-coordination-standalone-extraction.md` (⚠️ subagent-confirmed).
- **12 files have malformed frontmatter** (no leading `---`); 8 are experiment scratch files that arguably should not live in `topics/` at all.
- Healthy: 197 symlinks with **0 broken**, 0 stub files, and `PORTFOLIO.md` regenerated within 1 second of the newest entry — the portfolio pipeline works.

### 3.5 Duplication with neighbouring tools

**build-loop** consumes `~/dev/research/` as a citation source (referenced in `agents/independent-auditor.md:198`, `agents/design-contract-specialist.md:239`) but writes its captures to its own memory store, never back. Two corpora, one purpose, no reconciliation. A backlog item proposing the fix — `build-loop-memory/projects/build-loop/issues/bl-research-plugin-trigger-policy.md`, created 2026-06-07, status `ready` — has sat unexecuted for ten weeks (⚠️ subagent-reported).

**api-registry / Context7** overlap narrowly and are correctly first on CLAUDE.md's ladder for per-library docs. The real gap is that the ladder **ends** at "got the doc" with no handoff to synthesis-and-persist. These tools are complements, not competitors; the missing piece is the seam between them.

### 3.6 Repo state

- **Stalled.** 33 commits total: Apr 20, May 4, Jun 7, Jul 2. Last commit 2026-07-14 (32 days ago); **zero feature commits since 2026-06-10** (⚠️ subagent git log).
- **An unfinished feature is sitting uncommitted.** 43 modified + 4 deleted tracked files, +482/−1005, plus 4 untracked. It is a coherent piece of work — generalizing the plugin from Claude-Code-only to dual-host, widening `hooks/hooks.json` to fall back through `RESEARCH_PLUGIN_ROOT` → `CLAUDE_PLUGIN_ROOT` → `CODEX_PLUGIN_ROOT`, adding a Codex install section to the README, and adding a deep-research-architecture overlay whose reference file is still untracked. Given that Codex is the plugin's dominant consumer, **this is the most valuable uncommitted work in the repo** (⚠️ characterized by subagent from sampled diffs; not re-read line by line by the author).
- **Test discovery is broken by naming.** `python3 -m pytest -q` reports `no tests ran in 0.01s` because the three suites are named `*_check.py`, which pytest's default discovery ignores. Run directly, all three pass (`research_depth_check.py`, `search_quality_check.py`, `connector_policy_check.py`, exit 0 each). CI or any agent running the conventional command sees a green no-op (⚠️ subagent-run).
- **Install is duplicated.** Claude Code resolves `research` through the dev-repo symlink, while `installed_plugins.json` points at a marketplace cache entry. Of the two cache dirs, `e97091896725/research.py` is byte-identical to HEAD (`50248c59…`) but its manifest **has no `version` field**, and the sibling `0.5.1/` copy is genuinely stale (3,699 vs 3,793 lines) (✅ `md5 -q`). Functionally benign today; a trap the moment someone edits the wrong copy.
- **`research.py` is a 3,793-line, 111-function monolith** mixing argparse, schema, SQLite, markdown generation, and Omniparse routing in one file, sectioned only by comment banners (⚠️ subagent measurement).

### 3.7 Phase 1 collapses several questions into one (added 2026-08-15 after user review)

`skills/research/SKILL.md:151` instructs: **"Research question — One clear question. Restate vague requests as specific questions."** `references/methodology.md:109` mentions sub-questions only as a fallback when a question proves intractable. There is no step that identifies the *meta-question(s)* behind a request, no decision card, and no MECE decomposition into sub-question groups that map to sections of the output (✅ grep of `SKILL.md` + `references/`).

The user's stated preference is the opposite default: do **not** force distinct questions into one; name the meta-question(s), then break each into sub-questions organized into MECE themes. Two existing artifacts already encode this and were not consulted when the skill was written:

- **A private work-notes question-design guide** (2026-07-19, confidence medium-high, read-only source, not in this repo): a *decision card* filled before drafting (decision → "by the end we need to know" → flagship question → required scope/basis → minimum useful answer → what changes depending on the answer), then **project decision components as MECE section headings**, with five evidence checks (scope · direct answer · drivers · boundaries · confidence) applied *within* sections rather than as section titles, and a per-question standard (one ask · short · concrete · basis-defined · neutral first). Built for expert calls; the framing discipline transfers directly to a research brief.
- **The work-machine fork of this plugin** (see §3.8) already ships an `optimize` phase and "section contracts with exact questions, evidence requirements, expected outputs, and completion rules" plus a query ledger — i.e., the meta-question → sub-question → section mapping this repo lacks.

Consequence today: multi-part requests ("compare X and Y and tell me whether Z still holds") get flattened into a single restated question, the output has no section-per-sub-question structure to be MECE against, and coverage gaps are invisible because there is no list of sub-questions to check off.

### 3.8 The plugin has forked: the work machine runs 0.5.3 with features this repo does not have (added 2026-08-15)

A private work-notes tool card (updated 2026-07-27) documents a **second canonical source** at the work machine's canonical checkout (path withheld — work-machine local), shared release **0.5.3**, installed in both Codex (`research@personal`, `0.5.3+codex.20260727150324`) and Claude Code (`research@personal-shared`) via local marketplaces, with source/cache parity verified 2026-07-27. This repo is **0.5.2** (`plugin.json`, `package.json` ✅). The work fork's documented capabilities absent here (✅ grep of `commands/`, `skills/`, `tests/` returns nothing for `optimize`, `section contract`, `query ledger`, `readiness`):

| Work fork 0.5.3 (per the work-notes card) | This repo 0.5.2 |
|---|---|
| `/research:optimize` — Q0–Q4 optimization levels, 0–24 readiness score across scope/time/definitions/evidence/metrics/comparisons/output; separates user facts, hypotheses, requested tests, unsupported assumptions | absent |
| Deep-research orchestration: section contracts, query ledger, source + claim registers, cross-section synthesis, explicit unresolved gaps | partial (`deep-research-architecture.md`, untracked) |
| Financial/operating-model controls: term authority, period/currency/numerator/denominator, attribution ladder, cost-bucket overlap groups | absent |
| Tests: `deep_orchestration_contract_check.py`, `financial_research_contract_check.py` (+ depth, search-quality) | depth, search-quality, connector-policy only |
| Depth vocabulary: quick / balanced / deep | light / standard / deep |
| `RESEARCH_CONTENT_DIR` / `RESEARCH_INDEX_DIR` split roots | `RESEARCH_PLUGIN_ROOT` only |

⚠️ The work fork is not on this machine; the comparison rests on the work-notes card, not a diff. ❓ Whether the fork was branched from this repo's uncommitted dual-host work (§3.6) or independently is unknown — that card was written 2026-07-27, twelve days after this repo's last commit and during the window the dual-host change set was being edited. Either way: **two 0.5.x lineages, the more capable one undocumented here, and the less capable one is the GitHub-published source of truth.**

---

## 4. Suggestions, ranked by leverage

### Do these

**1. Add the plugin to `~/.claude/CLAUDE.md`'s research ladder.** — effort **XS**
*Where:* `~/.claude/CLAUDE.md` lines 110–146, action ladder. Add a persistence rung: after api-registry/WebSearch returns, `research:save` the synthesis; before searching, `research:search` the local KB.
*Evidence:* 0 occurrences of the plugin in that file; 1,610 web-fetch calls with 0 follow-on saves; 12 Claude Code activations all arriving through other routes (§3.1). This single edit addresses the largest measured gap in the audit and costs one paragraph.

**2. Record provenance on every entry.** — effort **S**
*Where:* `research.py` `cmd_save`, frontmatter emitter — add `host`, `agent`, `tool_version`, `session_id`, populated from env (`CLAUDE_PLUGIN_ROOT`/`CODEX_PLUGIN_ROOT` already distinguish hosts).
*Evidence:* <3% provenance coverage forced this entire audit to reconstruct attribution from 11.4 GB of transcripts (§3.4). With this field, the same question becomes one `sqlite3 GROUP BY`. It also makes the next audit possible after transcripts are purged — as May and June already were.

**3. Make `verify` bootstrap its own atoms.** — effort **S**
*Where:* `cmd_verify` — if the atoms file is absent, call the extract path directly rather than exiting 2.
*Evidence:* 38.9% failure rate on `verify`, cause traced to `extract` having zero invocations across both hosts (§3.3). The highest-failure command fails for a reason entirely within the plugin's control.

**4. Commit or delete the dual-host work.** — effort **S**
*Where:* the 47-file uncommitted change set.
*Evidence:* Codex is 95% of usage (325 of 342 CLI calls) and the uncommitted diff is precisely the Codex-hardening work (§3.6). Leaving it unstaged for a month keeps the dominant host on a path the repo does not officially support. If it is not going to land, revert it so the tree stops lying about its state.

**5. Run `sync` and delete the decoy databases.** — effort **XS**
*Where:* `~/dev/research/` — one `research.py sync`, then `rm index.db research.db`.
*Evidence:* 30 of 217 entries unindexed and unsearchable; two 0-byte files that already misled a reader in this audit (§3.4).

**6. Rename the test files to `test_*.py`.** — effort **XS**
*Evidence:* `pytest -q` currently exits green having run nothing (§3.6). A green no-op is worse than a red failure — it certifies absence of testing as presence of passing.

**7. Delete the legacy `~/.claude/skills/research/`.** — effort **XS**
*Evidence:* Four months stale, distinct md5, competing triggers, and at least one observed misroute to the bare `research` skill (§3.2). Nothing references it; the plugin supersedes it entirely.

**8. Constrain `status` and `confidence` to enums.** — effort **S**
*Where:* `cmd_save` validation + a one-off migration.
*Evidence:* 17 and 16 distinct values respectively, including a 108-character prose string in `confidence` (§3.4). Free text in a filter field means the filter does not work.

**9. Retire the 8 never-invoked surfaces.** — effort **M**
*Where:* `active-ingest`, `extract` (fold into `verify` per #3), `review`, `link`, `archive`, `compress`, `recategorize`, `analyze-run`.
*Evidence:* Zero invocations across 11.4 GB of transcripts spanning four months and two hosts (§2.5). Each carries a command file, docs, and CLI surface. Deprecate behind a flag first if deletion feels premature — but stop documenting them as though they are used.

**10. Close the build-loop double-store.** — effort **M**
*Where:* `build-loop/scripts/reference_capture.py`, or the ten-week-old `bl-research-plugin-trigger-policy.md` backlog item.
*Evidence:* 124 parallel files, demonstrated duplicate capture of the same Groq catalog facts (§3.5). Pick one store. ❓ Which direction is correct is a design decision this audit does not have the standing to make.

**11. Reframe Phase 1 as decision → meta-question(s) → MECE sub-question groups; port `optimize` from the work fork.** — effort **S** (skill text) / **M** (with `optimize` port) · *added 2026-08-15 after user review; leverage places it directly after #1*
*Where:* `skills/research/SKILL.md` §Phase 1 (line 151) and §Phase 2; `references/methodology.md`; new `commands/optimize.md` mirroring the work fork.
*Change:* replace "One clear question" with: (a) a decision card (decision the research informs · what we must know by the end · flagship question · scope + basis · minimum useful answer · what changes with the answer); (b) identify one or more **meta-questions** — never merge distinct questions; (c) decompose each meta-question into sub-questions grouped into **MECE themes that become the output's section headings**, with scope/direct-answer/drivers/boundaries/confidence as evidence checks inside each theme; (d) carry the sub-question list into Phase 2 as section contracts (exact question · evidence required · completion rule) and check it off at Phase 4/5 as the coverage summary.
*Evidence:* §3.7 — the skill's own instruction collapses questions; the goal-led MECE guide and the work fork's `optimize` already solve this; `deep-research-architecture.md:198` already assumes "major subquestions" exist that no upstream step produces.
*UX:* multi-part asks stop being flattened; the delivered answer is sectioned per sub-question so gaps are visible; the same sub-question list drives Codex section fan-out.

**12. Reconcile the fork.** — effort **M**
*Where:* this repo ↔ the work machine's canonical checkout (path withheld — work-machine local).
*Change:* diff 0.5.3 against this tree (including the uncommitted dual-host set), decide the canonical lineage, and land the delta here — at minimum `optimize`, the two contract tests, the split content/index roots, and the quick/balanced/deep vocabulary decision. Record the outcome in this repo's CHANGELOG and the work-notes tool card (read-only from here — update from the work machine).
*Evidence:* §3.8. Suggestion #4 (commit the dual-host work) is a prerequisite: reconciling against a dirty tree hides which side introduced what.

### Do not do these

- **Do not conclude the plugin is unused and archive it.** 325 Codex invocations across 33 sessions and seven distinct project workdirs say otherwise. The Claude Code number is a routing artefact, not a verdict on value.
- **Do not rewrite `research.py` into modules yet.** The monolith is ugly (3,793 lines) but produced zero of the 44 observed failures — those were preconditions, argument errors, and environment issues. Refactoring is real work with no evidence behind it while the routing gap is unfixed.
- **Do not add new commands.** 60% of the existing surface is at or near zero usage. Nothing in the evidence points at a missing capability; the evidence points at unreachable existing ones.
- **Do not treat the version drift as urgent.** The active cache copy is byte-identical to HEAD (✅ md5). The stale `0.5.1/` dir and the missing `version` field are hygiene, not breakage — worth fixing in passing, not worth a task.
- **Do not build usage telemetry into the plugin.** Suggestion #2 (provenance frontmatter) answers the same question as a side effect of a write that already happens, with no new collection surface and no privacy question.
- **Do not "fix" the duplicate entries by automated dedupe.** 5 pairs, human-authored, possibly deliberate forks. ❓ Not enough evidence to distinguish drafts from genuine duplicates; this needs a human read, not a script.

---

## 5. Method and evidence appendix

### 5.1 Counting discipline

A plugin surface named in a session's system prompt is not usage. Every Claude Code session lists all installed skills, so raw `grep 'research:'` matched 444–821 files per command — approximately 10,000 string hits against 6 real Skill invocations. All counts in this report are **executed tool calls**, identified by JSON shape:

- **Claude Code Skill:** assistant `tool_use` block, `{"type":"tool_use","name":"Skill","input":{"skill":"research:…"}}`
- **Claude Code slash:** `<command-name>/research…</command-name>`
- **Claude Code Bash:** `tool_use` with `name=="Bash"`, `input.command` matching `python3?\s+…research\.py\s+<subcommand>`
- **Codex:** `payload.type=="function_call"`, `payload.arguments` parsed as JSON, `command`/`cmd` matching the same pattern; exit status read from the correlated `function_call_output` by `call_id`

File-inspection calls (`cat`, `grep`, `head` on `research.py`) were classified separately: 38 in the Claude Code corpus, excluded from invocation counts. An unrelated `market-research-platform/graph/research.py` was excluded by path.

### 5.2 Headline commands

```bash
# Corpus sizing
find ~/.claude/projects -name '*.jsonl' | wc -l                    # 1853
find ~/.claude/projects -name '*.jsonl' -exec stat -f '%Sm' -t '%Y-%m' {} \; \
  | sort | uniq -c                                                 # Mar 20, Apr 10, Jul 1099, Aug 732
find ~/.codex/sessions -name '*.jsonl' | wc -l                     # 2207
du -sh ~/.codex/sessions                                           # 9.6G

# Claude Code activations
find . -name '*.jsonl' -print0 | xargs -0 grep -oh '"skill":"[^"]*"' \
  | sort | uniq -c | sort -rn                                      # research:research 5, research 1
find . -name '*.jsonl' -print0 | xargs -0 grep -oh '<command-name>[^<]*</command-name>' \
  | sort | uniq -c | sort -rn                                      # /research 3, /research:research 3
find . -name '*.jsonl' -print0 | xargs -0 grep -oh '"name":"WebSearch"' | wc -l   # 881
find . -name '*.jsonl' -print0 | xargs -0 grep -oh '"name":"WebFetch"'  | wc -l   # 729

# Executed CLI, both hosts (scratchpad parsers mine2.py / cx2.py / cx3.py)
#   Claude Code: 21 total (17 excluding this audit)
#   Codex:      325 total, 33 sessions, 44 failures (13.5%)

# Store
sqlite3 -readonly ~/dev/research/.db.sqlite3 "SELECT count(*) FROM entries;"       # 187
find ~/dev/research/topics -name '*.md' -type f | wc -l                            # 217
sqlite3 -readonly ~/dev/research/.db.sqlite3 \
  "SELECT substr(created,1,7), count(*) FROM entries GROUP BY 1;"                  # Apr 45 May 24 Jun 18 Jul 64 Aug 36

# Routing
grep -c 'research:'      ~/.claude/CLAUDE.md    # 0
grep -c 'research-plugin' ~/.claude/CLAUDE.md   # 0
grep -c 'dev/research'    ~/.claude/CLAUDE.md   # 0
md5 -q .../research-plugin/skills/research/SKILL.md   # 688bbb3548867cfd05f982f94c4603bb
md5 -q .../build-loop/skills/research/SKILL.md        # b8a7a0b22d8c63f768384e2ce2edbbe2
md5 -q ~/.claude/skills/research/SKILL.md             # b40a03dc3bf224eefdec9c55df505aed
grep -c 'research.py' ~/.zsh_history ~/.bash_history  # 0, 0
```

### 5.3 Sample paths

- Store: `~/dev/research/.db.sqlite3` (8.48 MB, mtime Aug 14 01:08), `~/dev/research/topics/`, `~/dev/research/PORTFOLIO.md`
- Dead decoys: `~/dev/research/index.db` (0 B), `~/dev/research/research.db` (0 B)
- Codex wiring: `~/.codex/config.toml:41`, `:613`; `~/.codex/plugins/cache/ross-labs-local/research/local/research.py`
- Claude Code wiring: `~/.claude/plugins/research` → dev repo; `~/.claude/settings.json:531`; caches at `~/.claude/plugins/cache/rosslabs-ai-toolkit/research/{0.5.1,e97091896725}/`
- Competing store: `build-loop-memory/projects/*/research/` (124 files); backlog item `build-loop-memory/projects/build-loop/issues/bl-research-plugin-trigger-policy.md`
- Parsers used: `mine2.py`, `mine3.py`, `mine4.py`, `cx2.py`, `cx3.py` (session scratchpad, not committed)

### 5.3b Sources added after user review (2026-08-15)

- Private work-notes tool card (2026-07-27) — work-fork status. Read-only, not in this repo; path withheld.
- Private work-notes question-design guide (2026-07-19) — decision-card + MECE section method. Read-only, path withheld.
- Private work-notes expert-call guide (2026-07-19) — five-artifact evidence chain and source-priority order. Read-only, path withheld.
- `grep -rn -i "one clear question\|sub-question" skills/` · `grep -rli "optimize\|section contract\|query ledger\|readiness" commands skills research.py tests` (no hits beyond a methodology anti-example) · `plugin.json` / `package.json` version fields.

### 5.4 What could not be verified

- ❓ **Claude Code May–June usage** — transcripts purged. Claude Code figures are lower bounds.
- ❓ **The pre-April period** for both hosts. The store's oldest entry is 2026-04-17, which is consistent with April being the true start, but transcripts cannot confirm it.
- ❓ **Why Codex usage stopped after 2026-07-31** while its plugin cache was refreshed Aug 14. Cannot distinguish a genuine lull from a search gap.
- ❓ **Whether the 5 duplicate-title pairs are true duplicates or deliberate forks** — requires human judgement, not a diff.
- ❓ **Whether the 30 unindexed entries were never synced or were deleted and recreated** — would need a per-file path diff against the DB.
- ⚠️ **Operations Center tasks** were not searched; only the MCP tool surface is visible in this session and its backing store was not located on disk within the time bound.
- ⚠️ Items marked ⚠️ above rest on subagent mining that the author did not independently re-execute: the Codex failure snippets (aggregate rate *was* re-derived), the uncommitted-diff characterization, the test-suite runs, git history, the `build-loop-memory` file counts, and the `~/.gemini` / `~/.cursor` / `~/.opencode` scans.
- ⚠️ Rally room state for this repo was read as untrusted data and contributed no usage signal beyond a July file-claim on `research.py`.
