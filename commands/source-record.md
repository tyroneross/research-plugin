---
description: Append a host-fetched or locally extracted source representation to the research audit trail.
argument-hint: "--manifest /absolute/path/source.json [--run-id ID] [--entry-slug SLUG]"
allowed-tools: Bash
---

Run `python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" source-record $ARGUMENTS`. The manifest must identify an absolute HTTP(S) or `file:` URL; use strict `sha256:<64 lowercase hex>` identities, ISO-8601 dates (capture timestamps require a timezone), and a locator. When a publication date, content hash, or locator is genuinely unavailable, supply the corresponding `*_unknown_reason` instead of a placeholder value.
