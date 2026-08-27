# Research plugin usage and integrity audit — 2026-08-27

## Conclusion

The plugin is used primarily through Codex, while Claude Code still performs substantial web research outside the plugin's persistence path. The existing corpus is useful but cannot support a trustworthy longitudinal graph yet: legacy entries lack capture hashes and actor/session provenance, verifier artifacts overwrite prior verdicts, and the file corpus and SQLite index are out of parity. The candidate build adds the append-only and deterministic foundation; it does not retroactively make historical evidence complete.

## Scope and counting rules

This audit sampled and deterministically parsed local Codex and Claude Code JSONL logs, the configured research store, installed plugin caches, hook configuration, verifier artifacts, extraction cache, git history, and the prior 2026-08-15 audit. A command counted only when it appeared in an executed shell/tool-call payload. Skill rosters, prompts, source-code strings, and inspection commands were excluded.

Host-log retention changes while the audit is running. At the final corpus-size check, Codex retained 2,760 JSONL files (12 GB) and Claude Code retained 1,553 JSONL files (2.0 GB). Claude history is therefore a lower bound and should not be compared as if it were complete.

## Observed use since 2026-08-16

The strict scan performed during this audit found:

| Host | Executed plugin operations | Sessions | Mix | Important limitation |
|---|---:|---:|---|---|
| Codex | 75 | 16 | save 32, verify 28, depth 12, search 2, index 1 | 24 calls contained an error record, but one tool call can contain several commands, so this is not an exact command failure rate |
| Claude Code | about 20 | 5 | score 14, save 3, search 2, depth 1 | Most were development/integration activity; one clear research run was observed |

Sixty-eight of the 75 Codex calls used the installed `0.5.1` cache path. The cached executable and skill were byte-identical to the newer repository implementation at inspection time, so behavior was newer than the displayed package label. This is a provenance defect: runtime label and runtime bytes disagree.

Claude Code made 656 retained `WebFetch` and 547 retained `WebSearch` calls after 2026-08-16. Those 1,203 calls do not prove 1,203 research tasks, but they do show that most Claude web retrieval bypasses the plugin's source ledger and reuse index.

## Store and telemetry findings

The final read-only store snapshot contained 419 Markdown files and 214 SQLite entries. A copied-store `doctor` run identified 245 topic files but only 214 unique valid slugs represented in SQLite:

- 26 malformed or missing-slug files;
- five duplicate slugs;
- historical entry source lists with no normalized observation history;
- effectively no legacy host, model, session, or tool-version provenance.

The verifier directory contained 239 JSON artifacts at the final count. A prior bounded scan of the 49 artifacts modified since 2026-08-16 found 31 passed, 11 inconclusive, five failed, and two dry-run verdicts. The legacy verifier stores the latest artifact at an atom path, so those files are not an append-only history.

The extraction cache contained three files, all dating to April 2026. The deterministic extraction/OCR path is therefore essentially unused in actual research.

The old hook swallowed re-ingest failures and emitted no durable telemetry. The candidate hook records bounded status-only JSONL events under the external index root: timestamp, event, source path, status, exit code, and host. It does not record prompts or source contents.

## Candidate controls added

The candidate implementation adds:

- append-only, hash-chained run events with actor, host, session, and tool-version snapshots;
- immutable source observations with publication/capture dates, hashes, extraction route, locator, revision links, and explicit unknown reasons;
- topic, tag, project, corpus, and source-ledger indexes under the external research root;
- graph-ready run, entry, source, observation, claim, calculation, trust, discrepancy, and traversal records;
- strict SHA-256 identity validation and local-file hash recomputation;
- deterministic decimal calculation receipts, boolean assertions, full-receipt hashes, and doctor verification against the receipt file;
- a dry-run-first, idempotent historical source importer that preserves missing provenance as unknown;
- bounded level-2/3 traversal decision recording with fail-closed robots and destination policy;
- a host-neutral orchestration contract, immutable task packets, exactly-one-result-per-task validation, and contract-bound append-only reconciliation;
- a macOS Apple Vision OCR adapter with fast and accurate modes.

Research outputs, source captures, indexes, run packets, receipts, graph exports, and telemetry remain outside plugin git through `RESEARCH_CONTENT_DIR` and `RESEARCH_INDEX_DIR` (default `~/dev/research/`).

## Boundaries

The graph is a graph-ready foundation, not the requested full longitudinal knowledge graph. The candidate does not yet enforce person/company/article entity manifests, authorship or publisher edges, claim validity intervals, cross-run claim equivalence, or automatic correction/retraction discovery. Trust observations remain component evidence, not a composite truth score.

No live historical data was migrated during this build. Run `legacy-source-import` without `--apply` first, inspect the counts, back up the external store, and only then apply the migration. Unknown historical hashes and dates will remain doctor findings until sources are recaptured.

A full rehearsal on a copied store planned 1,557 observations across 164 entries, imported all 1,557, and imported zero on the second run. It skipped two non-URL source labels with explicit reasons. The post-import event chain passed; 1,557 observations correctly remained incomplete because historical content hashes were unavailable, and 10 entries still had no normalizable source history. These are migration coverage findings, not evidence that the underlying sources were recaptured.

## Decision

Activate the candidate only after the independent audit passes and installed caches report the same version and bytes. Then run the three-query frozen replay in the evaluation plan before making an improvement claim. Do not treat the current test suite or one OCR fixture as evidence of research-quality improvement.
