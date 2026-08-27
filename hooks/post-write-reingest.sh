#!/usr/bin/env bash
# PostToolUse hook: if Write/Edit touched the configured content root's
# topics/*.md tree, re-ingest that entry and append bounded local telemetry.
# Never blocks the host on failure.

set -e

# Read hook payload from stdin
payload=$(cat 2>/dev/null || true)
[ -z "$payload" ] && exit 0

# Extract file path via jq if available, else python
if command -v jq >/dev/null 2>&1; then
  file_path=$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
else
  file_path=$(printf '%s' "$payload" | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin)
    print(d.get("tool_input",{}).get("file_path",""))
except: pass' 2>/dev/null || true)
fi

[ -z "$file_path" ] && exit 0

# Resolve the content root. RESEARCH_BASE_DIR is preserved as a compatibility alias.
content_root="${RESEARCH_CONTENT_DIR:-${RESEARCH_BASE_DIR:-$HOME/dev/research}}"
case "$content_root" in
  "~"/*) content_root="$HOME/${content_root#~/}" ;;
esac

# Resolve the installed plugin root. Hosted installs set one of the root
# variables; direct script execution can fall back to this file's location.
plugin_root="${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PROJECT_DIR:-}}}}"
if [ -z "$plugin_root" ]; then
  plugin_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

host_kind="unknown"
if [ -n "${CODEX_PLUGIN_ROOT:-}" ]; then
  host_kind="codex"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  host_kind="claude"
fi

index_root="${RESEARCH_INDEX_DIR:-${RESEARCH_BASE_DIR:-$HOME/dev/research}}"
case "$index_root" in
  "~"/*) index_root="$HOME/${index_root#~/}" ;;
esac

# Only fire for research entries under <content-root>/topics/**.md
case "$file_path" in
  "$content_root"/topics/*/*.md)
    hook_status=0
    python3 "$plugin_root/research.py" save --file "$file_path" --skip-symlink \
      --actor-type host-hook --actor-id post-write-reingest --host "$host_kind" \
      --tool-version "${RESEARCH_TOOL_VERSION:-unknown}" >/dev/null 2>&1 || hook_status=$?
    mkdir -p "$index_root/telemetry" 2>/dev/null || true
    python3 -c 'import json,sys,datetime
p,source,status,host=sys.argv[1:]
event={"timestamp":datetime.datetime.now().astimezone().isoformat(),"event":"post_write_reingest","source_path":source,"status":"passed" if status=="0" else "failed","exit_code":int(status),"host":host}
with open(p,"a",encoding="utf-8") as f: f.write(json.dumps(event,separators=(",",":"))+"\n")' \
      "$index_root/telemetry/hook-events.jsonl" "$file_path" "$hook_status" "$host_kind" 2>/dev/null || true
    ;;
  *)
    ;;
esac

exit 0
