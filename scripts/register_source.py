#!/usr/bin/env python3
"""Register one captured source as a run-bound observation, and print its observation_id.

`research.py source-record` takes a JSON capture manifest. Hand-authoring that manifest
for every source is the step most runs get wrong: a missing content_hash, published_at,
or locator field fails the merge gate long after the fetch context is gone. This wraps it.

Usage:
  python3 scripts/register_source.py \
      --run-id run-abc123 \
      --url https://example.org/spec \
      --title "Example specification" \
      --tier T1 --role primary \
      --capture-file captures/T1-example.txt \
      --published-at 2026-08-31 \
      --locator "section 3.2" \
      --independence "standards body publishing its own specification"

The capture file holds the excerpt you retained. Its SHA-256 becomes the manifest's
content_hash, which is what binds a later claim to this evidence. See the capture-sizing
rule in skills/research/references/deep-research-architecture.md: retain condensed notes
with short quoted fragments, not a verbatim dump of the page.

Exit codes: 0 registered, 2 bad input or source-record failure.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
RESEARCH_PY = PLUGIN_ROOT / "research.py"

ROLES = ("primary", "independent-corroboration", "counter-evidence", "currentness")
MAX_CAPTURE_WORDS = 500


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run-id", default=os.environ.get("RESEARCH_RUN_ID"),
                   help="Run to bind this observation to; defaults to $RESEARCH_RUN_ID")
    p.add_argument("--url", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--tier", required=True, choices=["T1", "T2", "T3", "T4"])
    p.add_argument("--role", required=True, choices=ROLES)
    p.add_argument("--capture-file", required=True,
                   help="Local file holding the retained excerpt; its SHA-256 becomes content_hash")
    p.add_argument("--published-at", help="YYYY-MM-DD as stated by the source")
    p.add_argument("--published-unknown", help="Why no publication date is available")
    p.add_argument("--locator", help="Section, page, or anchor the excerpt came from")
    p.add_argument("--locator-unknown", help="Why no stable locator exists")
    p.add_argument("--independence", default="",
                   help="One line on why this source is independent of the others. "
                        "For a vendor page: 'vendor self-description, primary only for its own product'")
    p.add_argument("--parser", default="WebFetch")
    p.add_argument("--entry-slug", default="")
    p.add_argument("--task", default="src", help="Worker or task id, used to name the manifest file")
    p.add_argument("--manifest-dir", help="Where to write the manifest (default: alongside the capture file)")
    p.add_argument("--allow-long-capture", action="store_true",
                   help=f"Skip the {MAX_CAPTURE_WORDS}-word capture warning")
    a = p.parse_args()

    if not a.run_id:
        print("ERROR: --run-id is required (or set $RESEARCH_RUN_ID)", file=sys.stderr)
        return 2

    cap = pathlib.Path(a.capture_file).expanduser()
    if not cap.is_file():
        print(f"ERROR: capture file not found: {cap}", file=sys.stderr)
        return 2
    raw = cap.read_bytes()
    if not raw.strip():
        print("ERROR: capture file is empty; save the retained excerpt before registering", file=sys.stderr)
        return 2

    words = len(raw.decode("utf-8", "replace").split())
    if words > MAX_CAPTURE_WORDS and not a.allow_long_capture:
        print(
            f"WARNING: capture is {words} words. Retain condensed notes with short quoted "
            f"fragments rather than a verbatim dump; the hash covers whatever you keep. "
            f"Pass --allow-long-capture to silence.",
            file=sys.stderr,
        )

    digest = hashlib.sha256(raw).hexdigest()
    manifest = {
        "url": a.url,
        "name": a.title,
        "tier": a.tier,
        "role": a.role,
        "independence": a.independence,
        "primary": a.role == "primary",
        "content_hash": f"sha256:{digest}",
        "parser": a.parser,
        "parser_version": _plugin_version(),
        "extraction_status": "success",
        "extraction_confidence": "high",
        "provenance_granularity": "section",
        "raw_ref": str(cap),
        "parse_notes": ["Hash covers the retained relevant excerpt, not the complete remote page."],
        "captured": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "run_id": a.run_id,
    }
    if a.published_at:
        manifest["published_at"] = a.published_at
    else:
        manifest["published_at_unknown_reason"] = a.published_unknown or "page states no publication date"
    if a.locator:
        manifest["locator"] = a.locator
    else:
        manifest["locator_unknown_reason"] = a.locator_unknown or "single-page document without stable section anchors"

    mdir = pathlib.Path(a.manifest_dir).expanduser() if a.manifest_dir else cap.parent
    mdir.mkdir(parents=True, exist_ok=True)
    mpath = mdir / f"{a.task}-{digest[:12]}.manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2))

    cmd = [sys.executable, str(RESEARCH_PY), "source-record", "--manifest", str(mpath),
           "--run-id", a.run_id, "--tool-version", _plugin_version()]
    if a.entry_slug:
        cmd += ["--entry-slug", a.entry_slug]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"ERROR: source-record failed: {proc.stderr.strip()}", file=sys.stderr)
        return 2
    try:
        print(json.loads(proc.stdout)["observation_id"])
    except (json.JSONDecodeError, KeyError):
        print(proc.stdout.strip())
    return 0


def _plugin_version() -> str:
    try:
        data = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text())
        return str(data.get("version", "unknown"))
    except (OSError, json.JSONDecodeError):
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())
