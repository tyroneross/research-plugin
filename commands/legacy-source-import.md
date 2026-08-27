---
description: Normalize historical entry source lists into the append-only source ledger without inventing missing capture provenance.
argument-hint: "[--apply]"
allowed-tools: Bash
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" legacy-source-import $ARGUMENTS`.

The default is a read-only dry run that reports planned entries and sources. Review that count before rerunning with `--apply`. The import uses stable run and observation IDs, is idempotent, and records missing historical capture date, publication date, and content hash as explicit unknowns. Those incomplete observations remain `doctor` findings until a later real capture supplies the missing evidence.
