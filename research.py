#!/usr/bin/env python3
"""research.py — central research knowledge base.

Subcommands (v0.1): init, save, search, list, link, index, archive
Subcommands (v0.2): score, verify
Subcommands (v0.3): review, compress
Subcommands (v0.4): table-profile, db-profile, analyze-plan, analyze-run
Subcommands (v0.5): sync, depth
Subcommands (bridges): extract (Omniparse)

Canonical markdown lives under a configurable content root (default:
~/dev/research). SQLite FTS5 and other operational state can live under a
separate configurable index root. The host agent's WebFetch/Read tools are
assumed to have already extracted source content into entry files; this
script persists, queries, scores, and verifies.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib
import ipaddress
import json
import os
import platform
import random
import re
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# ---------- Paths ----------

DEFAULT_BASE_DIR = Path.home() / "dev" / "research"
BASE_DIR = Path(os.environ.get("RESEARCH_BASE_DIR", DEFAULT_BASE_DIR)).expanduser()
CONTENT_DIR = Path(os.environ.get("RESEARCH_CONTENT_DIR", BASE_DIR)).expanduser()
INDEX_DIR = Path(os.environ.get("RESEARCH_INDEX_DIR", BASE_DIR)).expanduser()
DB_PATH = INDEX_DIR / ".db.sqlite3"
PLUGIN_ROOT = Path(__file__).resolve().parent
DATA_DIR = PLUGIN_ROOT / "data"
DEFAULT_PROJECTS_DIR = Path.home() / "dev" / "git-folder"
GIT_FOLDER = Path(os.environ.get("RESEARCH_PROJECTS_DIR", DEFAULT_PROJECTS_DIR)).expanduser()


# ---------- Schema ----------

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  path TEXT NOT NULL,
  title TEXT,
  topics TEXT,
  projects TEXT,
  tags TEXT,
  sources TEXT,
  status TEXT,
  workflow TEXT,
  created TEXT,
  reviewed TEXT,
  topic_velocity TEXT,
  confidence TEXT,
  corroboration INTEGER DEFAULT 0,
  tldr TEXT,
  notes TEXT,
  raw TEXT,
  verification TEXT,
  inbound TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
  slug, title, tldr, notes, raw,
  content='entries', content_rowid='id',
  tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
  INSERT INTO entries_fts(rowid, slug, title, tldr, notes, raw)
  VALUES (new.id, new.slug, new.title, new.tldr, new.notes, new.raw);
END;

CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, slug, title, tldr, notes, raw)
  VALUES ('delete', old.id, old.slug, old.title, old.tldr, old.notes, old.raw);
END;

CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, slug, title, tldr, notes, raw)
  VALUES ('delete', old.id, old.slug, old.title, old.tldr, old.notes, old.raw);
  INSERT INTO entries_fts(rowid, slug, title, tldr, notes, raw)
  VALUES (new.id, new.slug, new.title, new.tldr, new.notes, new.raw);
END;

CREATE TABLE IF NOT EXISTS domain_scores (
  domain TEXT PRIMARY KEY,
  tier TEXT NOT NULL,
  reason TEXT,
  set_by TEXT,
  set_date TEXT
);

CREATE TABLE IF NOT EXISTS linked_files (
  id INTEGER PRIMARY KEY,
  project TEXT NOT NULL,
  source_path TEXT UNIQUE NOT NULL,
  relpath TEXT NOT NULL,
  name TEXT NOT NULL,
  title TEXT,
  summary TEXT,
  mtime TEXT,
  size INTEGER,
  body TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS linked_files_fts USING fts5(
  project, relpath, title, summary, body,
  content='linked_files', content_rowid='id',
  tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS linked_files_ai AFTER INSERT ON linked_files BEGIN
  INSERT INTO linked_files_fts(rowid, project, relpath, title, summary, body)
  VALUES (new.id, new.project, new.relpath, new.title, new.summary, new.body);
END;

CREATE TRIGGER IF NOT EXISTS linked_files_ad AFTER DELETE ON linked_files BEGIN
  INSERT INTO linked_files_fts(linked_files_fts, rowid, project, relpath, title, summary, body)
  VALUES ('delete', old.id, old.project, old.relpath, old.title, old.summary, old.body);
END;

CREATE TRIGGER IF NOT EXISTS linked_files_au AFTER UPDATE ON linked_files BEGIN
  INSERT INTO linked_files_fts(linked_files_fts, rowid, project, relpath, title, summary, body)
  VALUES ('delete', old.id, old.project, old.relpath, old.title, old.summary, old.body);
  INSERT INTO linked_files_fts(rowid, project, relpath, title, summary, body)
  VALUES (new.id, new.project, new.relpath, new.title, new.summary, new.body);
END;

CREATE TABLE IF NOT EXISTS research_runs (
  run_id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  completed_at TEXT,
  objective TEXT,
  intent TEXT,
  outcome TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  actor_type TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  host TEXT NOT NULL,
  session_id TEXT NOT NULL,
  tool_version TEXT NOT NULL,
  contract_json TEXT NOT NULL DEFAULT '{}',
  contract_hash TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS audit_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT UNIQUE NOT NULL,
  event_type TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  run_id TEXT,
  actor_type TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  host TEXT NOT NULL DEFAULT 'unknown',
  session_id TEXT NOT NULL DEFAULT 'unknown',
  tool_version TEXT NOT NULL DEFAULT 'unknown',
  payload_json TEXT NOT NULL,
  previous_hash TEXT NOT NULL,
  event_hash TEXT UNIQUE NOT NULL,
  hash_scheme TEXT NOT NULL DEFAULT 'sha256-json-sort-keys-v2-provenance',
  FOREIGN KEY(run_id) REFERENCES research_runs(run_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS audit_events_one_successor
  ON audit_events(previous_hash);

CREATE TRIGGER IF NOT EXISTS audit_events_no_update
BEFORE UPDATE ON audit_events BEGIN
  SELECT RAISE(ABORT, 'audit_events is append-only');
END;

CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
BEFORE DELETE ON audit_events BEGIN
  SELECT RAISE(ABORT, 'audit_events is append-only');
END;

CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  canonical_url TEXT UNIQUE NOT NULL,
  domain TEXT NOT NULL,
  source_kind TEXT,
  name TEXT,
  first_seen_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS source_observations (
  observation_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  entry_slug TEXT,
  published_at TEXT,
  modified_at TEXT,
  captured_at TEXT NOT NULL,
  final_url TEXT,
  content_hash TEXT,
  normalized_hash TEXT,
  capture_method TEXT NOT NULL,
  extractor TEXT,
  extractor_version TEXT,
  locator TEXT,
  raw_ref TEXT,
  status TEXT NOT NULL,
  change_from_observation_id TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY(source_id) REFERENCES sources(source_id),
  FOREIGN KEY(run_id) REFERENCES research_runs(run_id),
  FOREIGN KEY(change_from_observation_id) REFERENCES source_observations(observation_id)
);

CREATE INDEX IF NOT EXISTS source_observations_source_time
  ON source_observations(source_id, captured_at);
CREATE INDEX IF NOT EXISTS source_observations_run
  ON source_observations(run_id);

CREATE TRIGGER IF NOT EXISTS source_observations_no_update
BEFORE UPDATE ON source_observations BEGIN
  SELECT RAISE(ABORT, 'source_observations is append-only');
END;

CREATE TRIGGER IF NOT EXISTS source_observations_no_delete
BEFORE DELETE ON source_observations BEGIN
  SELECT RAISE(ABORT, 'source_observations is append-only');
END;

CREATE TABLE IF NOT EXISTS graph_entities (
  entity_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  canonical_key TEXT NOT NULL,
  label TEXT,
  created_at TEXT NOT NULL,
  retired_at TEXT,
  properties_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(kind, canonical_key)
);

CREATE TABLE IF NOT EXISTS graph_edges (
  edge_id TEXT PRIMARY KEY,
  subject_id TEXT NOT NULL,
  predicate TEXT NOT NULL,
  object_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  valid_from TEXT,
  valid_to TEXT,
  evidence_observation_id TEXT,
  locator TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  confidence TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY(subject_id) REFERENCES graph_entities(entity_id),
  FOREIGN KEY(object_id) REFERENCES graph_entities(entity_id),
  FOREIGN KEY(run_id) REFERENCES research_runs(run_id),
  FOREIGN KEY(evidence_observation_id) REFERENCES source_observations(observation_id)
);

CREATE INDEX IF NOT EXISTS graph_edges_subject ON graph_edges(subject_id, predicate);
CREATE INDEX IF NOT EXISTS graph_edges_object ON graph_edges(object_id, predicate);

CREATE TRIGGER IF NOT EXISTS graph_edges_no_update
BEFORE UPDATE ON graph_edges BEGIN
  SELECT RAISE(ABORT, 'graph_edges is append-only');
END;

CREATE TRIGGER IF NOT EXISTS graph_edges_no_delete
BEFORE DELETE ON graph_edges BEGIN
  SELECT RAISE(ABORT, 'graph_edges is append-only');
END;

CREATE TABLE IF NOT EXISTS trust_observations (
  trust_observation_id TEXT PRIMARY KEY,
  subject_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  topic_key TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  dimension TEXT NOT NULL,
  rating TEXT NOT NULL,
  rationale TEXT NOT NULL,
  evidence_observation_id TEXT,
  formula_version TEXT NOT NULL,
  FOREIGN KEY(subject_id) REFERENCES graph_entities(entity_id),
  FOREIGN KEY(run_id) REFERENCES research_runs(run_id),
  FOREIGN KEY(evidence_observation_id) REFERENCES source_observations(observation_id)
);

CREATE INDEX IF NOT EXISTS trust_observations_subject_topic_time
  ON trust_observations(subject_id, topic_key, observed_at);

CREATE TRIGGER IF NOT EXISTS trust_observations_no_update
BEFORE UPDATE ON trust_observations BEGIN
  SELECT RAISE(ABORT, 'trust_observations is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trust_observations_no_delete
BEFORE DELETE ON trust_observations BEGIN
  SELECT RAISE(ABORT, 'trust_observations is append-only');
END;

CREATE TABLE IF NOT EXISTS discrepancies (
  discrepancy_id TEXT PRIMARY KEY,
  left_claim_id TEXT NOT NULL,
  right_claim_id TEXT NOT NULL,
  discrepancy_type TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  status TEXT NOT NULL,
  resolution_claim_id TEXT,
  run_id TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY(run_id) REFERENCES research_runs(run_id)
);

CREATE TRIGGER IF NOT EXISTS discrepancies_no_update
BEFORE UPDATE ON discrepancies BEGIN
  SELECT RAISE(ABORT, 'discrepancies is append-only');
END;

CREATE TRIGGER IF NOT EXISTS discrepancies_no_delete
BEFORE DELETE ON discrepancies BEGIN
  SELECT RAISE(ABORT, 'discrepancies is append-only');
END;

CREATE TABLE IF NOT EXISTS traversal_links (
  traversal_link_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  parent_observation_id TEXT,
  discovered_at TEXT NOT NULL,
  discovery_order INTEGER NOT NULL,
  depth INTEGER NOT NULL,
  displayed_url TEXT NOT NULL,
  resolved_url TEXT,
  canonical_url TEXT,
  decision TEXT NOT NULL,
  reason TEXT NOT NULL,
  evidence_gap TEXT,
  child_observation_id TEXT,
  bytes INTEGER,
  elapsed_ms INTEGER,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY(run_id) REFERENCES research_runs(run_id),
  FOREIGN KEY(parent_observation_id) REFERENCES source_observations(observation_id),
  FOREIGN KEY(child_observation_id) REFERENCES source_observations(observation_id)
);

CREATE INDEX IF NOT EXISTS traversal_links_run_order
  ON traversal_links(run_id, depth, discovery_order);

CREATE TRIGGER IF NOT EXISTS traversal_links_no_update
BEFORE UPDATE ON traversal_links BEGIN
  SELECT RAISE(ABORT, 'traversal_links is append-only');
END;

CREATE TRIGGER IF NOT EXISTS traversal_links_no_delete
BEFORE DELETE ON traversal_links BEGIN
  SELECT RAISE(ABORT, 'traversal_links is append-only');
END;

CREATE TABLE IF NOT EXISTS calculation_receipts (
  receipt_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  claim_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  correction_of_receipt_id TEXT,
  status TEXT NOT NULL,
  formula TEXT NOT NULL,
  formula_hash TEXT NOT NULL,
  unit TEXT NOT NULL,
  denominator TEXT NOT NULL,
  grain TEXT NOT NULL,
  assumptions_json TEXT NOT NULL,
  inputs_json TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  code_hash TEXT NOT NULL,
  command_json TEXT NOT NULL,
  runtime_ms INTEGER NOT NULL,
  result_text TEXT,
  output_hash TEXT NOT NULL,
  checks_json TEXT NOT NULL,
  environment_json TEXT NOT NULL,
  receipt_hash TEXT NOT NULL DEFAULT '',
  receipt_path TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES research_runs(run_id),
  FOREIGN KEY(correction_of_receipt_id) REFERENCES calculation_receipts(receipt_id)
);

CREATE TRIGGER IF NOT EXISTS calculation_receipts_no_update
BEFORE UPDATE ON calculation_receipts BEGIN
  SELECT RAISE(ABORT, 'calculation_receipts is append-only');
END;

CREATE TRIGGER IF NOT EXISTS calculation_receipts_no_delete
BEFORE DELETE ON calculation_receipts BEGIN
  SELECT RAISE(ABORT, 'calculation_receipts is append-only');
END;
"""


# ---------- Utilities ----------

def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def content_path(*parts: str) -> Path:
    return CONTENT_DIR.joinpath(*parts)


def index_path(*parts: str) -> Path:
    return INDEX_DIR.joinpath(*parts)


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def _stringify_dates(obj: Any) -> Any:
    """Recursively convert date/datetime objects to ISO strings for JSON serialization."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _stringify_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_dates(v) for v in obj]
    return obj


def parse_frontmatter(text: str, *, fatal: bool = True) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm_text, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        if not fatal:
            raise ValueError(f"invalid frontmatter YAML: {e}") from e
        print(f"ERROR parsing frontmatter: {e}", file=sys.stderr)
        sys.exit(2)
    return _stringify_dates(fm), body


def dump_frontmatter(fm: dict, body: str) -> str:
    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return f"---\n{fm_text}---\n{body}"


SECTION_RE = re.compile(r"^##\s+(TL;DR|Notes|Raw)\s*$", re.MULTILINE)


def split_sections(body: str) -> dict[str, str]:
    """Return {'tldr': str, 'notes': str, 'raw': str}. Missing sections -> ''."""
    parts = SECTION_RE.split(body)
    out = {"tldr": "", "notes": "", "raw": ""}
    i = 1
    while i < len(parts) - 1:
        header = parts[i]
        content = parts[i + 1].strip()
        key = {"TL;DR": "tldr", "Notes": "notes", "Raw": "raw"}[header]
        out[key] = content
        i += 2
    return out


def detect_project(cwd: Path | None = None) -> str | None:
    """If cwd is under $RESEARCH_PROJECTS_DIR/<name>/, return <name>."""
    cwd = cwd or Path.cwd()
    try:
        rel = cwd.resolve().relative_to(GIT_FOLDER.resolve())
    except ValueError:
        return None
    parts = rel.parts
    return parts[0] if parts else None


def top_level_topic(slug: str) -> str:
    return slug.split(".", 1)[0]


ETLD1_SPECIAL = {
    # Hosts where eTLD+1 alone isn't enough; keep full for scoring.
    "github.io",
    "readthedocs.io",
    "substack.com",
    "medium.com",
}


def etld1(url: str) -> str:
    try:
        host = urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""
    if not host:
        return ""
    # Strip port
    host = host.split(":", 1)[0]
    # Simple eTLD+1: last two labels (won't be perfect for all country TLDs but good enough)
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    # Heuristic for common two-part TLDs
    two_part_tlds = {"co.uk", "ac.uk", "gov.uk", "co.jp", "com.au", "co.nz"}
    last2 = ".".join(parts[-2:])
    last3 = ".".join(parts[-3:])
    if last2 in two_part_tlds:
        return last3
    return last2


def today_iso() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def ensure_layout() -> None:
    """Create the configured content and index roots if missing. Idempotent."""
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ("topics", "indices", "archive", "archive/raw", "inbox", "projects"):
        content_path(sub).mkdir(parents=True, exist_ok=True)
    for sub in ("verifier-log",):
        index_path(sub).mkdir(parents=True, exist_ok=True)
    readme = content_path("README.md")
    if not readme.exists():
        readme.write_text(
            "# Research Content Root\n\n"
            "Canonical research markdown lives in this directory. Managed by the `research` plugin.\n\n"
            "- `topics/<top>/<slug>.md` — canonical entries\n"
            "- `indices/` — auto-generated Maps of Content per topic\n"
            "- `archive/` — never-deleted moved entries (redirect stubs remain in `topics/`)\n"
            f"- SQLite index root: `{INDEX_DIR}`\n"
            f"- SQLite DB: `{DB_PATH}`\n\n"
            "Subcommands: run `python <plugin>/research.py --help`.\n"
            "Or use slash commands: `/research:search`, `/research:list`, `/research:review`, etc.\n\n"
            "## Searching\n\n"
            "```bash\n"
            "# Ranked full-text\n"
            "python <plugin>/research.py search 'chain of thought'\n\n"
            "# Or just grep\n"
            "grep -r 'chain of thought' topics/\n"
            "```\n"
        )


def ensure_db() -> None:
    conn = db_connect()
    with conn:
        conn.executescript(SCHEMA)
        run_columns = {row["name"] for row in conn.execute("PRAGMA table_info(research_runs)")}
        if "contract_hash" not in run_columns:
            conn.execute("ALTER TABLE research_runs ADD COLUMN contract_hash TEXT NOT NULL DEFAULT ''")
        event_columns = {row["name"] for row in conn.execute("PRAGMA table_info(audit_events)")}
        for column in ("host", "session_id", "tool_version"):
            if column not in event_columns:
                conn.execute(f"ALTER TABLE audit_events ADD COLUMN {column} TEXT NOT NULL DEFAULT 'unknown'")
        receipt_columns = {row["name"] for row in conn.execute("PRAGMA table_info(calculation_receipts)")}
        if "receipt_hash" not in receipt_columns:
            conn.execute("ALTER TABLE calculation_receipts ADD COLUMN receipt_hash TEXT NOT NULL DEFAULT ''")
    conn.close()


def _canonical_json(value: Any) -> str:
    """Stable local serialization for hashes; this is not RFC 8785 JCS."""
    return json.dumps(_stringify_dates(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


SHA256_REF_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _validate_hash_ref(value: Any, field: str) -> str:
    text = str(value or "")
    if text and not SHA256_REF_RE.fullmatch(text):
        raise ValueError(f"{field} must use sha256:<64 lowercase hex>")
    return text


def _validate_iso_date(value: Any, field: str, *, timezone_required: bool = False) -> str:
    text = str(value or "")
    if not text:
        return text
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"{field} must be ISO-8601") from exc
        if timezone_required:
            raise ValueError(f"{field} must include a timezone")
        return text
    if timezone_required and parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return text


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _contract_hash(contract: dict[str, Any]) -> str:
    payload = {key: value for key, value in contract.items() if key != "created_at"}
    return "sha256:" + _sha256_text(_canonical_json(payload))


def _actor_from_args(args: argparse.Namespace) -> dict[str, str]:
    return {
        "actor_type": str(getattr(args, "actor_type", None) or os.environ.get("RESEARCH_ACTOR_TYPE") or "unknown"),
        "actor_id": str(getattr(args, "actor_id", None) or os.environ.get("RESEARCH_ACTOR_ID") or "unknown"),
        "host": str(getattr(args, "host", None) or os.environ.get("RESEARCH_HOST") or "unknown"),
        "session_id": str(getattr(args, "session_id", None) or os.environ.get("RESEARCH_SESSION_ID") or "unknown"),
        "tool_version": str(getattr(args, "tool_version", None) or os.environ.get("RESEARCH_TOOL_VERSION") or "unknown"),
    }


def _ensure_run(
    conn: sqlite3.Connection,
    run_id: str,
    actor: dict[str, str],
    *,
    objective: str = "",
    intent: str = "",
    outcome: str = "",
    contract: dict[str, Any] | None = None,
) -> None:
    contract_payload = contract or {}
    contract_json = _canonical_json(contract_payload)
    contract_hash = _contract_hash(contract_payload) if contract_payload else ""
    existing = conn.execute("SELECT * FROM research_runs WHERE run_id=?", (run_id,)).fetchone()
    if existing:
        if contract_hash and existing["contract_hash"] and existing["contract_hash"] != contract_hash:
            raise ValueError(f"run contract differs from initialized contract for {run_id}")
        enriched = {
            field: actor[field]
            for field in ("actor_type", "actor_id", "host", "session_id", "tool_version")
            if str(existing[field] or "unknown") == "unknown" and str(actor[field] or "unknown") != "unknown"
        }
        conn.execute(
            """
            UPDATE research_runs SET
              objective=CASE WHEN objective='' THEN ? ELSE objective END,
              intent=CASE WHEN intent='' THEN ? ELSE intent END,
              outcome=CASE WHEN outcome='' THEN ? ELSE outcome END,
              actor_type=CASE WHEN actor_type='unknown' THEN ? ELSE actor_type END,
              actor_id=CASE WHEN actor_id='unknown' THEN ? ELSE actor_id END,
              host=CASE WHEN host='unknown' THEN ? ELSE host END,
              session_id=CASE WHEN session_id='unknown' THEN ? ELSE session_id END,
              tool_version=CASE WHEN tool_version='unknown' THEN ? ELSE tool_version END,
              contract_json=CASE WHEN contract_hash='' AND ?!='' THEN ? ELSE contract_json END,
              contract_hash=CASE WHEN contract_hash='' AND ?!='' THEN ? ELSE contract_hash END
            WHERE run_id=?
            """,
            (
                objective, intent, outcome,
                actor["actor_type"], actor["actor_id"], actor["host"], actor["session_id"], actor["tool_version"],
                contract_hash, contract_json, contract_hash, contract_hash, run_id,
            ),
        )
        if enriched:
            _append_event(
                conn,
                event_type="run.provenance_enriched",
                run_id=run_id,
                actor_type=actor["actor_type"],
                actor_id=actor["actor_id"],
                payload={"enriched_fields": enriched},
                actor_snapshot=actor,
            )
        return
    conn.execute(
        """
        INSERT OR IGNORE INTO research_runs
          (run_id, started_at, objective, intent, outcome, status, actor_type,
           actor_id, host, session_id, tool_version, contract_json, contract_hash)
        VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            now_iso(),
            objective,
            intent,
            outcome,
            actor["actor_type"],
            actor["actor_id"],
            actor["host"],
            actor["session_id"],
            actor["tool_version"],
            contract_json,
            contract_hash,
        ),
    )
    _append_event(
        conn,
        event_type="run.created",
        run_id=run_id,
        actor_type=actor["actor_type"],
        actor_id=actor["actor_id"],
        payload={"objective": objective, "intent": intent, "outcome": outcome, "contract_hash": contract_hash},
        actor_snapshot=actor,
    )


def _append_event(
    conn: sqlite3.Connection,
    *,
    event_type: str,
    run_id: str | None,
    actor_type: str,
    actor_id: str,
    payload: dict[str, Any],
    actor_snapshot: dict[str, str] | None = None,
) -> dict[str, Any]:
    previous = conn.execute("SELECT event_hash FROM audit_events ORDER BY seq DESC LIMIT 1").fetchone()
    previous_hash = previous["event_hash"] if previous else "GENESIS"
    run_actor = conn.execute(
        "SELECT host, session_id, tool_version FROM research_runs WHERE run_id=?", (run_id,)
    ).fetchone() if run_id else None
    snapshot = actor_snapshot or {}
    event = {
        "event_id": _new_id("evt"),
        "event_type": event_type,
        "occurred_at": now_iso(),
        "run_id": run_id,
        "actor_type": str(snapshot.get("actor_type") or actor_type),
        "actor_id": str(snapshot.get("actor_id") or actor_id),
        "host": str(snapshot.get("host") or (run_actor["host"] if run_actor else "unknown")),
        "session_id": str(snapshot.get("session_id") or (run_actor["session_id"] if run_actor else "unknown")),
        "tool_version": str(snapshot.get("tool_version") or (run_actor["tool_version"] if run_actor else "unknown")),
        "payload": _stringify_dates(payload),
        "previous_hash": previous_hash,
        "hash_scheme": "sha256-json-sort-keys-v2-provenance",
    }
    event_hash = _sha256_text(_canonical_json(event))
    conn.execute(
        """
        INSERT INTO audit_events
          (event_id, event_type, occurred_at, run_id, actor_type, actor_id,
           host, session_id, tool_version, payload_json, previous_hash, event_hash, hash_scheme)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["event_id"],
            event_type,
            event["occurred_at"],
            run_id,
            event["actor_type"],
            event["actor_id"],
            event["host"],
            event["session_id"],
            event["tool_version"],
            _canonical_json(event["payload"]),
            previous_hash,
            event_hash,
            event["hash_scheme"],
        ),
    )
    event["event_hash"] = event_hash
    return event


def _verify_event_chain(conn: sqlite3.Connection) -> tuple[bool, list[dict[str, Any]]]:
    previous_hash = "GENESIS"
    errors: list[dict[str, Any]] = []
    for row in conn.execute("SELECT * FROM audit_events ORDER BY seq"):
        payload = json.loads(row["payload_json"])
        event = {
            "event_id": row["event_id"],
            "event_type": row["event_type"],
            "occurred_at": row["occurred_at"],
            "run_id": row["run_id"],
            "actor_type": row["actor_type"],
            "actor_id": row["actor_id"],
            "payload": payload,
            "previous_hash": row["previous_hash"],
            "hash_scheme": row["hash_scheme"],
        }
        if row["hash_scheme"] == "sha256-json-sort-keys-v2-provenance":
            event.update({
                "host": row["host"],
                "session_id": row["session_id"],
                "tool_version": row["tool_version"],
            })
        expected = _sha256_text(_canonical_json(event))
        if row["previous_hash"] != previous_hash or row["event_hash"] != expected:
            errors.append({"seq": row["seq"], "event_id": row["event_id"], "reason": "chain_or_hash_mismatch"})
        previous_hash = row["event_hash"]
    return not errors, errors


def _canonical_source_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme.lower() == "file":
        local_path = Path(urllib.parse.unquote(parsed.path)).expanduser()
        if not local_path.is_absolute():
            raise ValueError(f"file source must use an absolute path: {value}")
        return local_path.resolve().as_uri()
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"source URL must be absolute HTTP(S) or file: {value}")
    host = parsed.hostname.lower() if parsed.hostname else ""
    port = parsed.port
    netloc = host
    if port and not ((parsed.scheme.lower() == "http" and port == 80) or (parsed.scheme.lower() == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = parsed.path or "/"
    return urllib.parse.urlunsplit((parsed.scheme.lower(), netloc, path, parsed.query, ""))


def _record_sources_for_entry(
    conn: sqlite3.Connection,
    *,
    sources: list[Any],
    run_id: str,
    entry_slug: str,
) -> list[str]:
    observation_ids: list[str] = []
    for item in sources:
        source = {"url": item} if isinstance(item, str) else dict(item or {})
        url = source.get("url") or source.get("source_url")
        if not url:
            continue
        try:
            canonical_url = _canonical_source_url(str(url))
        except ValueError:
            continue
        source_id = "src-" + _sha256_text(canonical_url)[:32]
        captured_at = str(source.get("captured_at") or source.get("captured") or now_iso())
        content_hash = _validate_hash_ref(source.get("content_hash"), "content_hash")
        normalized_hash = _validate_hash_ref(source.get("normalized_hash"), "normalized_hash")
        if canonical_url.startswith("file:") and content_hash:
            local_path = Path(urllib.parse.unquote(urllib.parse.urlsplit(canonical_url).path))
            if local_path.is_file():
                actual_hash = "sha256:" + _file_sha256(local_path)
                if actual_hash != content_hash:
                    raise ValueError(f"content_hash does not match local file: {local_path}")
        published_at = source.get("published_at") or source.get("published")
        if captured_at == "0001-01-01T00:00:00Z":
            if not source.get("legacy_import") or not source.get("captured_at_unknown_reason"):
                raise ValueError("unknown captured_at requires legacy_import and captured_at_unknown_reason")
        else:
            _validate_iso_date(captured_at, "captured_at", timezone_required=True)
        if published_at:
            _validate_iso_date(published_at, "published_at")
        if source.get("modified_at") or source.get("modified"):
            _validate_iso_date(source.get("modified_at") or source.get("modified"), "modified_at")
        if not content_hash:
            source.setdefault("content_hash_unknown_reason", "not provided by entry source metadata")
        if not published_at:
            source.setdefault("published_at_unknown_reason", "not provided by entry source metadata")
        observation_status = str(
            source.get("status")
            or ("captured" if content_hash and (published_at or source.get("published_at_unknown_reason")) else "incomplete")
        )
        observation_key = _canonical_json({
            "source_id": source_id,
            "run_id": run_id,
            "entry_slug": entry_slug,
            "captured_at": captured_at,
            "content_hash": content_hash,
        })
        observation_id = "obs-" + _sha256_text(observation_key)[:32]
        prior = conn.execute(
            """SELECT observation_id, content_hash FROM source_observations
               WHERE source_id=?
               ORDER BY CASE WHEN captured_at='0001-01-01T00:00:00Z' THEN 0 ELSE 1 END DESC,
                        captured_at DESC LIMIT 1""",
            (source_id,),
        ).fetchone()
        conn.execute(
            """
            INSERT OR IGNORE INTO sources
              (source_id, canonical_url, domain, source_kind, name, first_seen_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                canonical_url,
                etld1(canonical_url) or str(source.get("domain") or "local-file"),
                str(source.get("kind") or source.get("type") or "web"),
                str(source.get("name") or source.get("title") or ""),
                captured_at,
                _canonical_json({k: v for k, v in source.items() if k not in {"url", "source_url"}}),
            ),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO source_observations
              (observation_id, source_id, run_id, entry_slug, published_at,
               modified_at, captured_at, final_url, content_hash, normalized_hash,
               capture_method, extractor, extractor_version, locator, raw_ref,
               status, change_from_observation_id, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation_id,
                source_id,
                run_id,
                entry_slug,
                published_at,
                source.get("modified_at") or source.get("modified"),
                captured_at,
                source.get("final_url") or canonical_url,
                content_hash,
                normalized_hash,
                str(source.get("capture_method") or source.get("method") or "host-tool"),
                source.get("extractor") or source.get("parser"),
                source.get("extractor_version") or source.get("parser_version"),
                source.get("locator"),
                source.get("raw_ref"),
                observation_status,
                prior["observation_id"] if prior and prior["content_hash"] != content_hash else None,
                _canonical_json(source),
            ),
        )
        observation_ids.append(observation_id)
    return observation_ids


def _graph_entity(
    conn: sqlite3.Connection,
    *,
    kind: str,
    canonical_key: str,
    label: str = "",
    properties: dict[str, Any] | None = None,
) -> str:
    entity_id = "ent-" + _sha256_text(f"{kind}:{canonical_key}")[:32]
    conn.execute(
        """
        INSERT OR IGNORE INTO graph_entities
          (entity_id, kind, canonical_key, label, created_at, properties_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (entity_id, kind, canonical_key, label, now_iso(), _canonical_json(properties or {})),
    )
    return entity_id


def _graph_edge(
    conn: sqlite3.Connection,
    *,
    subject_id: str,
    predicate: str,
    object_id: str,
    run_id: str,
    evidence_observation_id: str | None = None,
    locator: str | None = None,
    status: str = "active",
    confidence: str | None = None,
) -> str:
    key = _canonical_json({
        "subject": subject_id,
        "predicate": predicate,
        "object": object_id,
        "run_id": run_id,
        "evidence": evidence_observation_id,
        "locator": locator,
    })
    edge_id = "edge-" + _sha256_text(key)[:32]
    conn.execute(
        """
        INSERT OR IGNORE INTO graph_edges
          (edge_id, subject_id, predicate, object_id, run_id, observed_at,
           evidence_observation_id, locator, status, confidence, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}')
        """,
        (edge_id, subject_id, predicate, object_id, run_id, now_iso(), evidence_observation_id, locator, status, confidence),
    )
    return edge_id


def _record_entry_graph(
    conn: sqlite3.Connection,
    *,
    slug: str,
    title: str,
    run_id: str,
    observation_ids: list[str],
) -> None:
    run_entity = _graph_entity(conn, kind="run", canonical_key=run_id, label=run_id)
    entry_entity = _graph_entity(conn, kind="entry", canonical_key=slug, label=title or slug)
    _graph_edge(conn, subject_id=entry_entity, predicate="wasGeneratedBy", object_id=run_entity, run_id=run_id)
    for observation_id in observation_ids:
        row = conn.execute(
            """
            SELECT o.source_id, o.locator, o.change_from_observation_id, s.canonical_url, s.name
            FROM source_observations o JOIN sources s ON s.source_id=o.source_id
            WHERE o.observation_id=?
            """,
            (observation_id,),
        ).fetchone()
        if not row:
            continue
        source_entity = _graph_entity(
            conn, kind="source", canonical_key=row["canonical_url"], label=row["name"] or row["canonical_url"]
        )
        observation_entity = _graph_entity(conn, kind="observation", canonical_key=observation_id, label=observation_id)
        _graph_edge(conn, subject_id=observation_entity, predicate="wasDerivedFrom", object_id=source_entity, run_id=run_id, evidence_observation_id=observation_id, locator=row["locator"])
        _graph_edge(conn, subject_id=entry_entity, predicate="hadPrimarySource", object_id=observation_entity, run_id=run_id, evidence_observation_id=observation_id, locator=row["locator"])
        _graph_edge(conn, subject_id=run_entity, predicate="used", object_id=observation_entity, run_id=run_id, evidence_observation_id=observation_id)
        if row["change_from_observation_id"]:
            prior_entity = _graph_entity(
                conn,
                kind="observation",
                canonical_key=row["change_from_observation_id"],
                label=row["change_from_observation_id"],
            )
            _graph_edge(
                conn,
                subject_id=observation_entity,
                predicate="wasRevisionOf",
                object_id=prior_entity,
                run_id=run_id,
                evidence_observation_id=observation_id,
                locator=row["locator"],
            )


def seed_domain_scores(refresh: bool = False) -> int:
    """Populate domain_scores from data/domain-scores-seed.json and iffy-domains.csv.

    Returns number of new/updated rows. Manual overrides (set_by='manual') are
    preserved even on refresh.
    """
    conn = db_connect()
    count = 0
    seed_json = DATA_DIR / "domain-scores-seed.json"
    if seed_json.exists():
        data = json.loads(seed_json.read_text())
        for dom, entry in data.items():
            row = conn.execute(
                "SELECT set_by FROM domain_scores WHERE domain = ?", (dom,)
            ).fetchone()
            if row and row["set_by"] == "manual" and not refresh:
                continue
            if row and row["set_by"] == "manual" and refresh:
                continue  # never clobber manual
            conn.execute(
                "INSERT OR REPLACE INTO domain_scores(domain, tier, reason, set_by, set_date) "
                "VALUES (?, ?, ?, ?, ?)",
                (dom, entry["tier"], entry.get("reason", ""), "seed", today_iso()),
            )
            count += 1
    iffy_csv = DATA_DIR / "iffy-domains.csv"
    if iffy_csv.exists():
        with iffy_csv.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                dom = (row.get("domain") or "").strip().lower()
                if not dom:
                    continue
                existing = conn.execute(
                    "SELECT set_by FROM domain_scores WHERE domain = ?", (dom,)
                ).fetchone()
                if existing and existing["set_by"] in ("manual", "llm"):
                    continue
                conn.execute(
                    "INSERT OR REPLACE INTO domain_scores(domain, tier, reason, set_by, set_date) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (dom, "T4", f"iffy index: {row.get('reason', 'low credibility')}", "seed", today_iso()),
                )
                count += 1
    conn.commit()
    conn.close()
    return count


# ---------- init ----------

def cmd_init(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    added = seed_domain_scores(refresh=args.refresh_seeds)
    print(f"Initialized research content at {CONTENT_DIR}")
    print(f"Index root: {INDEX_DIR}")
    print(f"DB: {DB_PATH}")
    print(f"Seeded/refreshed {added} domain scores")
    return 0


# ---------- save ----------

def _slug_to_path(slug: str) -> Path:
    return content_path("topics", top_level_topic(slug), f"{slug}.md")


def _resolve_collision(slug: str, fm: dict) -> str:
    """If an entry with this slug exists with a different created date, bump -v2."""
    conn = db_connect()
    existing = conn.execute(
        "SELECT created FROM entries WHERE slug = ?", (slug,)
    ).fetchone()
    conn.close()
    if not existing:
        return slug
    if existing["created"] == fm.get("created"):
        return slug  # same entry, update
    # Collision: find next -vN
    base = re.sub(r"-v\d+$", "", slug)
    n = 2
    while True:
        candidate = f"{base}-v{n}"
        conn = db_connect()
        row = conn.execute(
            "SELECT 1 FROM entries WHERE slug = ?", (candidate,)
        ).fetchone()
        conn.close()
        if not row:
            return candidate
        n += 1


def _summary_from_tldr(tldr: str, limit: int = 120) -> str:
    """Extract a single-line summary from a TL;DR section. First sentence or `limit` chars."""
    if not tldr:
        return ""
    text = " ".join(tldr.strip().split())
    # First sentence
    m = re.search(r"^(.+?[.!?])(?:\s|$)", text)
    if m:
        sent = m.group(1).strip()
        if len(sent) <= limit:
            return sent
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "\u2026"


def _managed_projects_dir() -> Path:
    """Return the content-root projects dir for plugin-managed symlinks."""
    return content_path("projects")


def _linked_projects_registry_path() -> Path:
    """Return the index-root linked-project registry path."""
    return index_path(".linked-projects.json")


def _read_linked_projects_registry() -> dict:
    """Load the linked-projects registry as a dict. Returns {} if absent or malformed."""
    p = _linked_projects_registry_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _write_linked_projects_registry(registry: dict) -> None:
    """Write the registry deterministically (sorted keys, stable output)."""
    p = _linked_projects_registry_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n")


_V030_ARTIFACT_NOTE_SHOWN: set[str] = set()


def _note_v030_artifacts(project_path: Path) -> None:
    """Print a one-time informational note if v0.3.0 artifacts are present in a project.

    v0.3.1 does not maintain these, but also does not delete them.
    """
    name = project_path.name
    if name in _V030_ARTIFACT_NOTE_SHOWN:
        return
    artifacts = []
    legacy_research_dir = project_path / "research"
    legacy_live = legacy_research_dir / ".live"
    legacy_index = project_path / "RossLabs-Research.md"
    if legacy_live.exists() and legacy_live.is_dir():
        artifacts.append(f"{legacy_live} (v0.3.0 live symlinks)")
    if legacy_research_dir.exists() and legacy_research_dir.is_dir():
        # Only flag if it looks plugin-authored (has topic subdirs matching slug tops)
        has_topic_child = any(
            (legacy_research_dir / c.name).is_dir() and c.name != ".live"
            for c in legacy_research_dir.iterdir()
        ) if legacy_research_dir.exists() else False
        if has_topic_child:
            artifacts.append(f"{legacy_research_dir} (v0.3.0 file copies)")
    if legacy_index.exists():
        artifacts.append(f"{legacy_index} (v0.3.0 project index)")
    if artifacts:
        print(
            f"Note: {name}/ contains v0.3.0 artifacts that v0.3.1 no longer maintains:",
            file=sys.stderr,
        )
        for a in artifacts:
            print(f"  - {a}", file=sys.stderr)
        print(
            "  These are preserved as-is. Remove manually if unwanted.",
            file=sys.stderr,
        )
    _V030_ARTIFACT_NOTE_SHOWN.add(name)


def _managed_symlink_path(project_name: str, canonical: Path) -> Path:
    """Return <content-root>/projects/<project_name>/<slug>.md — the central symlink target."""
    return _managed_projects_dir() / project_name / canonical.name


def _write_managed_symlink(project_name: str, canonical: Path) -> Path:
    """Create or refresh a symlink at <content-root>/projects/<name>/<slug>.md -> canonical.

    Idempotent. Returns the symlink path.
    """
    link = _managed_symlink_path(project_name, canonical)
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() or link.is_symlink():
        try:
            link.unlink()
        except OSError:
            pass
    try:
        link.symlink_to(canonical)
    except OSError as e:
        print(f"WARN: could not create symlink {link}: {e}", file=sys.stderr)
    return link


def _extract_title_and_summary(path: Path) -> tuple[str, str]:
    """Extract (title, 1-line-summary) from a markdown file deterministically.

    Title: first '# H1' line text. Fallback to filename stem if no H1.
    Summary: first non-empty, non-heading paragraph, first sentence, truncated ~120 chars.
    Zero LLM calls. Frontmatter (if present) is skipped.
    """
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return path.stem, ""

    # Strip YAML frontmatter if present
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            body = text[end + 5 :]
        else:
            end = text.find("\n---", 4)
            if end != -1:
                body = text[end + 4 :]

    lines = body.splitlines()
    title: str | None = None
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            break
    if not title:
        title = path.stem.replace("-", " ").replace("_", " ").strip() or path.name

    # First paragraph: collect consecutive non-empty, non-heading lines after any H1
    summary_lines: list[str] = []
    in_paragraph = False
    seen_h1 = False
    hr_pat = re.compile(r"^([-*_])\1{2,}$")
    for ln in lines:
        stripped = ln.strip()
        is_heading = stripped.startswith("#")
        is_hr = bool(hr_pat.match(stripped))
        if is_heading or is_hr:
            if not seen_h1 and stripped.startswith("# "):
                seen_h1 = True
                continue
            if in_paragraph:
                break
            # Skip subsequent headings / horizontal rules until content starts
            continue
        if not stripped:
            if in_paragraph:
                break
            continue
        # Skip list markers, block quotes, table rows, code fences
        if stripped.startswith(("```", "|", "- ", "* ", "> ")) and not summary_lines:
            continue
        summary_lines.append(stripped)
        in_paragraph = True

    summary = " ".join(summary_lines)
    # First sentence, naive: cut at first ". " followed by capital or end
    m = re.search(r"([^.!?]+[.!?])(?:\s|$)", summary)
    if m:
        summary = m.group(1).strip()
    summary = re.sub(r"\s+", " ", summary).strip()
    # Strip simple markdown emphasis
    summary = re.sub(r"\*\*([^*]+)\*\*", r"\1", summary)
    summary = re.sub(r"\*([^*]+)\*", r"\1", summary)
    summary = re.sub(r"`([^`]+)`", r"\1", summary)
    if len(summary) > 120:
        summary = summary[:117].rstrip() + "..."
    return title, summary


def _scan_linked_project_files(source_dir: Path) -> list[dict]:
    """Walk source_dir recursively for *.md files. Return [{name,title,summary,mtime,size}]."""
    files: list[dict] = []
    for md in sorted(source_dir.rglob("*.md")):
        if not md.is_file():
            continue
        try:
            stat = md.stat()
        except OSError:
            continue
        title, summary = _extract_title_and_summary(md)
        files.append({
            "name": md.name,
            "relpath": str(md.relative_to(source_dir)),
            "title": title,
            "summary": summary,
            "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "size": stat.st_size,
            "abspath": str(md),
        })
    return files


def _linked_file_body(path: Path) -> str:
    """Return markdown body text for linked-file search without requiring plugin frontmatter."""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return ""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5 :]
    return text


def _index_linked_project_files(project_name: str, files: list[dict]) -> int:
    """Upsert linked external files into their own FTS-backed table."""
    ensure_db()
    conn = db_connect()
    desired_paths = {f["abspath"] for f in files}
    indexed = 0
    with conn:
        if desired_paths:
            placeholders = ",".join("?" for _ in desired_paths)
            conn.execute(
                f"DELETE FROM linked_files WHERE project = ? AND source_path NOT IN ({placeholders})",  # nosec: parameterized IN-clause, values bound as params
                [project_name, *sorted(desired_paths)],
            )
        else:
            conn.execute("DELETE FROM linked_files WHERE project = ?", (project_name,))
        for f in files:
            body = _linked_file_body(Path(f["abspath"]))
            conn.execute(
                """
                INSERT INTO linked_files
                  (project, source_path, relpath, name, title, summary, mtime, size, body)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_path) DO UPDATE SET
                  project=excluded.project,
                  relpath=excluded.relpath,
                  name=excluded.name,
                  title=excluded.title,
                  summary=excluded.summary,
                  mtime=excluded.mtime,
                  size=excluded.size,
                  body=excluded.body
                """,
                (
                    project_name,
                    f["abspath"],
                    f["relpath"],
                    f["name"],
                    f["title"],
                    f["summary"],
                    f["mtime"],
                    f["size"],
                    body,
                ),
            )
            indexed += 1
    conn.close()
    return indexed


def _refresh_linked_project_symlinks(project_name: str, files: list[dict]) -> list[Path]:
    """Refresh <content-root>/projects/<name>/ symlinks for a linked external project.

    Keeps one symlink per unique filename (collisions within one project resolve to last-seen).
    Wipes stale links that no longer appear in `files`. Returns list of link paths created.
    """
    link_dir = _managed_projects_dir() / project_name
    link_dir.mkdir(parents=True, exist_ok=True)
    desired: dict[str, str] = {}  # name -> abspath
    for f in files:
        desired[f["name"]] = f["abspath"]
    # Remove any existing symlinks not in desired
    existing = {c.name for c in link_dir.iterdir()} if link_dir.exists() else set()
    for stale_name in existing - set(desired.keys()):
        stale = link_dir / stale_name
        if stale.is_symlink() or stale.is_file():
            try:
                stale.unlink()
            except OSError:
                pass
    # Create / refresh
    out: list[Path] = []
    for name, target in desired.items():
        link = link_dir / name
        if link.is_symlink() or link.exists():
            try:
                link.unlink()
            except OSError:
                pass
        try:
            link.symlink_to(target)
            out.append(link)
        except OSError as e:
            print(f"WARN: could not symlink {link} -> {target}: {e}", file=sys.stderr)
    return out


def cmd_save(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    src_path = Path(args.file).resolve()
    if not src_path.exists():
        print(f"ERROR: file not found: {src_path}", file=sys.stderr)
        return 2
    text = src_path.read_text()
    fm, body = parse_frontmatter(text)
    if not fm.get("slug"):
        print("ERROR: entry missing slug in frontmatter", file=sys.stderr)
        return 2

    # Required defaults, coercing explicit-null (None) to empty-list/defaults
    fm.setdefault("created", today_iso())
    fm["reviewed"] = today_iso()
    fm.setdefault("status", "evergreen")
    fm.setdefault("workflow", "general")
    fm.setdefault("confidence", "inferred")
    fm.setdefault("corroboration", 0)
    actor = _actor_from_args(args)
    run_id = str(getattr(args, "run_id", None) or os.environ.get("RESEARCH_RUN_ID") or _new_id("run"))
    fm["research_run_id"] = run_id
    fm["provenance"] = {
        "actor_type": actor["actor_type"],
        "actor_id": actor["actor_id"],
        "host": actor["host"],
        "session_id": actor["session_id"],
        "tool_version": actor["tool_version"],
    }
    for list_key, default in [
        ("topics", [top_level_topic(fm["slug"])]),
        ("projects", []),
        ("tags", []),
        ("sources", []),
        ("related", []),
        ("inbound", []),
    ]:
        if fm.get(list_key) is None:
            fm[list_key] = default

    # Reject malformed claimed identities before writing the canonical file.
    try:
        for item in fm.get("sources", []):
            source = {"url": item} if isinstance(item, str) else dict(item or {})
            url = source.get("url") or source.get("source_url")
            if not url:
                continue
            canonical_source = _canonical_source_url(str(url))
            claimed_hash = _validate_hash_ref(source.get("content_hash"), "content_hash")
            _validate_hash_ref(source.get("normalized_hash"), "normalized_hash")
            if canonical_source.startswith("file:") and claimed_hash:
                local_path = Path(urllib.parse.unquote(urllib.parse.urlsplit(canonical_source).path))
                if local_path.is_file() and "sha256:" + _file_sha256(local_path) != claimed_hash:
                    raise ValueError(f"content_hash does not match local file: {local_path}")
    except (TypeError, ValueError) as exc:
        print(f"ERROR: invalid source metadata: {exc}", file=sys.stderr)
        return 2

    # Collision resolution
    original_slug = fm["slug"]
    fm["slug"] = _resolve_collision(original_slug, fm)
    if fm["slug"] != original_slug:
        print(f"Slug collision: {original_slug} -> {fm['slug']}")

    # Determine canonical path
    canonical = _slug_to_path(fm["slug"])
    canonical.parent.mkdir(parents=True, exist_ok=True)
    sections = split_sections(body)

    # For project symlink line preview
    fm["tldr_preview"] = (sections["tldr"].split("\n")[0] if sections["tldr"] else "")[:80]

    # Write canonical file (with slug update applied)
    # Strip internal tldr_preview before writing frontmatter
    write_fm = {k: v for k, v in fm.items() if k != "tldr_preview"}
    new_text = dump_frontmatter(write_fm, body)
    canonical.write_text(new_text)

    # If source was elsewhere, move the original (unless it's the canonical path already)
    if src_path.resolve() != canonical.resolve() and args.move_source:
        src_path.unlink()

    # DB upsert
    conn = db_connect()
    verification = write_fm.get("verification") or {}
    row = (
        fm["slug"],
        str(canonical),
        fm.get("title", ""),
        json.dumps(fm.get("topics", [])),
        json.dumps(fm.get("projects", [])),
        json.dumps(fm.get("tags", [])),
        json.dumps(fm.get("sources", [])),
        fm.get("status", "evergreen"),
        fm.get("workflow", "general"),
        fm.get("created", today_iso()),
        fm.get("reviewed", today_iso()),
        fm.get("topic_velocity", "medium"),
        fm.get("confidence", "inferred"),
        int(fm.get("corroboration", 0)),
        sections["tldr"],
        sections["notes"],
        sections["raw"],
        json.dumps(verification),
        json.dumps(fm.get("inbound", [])),
    )
    with conn:
        _ensure_run(
            conn,
            run_id,
            actor,
            objective=str(fm.get("research_question") or fm.get("title") or fm["slug"]),
            outcome=str(fm.get("decision_use") or "persisted research entry"),
        )
        conn.execute(
            """
            INSERT INTO entries
          (slug, path, title, topics, projects, tags, sources, status, workflow,
           created, reviewed, topic_velocity, confidence, corroboration,
           tldr, notes, raw, verification, inbound)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
          path=excluded.path,
          title=excluded.title,
          topics=excluded.topics,
          projects=excluded.projects,
          tags=excluded.tags,
          sources=excluded.sources,
          status=excluded.status,
          workflow=excluded.workflow,
          created=excluded.created,
          reviewed=excluded.reviewed,
          topic_velocity=excluded.topic_velocity,
          confidence=excluded.confidence,
          corroboration=excluded.corroboration,
          tldr=excluded.tldr,
          notes=excluded.notes,
          raw=excluded.raw,
          verification=excluded.verification,
          inbound=excluded.inbound
            """,
            row,
        )
        observation_ids = _record_sources_for_entry(
            conn,
            sources=fm.get("sources", []),
            run_id=run_id,
            entry_slug=fm["slug"],
        )
        _record_entry_graph(
            conn,
            slug=fm["slug"],
            title=str(fm.get("title") or fm["slug"]),
            run_id=run_id,
            observation_ids=observation_ids,
        )
        prior_run_status = conn.execute("SELECT status FROM research_runs WHERE run_id=?", (run_id,)).fetchone()["status"]
        completed_at = now_iso()
        conn.execute(
            "UPDATE research_runs SET status='completed', completed_at=COALESCE(completed_at, ?) WHERE run_id=?",
            (completed_at, run_id),
        )
        _append_event(
            conn,
            event_type="entry.saved",
            run_id=run_id,
            actor_type=actor["actor_type"],
            actor_id=actor["actor_id"],
            payload={
                "slug": fm["slug"],
                "canonical_path": str(canonical),
                "canonical_sha256": _file_sha256(canonical),
                "source_observation_ids": observation_ids,
                "projects": fm.get("projects", []),
                "topics": fm.get("topics", []),
            },
            actor_snapshot=actor,
        )
        if prior_run_status != "completed":
            _append_event(
                conn,
                event_type="run.completed",
                run_id=run_id,
                actor_type=actor["actor_type"],
                actor_id=actor["actor_id"],
                payload={"completed_at": completed_at, "final_entry_slug": fm["slug"]},
                actor_snapshot=actor,
            )
    conn.close()

    # v0.3.1: plugin-managed projects get ONE symlink at <content-root>/projects/<name>/<slug>.md.
    # No file copies. No writes into the project directory (unless --with-project-index).
    project_outputs: list[tuple[str, Path]] = []  # (project_name, managed_symlink_path)
    with_project_index = bool(getattr(args, "with_project_index", False))
    if not args.skip_symlink:
        for proj in fm.get("projects", []):
            managed_link = _write_managed_symlink(proj, canonical)
            project_outputs.append((proj, managed_link))
            # Opt-in: also regenerate <project>/RossLabs-Research.md
            if with_project_index:
                proj_dir = GIT_FOLDER / proj
                if proj_dir.exists() and proj_dir.is_dir():
                    _note_v030_artifacts(proj_dir)
                    _rebuild_project_research_md(proj_dir)

    # Rebuild indexes (canonical + portfolio) unless explicitly skipped
    skip_index = bool(args.skip_index or getattr(args, "no_index", False))
    if not skip_index:
        _rebuild_indexes()
        _rebuild_portfolio()

    print(f"Saved: {fm['slug']}")
    print(f"  Canonical: {canonical}")
    for proj, managed_link in project_outputs:
        print(f"  Project:  {proj}")
        print(f"    Symlink: {managed_link}")
        if with_project_index:
            print(f"    Index:   {GIT_FOLDER / proj / 'RossLabs-Research.md'}")
    if not skip_index:
        print(f"  Portfolio: {content_path('PORTFOLIO.md')}")
    print(f"  Corroboration: {fm.get('corroboration', 0)}  Confidence: {fm.get('confidence')}")
    print(f"  Run: {run_id}")
    return 0


# ---------- search ----------

def _quote_fts_token(token: str) -> str:
    return '"' + token.replace('"', '""') + '"'


def _plain_fts_query(query: str) -> str:
    """Convert normal user text into a safe FTS5 AND query.

    FTS5 treats punctuation such as hyphen as syntax in raw queries. Quoting each
    token keeps everyday searches like `research-plugin` from becoming parser
    errors while still allowing quoted phrases from the user's input.
    """
    tokens: list[str] = []
    for match in re.finditer(r'"([^"]+)"|(\S+)', query):
        token = (match.group(1) or match.group(2) or "").strip()
        token = token.strip(" \t\r\n,;:!?()[]{}<>")
        if token:
            tokens.append(_quote_fts_token(token))
    return " ".join(tokens)


def _search_entries(conn: sqlite3.Connection, args: argparse.Namespace, fts_query: str) -> list[dict]:
    where_clauses = ["entries_fts MATCH ?"]
    params: list[Any] = [fts_query]
    if args.tag:
        where_clauses.append("entries.tags LIKE ?")
        params.append(f'%"{args.tag}"%')
    if args.topic:
        where_clauses.append("entries.topics LIKE ?")
        params.append(f'%"{args.topic}"%')
    if args.project:
        where_clauses.append("entries.projects LIKE ?")
        params.append(f'%"{args.project}"%')
    if args.status:
        where_clauses.append("entries.status = ?")
        params.append(args.status)

    sql = f"""
        SELECT 'entry' AS kind,
               entries.slug,
               entries.title,
               entries.path,
               entries.reviewed,
               entries.confidence,
               entries.corroboration,
               NULL AS project,
               NULL AS relpath,
               bm25(entries_fts, 8.0, 6.0, 4.0, 2.0, 1.0) AS score,
               snippet(entries_fts, -1, '[', ']', ' ... ', 32) AS snippet
        FROM entries_fts
        JOIN entries ON entries.id = entries_fts.rowid
        WHERE {' AND '.join(where_clauses)}
        ORDER BY score
        LIMIT ?
    """
    params.append(args.n)
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _search_linked_files(conn: sqlite3.Connection, args: argparse.Namespace, fts_query: str) -> list[dict]:
    if args.entries_only or args.tag or args.topic or args.status:
        return []
    where_clauses = ["linked_files_fts MATCH ?"]
    params: list[Any] = [fts_query]
    if args.project:
        where_clauses.append("linked_files.project = ?")
        params.append(args.project)

    sql = f"""
        SELECT 'linked' AS kind,
               linked_files.project || '/' || linked_files.relpath AS slug,
               linked_files.title,
               linked_files.source_path AS path,
               linked_files.mtime AS reviewed,
               'linked' AS confidence,
               0 AS corroboration,
               linked_files.project AS project,
               linked_files.relpath AS relpath,
               bm25(linked_files_fts, 2.0, 3.0, 6.0, 4.0, 1.0) AS score,
               snippet(linked_files_fts, -1, '[', ']', ' ... ', 32) AS snippet
        FROM linked_files_fts
        JOIN linked_files ON linked_files.id = linked_files_fts.rowid
        WHERE {' AND '.join(where_clauses)}
        ORDER BY score
        LIMIT ?
    """
    params.append(args.n)
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def cmd_search(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    fts_query = args.query if args.fts_query else _plain_fts_query(args.query)
    if not fts_query:
        print("ERROR: empty search query", file=sys.stderr)
        conn.close()
        return 2
    try:
        rows = _search_entries(conn, args, fts_query)
        rows.extend(_search_linked_files(conn, args, fts_query))
        rows.sort(key=lambda r: r["score"])
        rows = rows[: args.n]
    except sqlite3.OperationalError as e:
        print(f"Query error: {e}", file=sys.stderr)
        conn.close()
        return 2
    conn.close()
    if args.json:
        print(json.dumps([dict(r) for r in rows], indent=2, default=str))
    else:
        if not rows:
            print("No matches.")
            return 0
        for r in rows:
            label = r["confidence"] if r["kind"] == "entry" else "linked"
            print(f"  [{label:8s}] {r['slug']:50s}  {r['title']}")
            print(f"     {r['path']}  (reviewed {r['reviewed']}, corroboration {r['corroboration']})")
            if r.get("snippet"):
                print(f"     {r['snippet']}")
    return 0


# ---------- research depth ----------

DEPTH_LIGHT_PATTERNS = [
    r"\bquick\b",
    r"\bbrief\b",
    r"\bshort\b",
    r"\bsimple\b",
    r"\btldr\b",
    r"\bwhat is\b",
    r"\bdefine\b",
    r"\bsummarize\b",
]

DEPTH_STANDARD_PATTERNS = [
    r"\bresearch\b",
    r"\binvestigate\b",
    r"\blook into\b",
]

DEPTH_DEEP_PATTERNS = [
    r"\bdeep\b",
    r"\bthorough\b",
    r"\bcomprehensive\b",
    r"\bexpansive\b",
    r"\bexhaustive\b",
    r"\bfull\b",
    r"\bsystematic\b",
    r"\bwide[- ]?ranging\b",
    r"\blandscape\b",
    r"\bstrategy\b",
    r"\brecommend\b",
    r"\brecommendation\b",
    r"\bdecision[- ]?grade\b",
    r"\bsource[- ]?backed\b",
    r"\bliterature\b",
    r"\barchitecture\b",
    r"\btrade[- ]?off",
    r"\brisk\b",
    r"\broadmap\b",
    r"\bbenchmark\b",
    r"\bvalidate\b",
    r"\bverification\b",
    r"\bpersona\b",
]

DEPTH_COMPARISON_PATTERNS = [
    r"\bcompare\b",
    r"\bversus\b",
    r"\bvs\.?\b",
    r"\bbetter\b",
    r"\boptions\b",
    r"\balternatives\b",
    r"\bevaluate\b",
    r"\bassess\b",
]

DEPTH_FRESHNESS_PATTERNS = [
    r"\blatest\b",
    r"\bcurrent\b",
    r"\btoday\b",
    r"\bnow\b",
    r"\bpricing\b",
    r"\bversion\b",
    r"\brelease\b",
    r"\bnews\b",
    r"\bstatus\b",
]

DEPTH_HIGH_STAKES_PATTERNS = [
    r"\blegal\b",
    r"\bmedical\b",
    r"\bclinical\b",
    r"\bfinancial\b",
    r"\binvestment\b",
    r"\btax\b",
    r"\bsecurity\b",
    r"\bcompliance\b",
]

DEPTH_QUANT_PATTERNS = [
    r"\bcalculate\b",
    r"\bquantitative\b",
    r"\bmetric\b",
    r"\bmetrics\b",
    r"\bcsv\b",
    r"\bdatabase\b",
    r"\bsql\b",
    r"\btable\b",
    r"\bschema\b",
]


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _coverage_requirements(depth: str, workflow: str, web_required: bool) -> dict[str, Any]:
    if depth == "deep":
        source_mix = {
            "primary_or_official": 2,
            "independent_analysis": 3,
            "counter_evidence": 2,
            "freshness_check": 1 if web_required else 0,
        }
        lanes = [
            "Primary/original sources for the core facts",
            "Independent expert, academic, or industry sources for corroboration",
            "Counter-evidence covering risks, criticism, failures, and alternatives",
            "Temporal coverage for changing facts, including recent updates when relevant",
            "Explicit gaps plus what evidence would change the answer",
        ]
        evidence = [
            "Maintain a source register with tier, date, role, and independence notes",
            "Extract a claim-level evidence matrix before synthesis",
            "Verify critical numeric, technical, legal, financial, medical, or security claims",
            "Persist by default with Raw source extracts retained",
        ]
    elif depth == "standard":
        source_mix = {
            "primary_or_official": 1,
            "independent_analysis": 1,
            "counter_evidence": 1,
            "freshness_check": 1 if web_required else 0,
        }
        lanes = [
            "Primary/official source where available",
            "At least one independent source for corroboration or contrast",
            "Counter-evidence or limitations search when the answer affects a decision",
            "Date check for time-sensitive facts",
            "Gaps and limitations stated explicitly",
        ]
        evidence = [
            "Record each source's role before synthesis",
            "Extract specific claims and data points rather than impressions",
            "Persist when the result is reusable, report-sized, or project-relevant",
        ]
    else:
        source_mix = {
            "primary_or_official": 0,
            "independent_analysis": 0,
            "counter_evidence": 0,
            "freshness_check": 1 if web_required else 0,
        }
        lanes = [
            "Answer the exact question",
            "Use a source only when the fact is external, current, or uncertain",
            "State uncertainty instead of expanding scope silently",
        ]
        evidence = [
            "Cite any external source used",
            "Skip persistence unless the user asks or the answer is reusable",
        ]

    if workflow == "quantitative":
        evidence.append("Profile data and run deterministic calculations before quantitative claims")
    elif workflow == "collection":
        evidence.append("Preserve source-faithful extraction and avoid claim flattening")
    elif workflow == "synthesis":
        evidence.append("Separate authorial findings from executive interpretation")

    return {
        "source_mix": source_mix,
        "lanes": lanes,
        "evidence_expectations": evidence,
    }


def _research_depth_profile(query: str) -> dict[str, Any]:
    text = " ".join(query.lower().split())
    words = re.findall(r"\b[\w-]+\b", text)
    score = 0
    reasons: list[str] = []

    if not text:
        return {
            "depth": "light",
            "score": 0,
            "workflow": "general",
            "web_required": False,
            "persist": False,
            "source_budget": {"target": 0, "minimum": 0, "maximum": 0},
            "coverage": _coverage_requirements("light", "general", False),
            "phases": ["ask-for-question"],
            "reasons": ["No research question provided."],
        }

    if _matches_any(text, DEPTH_DEEP_PATTERNS):
        score += 3
        reasons.append("Deep-work language: thorough, expansive, strategy, recommendation, validation, risk, architecture, or similar.")
    if _matches_any(text, DEPTH_COMPARISON_PATTERNS):
        score += 2
        reasons.append("Comparison or evaluation requires criteria and multiple sources.")
    if _matches_any(text, DEPTH_STANDARD_PATTERNS):
        score += 2
        reasons.append("Explicit research language needs a bounded multi-source pass.")
    if _matches_any(text, DEPTH_FRESHNESS_PATTERNS):
        score += 2
        reasons.append("Freshness-sensitive terms require current-source checking.")
    if _matches_any(text, DEPTH_HIGH_STAKES_PATTERNS):
        score += 3
        reasons.append("High-stakes domain requires stronger verification and caveats.")
    if _matches_any(text, DEPTH_QUANT_PATTERNS):
        score += 3
        reasons.append("Quantitative or tabular claims require profiling and computed validation.")
    if re.search(r"\b(deep|thorough|comprehensive|expansive|exhaustive|systematic|full)\s+(research|investigation|analysis|review)\b", text):
        score = max(score, 5)
        reasons.append("User explicitly requested deep research depth.")
    if re.search(r"\b(quick|light|brief|short)\s+(research|answer|lookup|summary|take|pass)\b", text) and score < 5:
        score = min(score, 1)
        reasons = [
            reason for reason in reasons
            if reason != "Explicit research language needs a bounded multi-source pass."
        ]
        reasons.append("User explicitly requested light research depth.")
    if len(words) >= 28:
        score += 2
        reasons.append("Long request likely contains multiple subquestions or constraints.")
    elif len(words) <= 8 and _matches_any(text, DEPTH_LIGHT_PATTERNS):
        score -= 1
        reasons.append("Short definitional or summary request can be handled lightly.")
    if re.search(r"\b(one|1)\s+(source|link|url|file|doc|document)\b", text):
        score -= 1
        reasons.append("Single-source request limits scope.")
    if re.search(r"\b(no need to save|inline only|don't save|do not save)\b", text):
        score -= 2
        reasons.append("User asked for inline-only or no persistence.")

    workflow = "general"
    if _matches_any(text, DEPTH_QUANT_PATTERNS):
        workflow = "quantitative"
    elif re.search(r"\bextract|collect|pull data|key claims|what does this say\b", text):
        workflow = "collection"
    elif re.search(r"\bsynthesize|executive summary|combine findings|what should we do\b", text):
        workflow = "synthesis"

    web_required = _matches_any(text, DEPTH_FRESHNESS_PATTERNS) or bool(
        re.search(r"\bweb|internet|sources|pricing|competitor|market|latest\b", text)
    )

    if score >= 5:
        depth = "deep"
        source_budget = {"target": 10, "minimum": 7, "maximum": 15}
        phases = ["frame", "coverage-plan", "source-register", "collect", "synthesize", "verify", "persist"]
        persist = True
    elif score >= 2:
        depth = "standard"
        source_budget = {"target": 5, "minimum": 3, "maximum": 8}
        phases = ["frame", "coverage-plan", "source", "synthesize", "persist-if-reusable"]
        persist = not re.search(r"\b(no need to save|inline only|don't save|do not save)\b", text)
    else:
        depth = "light"
        source_budget = {"target": 1, "minimum": 0, "maximum": 2}
        phases = ["answer", "cite-if-external", "skip-persist-unless-reusable"]
        persist = False

    if not reasons:
        reasons.append("No deep-work signals detected; defaulting to a bounded light pass.")

    return {
        "depth": depth,
        "score": score,
        "workflow": workflow,
        "web_required": web_required,
        "persist": persist,
        "source_budget": source_budget,
        "coverage": _coverage_requirements(depth, workflow, web_required),
        "phases": phases,
        "reasons": reasons,
    }


def cmd_depth(args: argparse.Namespace) -> int:
    profile = _research_depth_profile(args.query)
    if args.json:
        print(json.dumps(profile, indent=2))
        return 0

    print(f"Research depth: {profile['depth']} (score {profile['score']})")
    print(f"Workflow: {profile['workflow']}")
    print(f"Web required: {'yes' if profile['web_required'] else 'no'}")
    print(f"Persist: {'yes' if profile['persist'] else 'no'}")
    budget = profile["source_budget"]
    print(
        "Source budget: "
        f"target {budget['target']} "
        f"(min {budget['minimum']}, max {budget['maximum']})"
    )
    print("Phases: " + " -> ".join(profile["phases"]))
    coverage = profile["coverage"]
    print("Coverage lanes:")
    for lane in coverage["lanes"]:
        print(f"  - {lane}")
    print("Source mix minimums:")
    for lane, minimum in coverage["source_mix"].items():
        print(f"  - {lane}: {minimum}")
    print("Evidence expectations:")
    for expectation in coverage["evidence_expectations"]:
        print(f"  - {expectation}")
    print("Reasons:")
    for reason in profile["reasons"]:
        print(f"  - {reason}")
    return 0


# ---------- list ----------

def cmd_list(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    sql = "SELECT slug, title, path, reviewed, confidence, corroboration, status FROM entries"
    params: list = []
    if args.status:
        sql += " WHERE status = ?"
        params.append(args.status)
    sql += " ORDER BY reviewed DESC LIMIT ?"
    params.append(args.n)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    if args.json:
        print(json.dumps([dict(r) for r in rows], indent=2, default=str))
        return 0
    if not rows:
        print("No entries.")
        return 0
    for r in rows:
        print(f"  {r['reviewed']}  [{r['confidence']:8s}] {r['slug']:50s}  {r['title']}")
    return 0


# ---------- link ----------

def cmd_link(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    row = conn.execute(
        "SELECT path, projects, title, reviewed, confidence, tldr FROM entries WHERE slug = ?",
        (args.slug,),
    ).fetchone()
    if not row:
        print(f"ERROR: no entry with slug: {args.slug}", file=sys.stderr)
        conn.close()
        return 2
    entry_path = Path(row["path"])
    proj_path = Path(args.project_path or Path.cwd()).resolve()
    if not proj_path.is_dir():
        print(f"ERROR: not a directory: {proj_path}", file=sys.stderr)
        conn.close()
        return 2

    # Update projects list in DB
    projs = json.loads(row["projects"] or "[]")
    project_name = proj_path.name
    if project_name not in projs:
        projs.append(project_name)
        conn.execute(
            "UPDATE entries SET projects = ? WHERE slug = ?",
            (json.dumps(projs), args.slug),
        )
        conn.commit()

    # Update entry file frontmatter too
    text = entry_path.read_text()
    fm, body = parse_frontmatter(text)
    fm["projects"] = projs
    entry_path.write_text(dump_frontmatter(fm, body))

    # v0.3.1: managed symlink under <content-root>/projects/<name>/<slug>.md
    managed_link = _write_managed_symlink(project_name, entry_path)
    _note_v030_artifacts(proj_path)
    conn.close()
    print(f"Linked {args.slug} -> {managed_link}")
    return 0


# ---------- link-project (v0.3.1) ----------

def _do_link_project(project_name: str, source_dir: Path) -> dict:
    """Register an external project research directory, scan it, create symlinks.

    Returns the registry entry dict that was written. Idempotent.
    """
    ensure_layout()
    ensure_db()
    source_dir = source_dir.resolve()
    if not source_dir.is_dir():
        raise ValueError(f"not a directory: {source_dir}")

    files = _scan_linked_project_files(source_dir)
    # Refresh symlinks at <content-root>/projects/<project_name>/
    _refresh_linked_project_symlinks(project_name, files)
    indexed = _index_linked_project_files(project_name, files)

    # Persist registry entry (without abspath — keep entry lean; can be rebuilt from path)
    registry = _read_linked_projects_registry()
    entry = {
        "path": str(source_dir),
        "linked": today_iso(),
        "files": [
            {k: f[k] for k in ("name", "relpath", "title", "summary", "mtime", "size")}
            for f in files
        ],
        "indexed": indexed,
    }
    registry[project_name] = entry
    _write_linked_projects_registry(registry)
    return entry


def cmd_link_project(args: argparse.Namespace) -> int:
    """Register an existing project research directory as a linked external source.

    Walks the directory recursively for *.md files, extracts title + 1-line summary,
    records registration in the index-root registry, creates symlinks under
    <content-root>/projects/<name>/. Does NOT modify the project directory.
    """
    ensure_layout()
    ensure_db()
    source_value = args.path or args.path_arg
    if not source_value:
        print("ERROR: missing path. Use: link-project <name> <path> or link-project <name> --path <path>", file=sys.stderr)
        return 2
    source = Path(source_value).expanduser()
    if not source.is_absolute():
        source = (Path.cwd() / source).resolve()
    if not source.exists():
        print(f"ERROR: path not found: {source}", file=sys.stderr)
        return 2
    if not source.is_dir():
        print(f"ERROR: not a directory: {source}", file=sys.stderr)
        return 2
    try:
        entry = _do_link_project(args.name, source)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # Rebuild portfolio so the linked project shows up
    if not getattr(args, "no_index", False):
        _rebuild_portfolio()

    link_dir = _managed_projects_dir() / args.name
    print(f"Linked project: {args.name}")
    print(f"  Source:   {entry['path']}")
    print(f"  Files:    {len(entry['files'])}")
    print(f"  Indexed:  {entry.get('indexed', len(entry['files']))}")
    print(f"  Symlinks: {link_dir}/")
    print(f"  Registry: {_linked_projects_registry_path()}")
    return 0


# ---------- index ----------

def _rebuild_project_research_md(project_path: Path) -> Path | None:
    """Regenerate <project>/RossLabs-Research.md from canonical entries linked to this project.

    Returns the index file path, or None if no entries point to this project.
    Pure read from DB + filesystem; no LLM calls.
    """
    ensure_db()
    conn = db_connect()
    project_name = project_path.name
    rows = [dict(r) for r in conn.execute(
        "SELECT slug, title, path, topics, projects, tags, reviewed, status, "
        "confidence, tldr FROM entries WHERE status != 'archived' ORDER BY slug"
    ).fetchall()]
    conn.close()
    matched: list[dict] = []
    for r in rows:
        projs = json.loads(r["projects"] or "[]")
        if project_name in projs:
            r["topics"] = json.loads(r["topics"] or "[]")
            r["tags"] = json.loads(r["tags"] or "[]")
            matched.append(r)
    index_md = project_path / "RossLabs-Research.md"
    if not matched:
        # No entries; leave any pre-existing index alone (may be from v0.3.0; user choice to keep/remove).
        return None
    # Group by top-level topic from slug
    by_top: dict[str, list[dict]] = {}
    for r in matched:
        by_top.setdefault(top_level_topic(r["slug"]), []).append(r)

    lines: list[str] = []
    lines.append(f"# Research \u2014 {project_name}\n\n")
    lines.append("_Auto-generated by RossLabs Research Plugin. Do not edit by hand; "
                 "changes are overwritten on next save._\n\n")
    lines.append(f"Last updated: {today_iso()}\n\n")
    lines.append(f"## Entries ({len(matched)} total)\n\n")
    for top in sorted(by_top):
        lines.append(f"### {top}\n")
        for r in sorted(by_top[top], key=lambda x: x["slug"]):
            # v0.3.1: link to canonical file under the content root (no project file copies).
            canonical_path = Path(r["path"])
            confidence = r.get("confidence", "inferred") or "inferred"
            status = r.get("status", "evergreen") or "evergreen"
            summary = _summary_from_tldr(r.get("tldr") or "")
            head = f"- [{r['title']}]({canonical_path}) \u2014 reviewed {r['reviewed']}, {confidence}, {status}\n"
            lines.append(head)
            if summary:
                lines.append(f"  > {summary}\n")
        lines.append("\n")

    # Cross-references section
    lines.append("## Cross-references\n\n")
    lines.append("This project's research also relates to entries in the central corpus:\n")
    # For each topic touched by this project, show count of total entries vs here
    conn2 = db_connect()
    total_rows = [dict(r) for r in conn2.execute(
        "SELECT slug FROM entries WHERE status != 'archived'"
    ).fetchall()]
    conn2.close()
    total_by_top: dict[str, int] = {}
    for r in total_rows:
        total_by_top[top_level_topic(r["slug"])] = total_by_top.get(top_level_topic(r["slug"]), 0) + 1
    for top in sorted(by_top):
        total = total_by_top.get(top, len(by_top[top]))
        here = len(by_top[top])
        lines.append(f"- `{content_path('topics', top)}/` ({total} total entries, {here} here)\n")
    lines.append("\n")
    lines.append(f"For the full master portfolio across all your projects, see `{content_path('PORTFOLIO.md')}`.\n")

    index_md.write_text("".join(lines))
    return index_md


def _rebuild_portfolio() -> Path:
    """Regenerate the content-root PORTFOLIO.md with plugin-managed, linked, and cross-cutting sections."""
    ensure_db()
    conn = db_connect()
    rows = [dict(r) for r in conn.execute(
        "SELECT slug, title, path, topics, projects, tags, reviewed, status FROM entries "
        "WHERE status != 'archived'"
    ).fetchall()]
    conn.close()
    by_project: dict[str, list[dict]] = {}
    cross_cutting: list[dict] = []
    for r in rows:
        projs = json.loads(r["projects"] or "[]")
        r["topics"] = json.loads(r["topics"] or "[]")
        r["tags"] = json.loads(r["tags"] or "[]")
        if not projs:
            cross_cutting.append(r)
        else:
            for p in projs:
                by_project.setdefault(p, []).append(r)

    registry = _read_linked_projects_registry()

    lines: list[str] = []
    lines.append("# Research Portfolio\n\n")
    lines.append(f"_Auto-generated. Updated: {today_iso()}_\n\n")

    # --- Plugin-managed projects ---
    lines.append("## Plugin-managed projects\n\n")
    lines.append("_Entries saved through `/research:save` with a `projects:` tag. "
                 f"Symlinks live at `{content_path('projects')}/<name>/`._\n\n")
    if not by_project:
        lines.append("_No project-tagged entries yet._\n\n")
    for proj in sorted(by_project):
        entries = by_project[proj]
        last_reviewed = max((e.get("reviewed") or "") for e in entries) or "unknown"
        topics_set = sorted({top_level_topic(e["slug"]) for e in entries})
        symlink_dir = _managed_projects_dir() / proj
        lines.append(f"### {proj}\n")
        lines.append(f"- {len(entries)} entries, last updated {last_reviewed}\n")
        lines.append(f"- Topics: {', '.join(topics_set)}\n")
        lines.append(f"- Symlink dir: {symlink_dir}/\n")
        tops = sorted({top_level_topic(e["slug"]) for e in entries})
        for top in tops:
            lines.append(f"- Central entries: {content_path('topics', top)}/\n")
        lines.append("\n")

    # --- Linked external research directories ---
    lines.append("## Linked external research directories\n\n")
    lines.append("_Registered via `/research:link-project`. The plugin does not own "
                 "or modify these files; it only reads, summarizes, and links them._\n\n")
    if not registry:
        lines.append("_None registered yet._\n\n")
    for name in sorted(registry):
        entry = registry[name]
        files = entry.get("files", [])
        lines.append(f"### {name}\n")
        lines.append(f"- Source: {entry.get('path', '?')}\n")
        lines.append(f"- {len(files)} files, last linked {entry.get('linked', '?')}\n")
        if files:
            lines.append("- Files:\n")
            for f in sorted(files, key=lambda x: x.get("relpath") or x.get("name", "")):
                relpath = f.get("relpath") or f.get("name", "")
                title = f.get("title") or f.get("name", "")
                summary = f.get("summary") or ""
                line = f"  - {relpath} \u2014 {title}"
                if summary:
                    line += f" \u2014 {summary}"
                lines.append(line + "\n")
        lines.append("\n")

    # --- Cross-cutting (unchanged) ---
    lines.append("## Cross-cutting\n\n")
    lines.append("_Entries without a `projects:` tag._\n\n")
    if not cross_cutting:
        lines.append("_None._\n\n")
    else:
        by_top_cc: dict[str, list[dict]] = {}
        for r in cross_cutting:
            by_top_cc.setdefault(top_level_topic(r["slug"]), []).append(r)
        for top in sorted(by_top_cc):
            entries = by_top_cc[top]
            slugs = [e["slug"].split(".", 1)[1] if "." in e["slug"] else e["slug"]
                     for e in sorted(entries, key=lambda x: x["slug"])]
            lines.append(f"### {top} ({len(entries)} entries)\n")
            lines.append(f"- {', '.join(slugs)}\n\n")

    lines.append("## Discovery for external tools\n\n")
    lines.append("Any LLM or tool can point at this file as the entry point. "
                 "Each entry resolves to a markdown file with:\n")
    lines.append("- Frontmatter (slug, title, topics, sources with tier scoring)\n")
    lines.append("- Three-layer body: TL;DR / Notes / Raw\n")
    lines.append("- Cited sources\n\n")
    lines.append("Reading order for max coverage:\n")
    lines.append("1. PORTFOLIO.md (this file) \u2014 corpus overview\n")
    lines.append(f"2. {content_path('by-topic.md')} \u2014 flat topic index\n")
    lines.append(f"3. {content_path('topics')}/*/*.md \u2014 individual entries\n")
    out = content_path("PORTFOLIO.md")
    out.write_text("".join(lines))
    return out


def _rebuild_indexes() -> None:
    """Regenerate index.md / by-topic.md / by-project.md / indices/<topic>.md / inbound."""
    ensure_db()
    conn = db_connect()
    rows = [dict(r) for r in conn.execute(
        "SELECT slug, title, path, topics, projects, tags, reviewed, confidence, "
        "corroboration, status FROM entries WHERE status != 'archived' ORDER BY reviewed DESC"
    ).fetchall()]
    for r in rows:
        r["topics"] = json.loads(r["topics"] or "[]")
        r["projects"] = json.loads(r["projects"] or "[]")
        r["tags"] = json.loads(r["tags"] or "[]")

    # index.md (chronological)
    lines = ["# Research Index\n", f"Last rebuilt: {today_iso()}\n",
             f"Total entries: {len(rows)}\n\n",
             "| Date | Slug | Title | Topics | Confidence |\n",
             "|---|---|---|---|---|\n"]
    for r in rows:
        lines.append(
            f"| {r['reviewed']} | [`{r['slug']}`]({r['path']}) | {r['title']} | "
            f"{', '.join(r['topics'])} | {r['confidence']} |\n"
        )
    content_path("index.md").write_text("".join(lines))

    # by-topic.md
    by_topic: dict[str, list[dict]] = {}
    for r in rows:
        for topic in r["topics"]:
            by_topic.setdefault(topic, []).append(r)
    lines = ["# Research by Topic\n", f"Last rebuilt: {today_iso()}\n\n"]
    for topic in sorted(by_topic):
        lines.append(f"## {topic}\n\n")
        for r in sorted(by_topic[topic], key=lambda x: x["reviewed"], reverse=True):
            lines.append(f"- [`{r['slug']}`]({r['path']}) — {r['title']} ({r['reviewed']}, {r['confidence']})\n")
        lines.append("\n")
    content_path("by-topic.md").write_text("".join(lines))

    # by-tag.md
    by_tag: dict[str, list[dict]] = {}
    for r in rows:
        for tag in r["tags"]:
            by_tag.setdefault(tag, []).append(r)
    lines = ["# Research by Tag\n", f"Last rebuilt: {today_iso()}\n\n"]
    for tag in sorted(by_tag):
        lines.append(f"## {tag}\n\n")
        for r in sorted(by_tag[tag], key=lambda x: x["reviewed"], reverse=True):
            lines.append(f"- [`{r['slug']}`]({r['path']}) — {r['title']} ({r['reviewed']}, {r['confidence']})\n")
        lines.append("\n")
    content_path("by-tag.md").write_text("".join(lines))

    # by-project.md
    by_proj: dict[str, list[dict]] = {"(cross-cutting)": []}
    for r in rows:
        if not r["projects"]:
            by_proj["(cross-cutting)"].append(r)
        else:
            for p in r["projects"]:
                by_proj.setdefault(p, []).append(r)
    lines = ["# Research by Project\n", f"Last rebuilt: {today_iso()}\n\n"]
    for proj in sorted(by_proj):
        if not by_proj[proj]:
            continue
        lines.append(f"## {proj}\n\n")
        for r in sorted(by_proj[proj], key=lambda x: x["reviewed"], reverse=True):
            lines.append(f"- [`{r['slug']}`]({r['path']}) — {r['title']} ({r['reviewed']}, {r['confidence']})\n")
        lines.append("\n")
    content_path("by-project.md").write_text("".join(lines))

    # indices/<top-level>.md (MOCs)
    indices_dir = content_path("indices")
    indices_dir.mkdir(exist_ok=True)
    # Wipe stale MOCs
    for old in indices_dir.glob("*.md"):
        old.unlink()
    by_top: dict[str, list[dict]] = {}
    for r in rows:
        top = top_level_topic(r["slug"])
        by_top.setdefault(top, []).append(r)
    for top, entries in by_top.items():
        ml = [f"# {top} — Map of Content\n\n",
              f"Last rebuilt: {today_iso()}. {len(entries)} entries.\n\n"]
        for r in sorted(entries, key=lambda x: x["slug"]):
            ml.append(f"- [`{r['slug']}`]({r['path']}) — {r['title']} "
                      f"({r['reviewed']}, {r['confidence']}, corroboration {r['corroboration']})\n")
        (indices_dir / f"{top}.md").write_text("".join(ml))

    # Inbound link maintenance: scan Notes for [[slug]] refs, update each entry's inbound[]
    slug_to_id = {r["slug"]: None for r in rows}
    inbound_map: dict[str, set[str]] = {s: set() for s in slug_to_id}
    for r in rows:
        path = Path(r["path"])
        if not path.exists():
            continue
        body = path.read_text()
        for ref in re.findall(r"\[\[([^\]]+)\]\]", body):
            ref = ref.strip()
            # Strip archive/ prefix if present
            ref = re.sub(r"^archive/", "", ref)
            if ref in inbound_map and ref != r["slug"]:
                inbound_map[ref].add(r["slug"])
    # Persist inbound to DB + frontmatter
    for r in rows:
        inbound = sorted(inbound_map[r["slug"]])
        conn.execute("UPDATE entries SET inbound = ? WHERE slug = ?",
                     (json.dumps(inbound), r["slug"]))
        # Update frontmatter too (non-destructive)
        path = Path(r["path"])
        if path.exists():
            text = path.read_text()
            fm, body = parse_frontmatter(text)
            if fm.get("inbound") != inbound:
                fm["inbound"] = inbound
                path.write_text(dump_frontmatter(fm, body))
    _write_source_indexes(conn)
    conn.commit()
    conn.close()


def cmd_index(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    _rebuild_indexes()

    # v0.3.1: refresh plugin-managed symlinks at <content-root>/projects/<name>/<slug>.md
    # from current DB state (covers cases where slugs were renamed or projects re-tagged).
    conn = db_connect()
    rows = conn.execute(
        "SELECT slug, path, projects FROM entries WHERE status != 'archived'"
    ).fetchall()
    conn.close()
    managed_by_project: dict[str, set[str]] = {}
    for row in rows:
        canonical = Path(row["path"])
        for p in json.loads(row["projects"] or "[]"):
            _write_managed_symlink(p, canonical)
            managed_by_project.setdefault(p, set()).add(canonical.name)
    # Prune stale managed symlinks that no longer correspond to a DB entry
    projects_root = _managed_projects_dir()
    pruned = 0
    if projects_root.exists():
        linked_names = set(_read_linked_projects_registry().keys())
        for proj_dir in projects_root.iterdir():
            if not proj_dir.is_dir():
                continue
            if proj_dir.name in linked_names:
                # Handled by link-project rescan below
                continue
            desired = managed_by_project.get(proj_dir.name, set())
            for child in proj_dir.iterdir():
                if child.is_symlink() and child.name not in desired:
                    try:
                        child.unlink()
                        pruned += 1
                    except OSError:
                        pass

    # v0.3.1: re-scan every registered linked-external project and refresh its symlinks.
    registry = _read_linked_projects_registry()
    rescanned = 0
    missing: list[str] = []
    for name, entry in list(registry.items()):
        src = Path(entry.get("path", ""))
        if not src.is_dir():
            missing.append(f"{name} ({src})")
            continue
        _do_link_project(name, src)
        rescanned += 1
    portfolio = _rebuild_portfolio()

    print("Indexes rebuilt.")
    print(f"  Managed project symlinks: {sum(len(v) for v in managed_by_project.values())} across {len(managed_by_project)} project(s)")
    if pruned:
        print(f"  Pruned stale symlinks:    {pruned}")
    print(f"  Linked external projects: {rescanned} rescanned")
    if missing:
        print(f"  Missing sources:          {len(missing)}")
        for m in missing:
            print(f"    - {m}")
    print(f"  Portfolio:                {portfolio}")
    return 0


# ---------- archive ----------

def cmd_archive(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    row = conn.execute("SELECT path FROM entries WHERE slug = ?", (args.slug,)).fetchone()
    if not row:
        print(f"ERROR: no entry: {args.slug}", file=sys.stderr)
        conn.close()
        return 2
    orig = Path(row["path"])
    if not orig.exists():
        print(f"WARN: file missing, only updating DB: {orig}", file=sys.stderr)
    dest = content_path("archive", f"{args.slug}.md")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if orig.exists():
        shutil.move(str(orig), str(dest))
    # Write redirect stub at orig path
    stub = (
        f"---\n"
        f"status: archived\n"
        f"redirect: ../../archive/{args.slug}.md\n"
        f"archived: {today_iso()}\n"
        f"---\n"
        f"Archived. See [[archive/{args.slug}]].\n"
    )
    orig.parent.mkdir(parents=True, exist_ok=True)
    orig.write_text(stub)
    conn.execute("UPDATE entries SET status = 'archived', path = ? WHERE slug = ?",
                 (str(dest), args.slug))
    conn.commit()
    conn.close()
    _rebuild_indexes()
    print(f"Archived: {args.slug} -> {dest}")
    print(f"Redirect stub: {orig}")
    return 0


# ---------- score ----------

def _score_domain_by_rule(domain: str) -> tuple[str, str] | None:
    """Apply deterministic rules. Return (tier, reason) or None if no match."""
    d = domain.lower()
    if d == "arxiv.org" or d.endswith(".arxiv.org"):
        return ("T1", "arXiv preprint server")
    if d == "doi.org":
        return ("T1", "DOI resolver")
    if d.endswith(".gov"):
        return ("T1", "government domain")
    if d.endswith(".edu"):
        return ("T1", "educational/research institution")
    if d in ("github.com",):
        # Github default — without org context, treat as T2
        return ("T2", "github.com repository")
    if d.endswith(".readthedocs.io"):
        return ("T1", "ReadTheDocs official project docs")
    if d in ("reddit.com", "stackoverflow.com", "news.ycombinator.com"):
        return ("T3", "community discussion")
    if d in ("medium.com", "dev.to", "substack.com", "hashnode.dev"):
        return ("T3", "personal blog platform")
    return None


def lookup_domain(conn: sqlite3.Connection, domain: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM domain_scores WHERE domain = ?", (domain,)
    ).fetchone()
    return dict(row) if row else None


def cmd_score(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    if args.tier:
        # Manual set
        domain = args.domain.lower()
        conn.execute(
            "INSERT OR REPLACE INTO domain_scores(domain, tier, reason, set_by, set_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (domain, args.tier, args.reason or "manual override", "manual", today_iso()),
        )
        conn.commit()
        conn.close()
        print(f"Set {domain} -> {args.tier} ({args.reason or 'manual override'})")
        return 0
    # Read
    # Allow URL or bare domain
    target = args.domain
    if "://" in target:
        target = etld1(target)
    target = target.lower()
    row = lookup_domain(conn, target)
    if row:
        print(f"{target}  {row['tier']}  ({row['set_by']}, {row['set_date']})  {row['reason'] or ''}")
        conn.close()
        return 0
    # Try rules
    rule = _score_domain_by_rule(target)
    if rule:
        tier, reason = rule
        conn.execute(
            "INSERT INTO domain_scores(domain, tier, reason, set_by, set_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (target, tier, reason, "rule", today_iso()),
        )
        conn.commit()
        print(f"{target}  {tier}  (rule: {reason})")
        conn.close()
        return 0
    print(f"{target}  (unknown, flag for LLM review)")
    conn.close()
    return 0


# ---------- verify ----------

OPENALEX_BASE = "https://api.openalex.org/works"
ARXIV_API = "http://export.arxiv.org/api/query"
_ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(.+)$", re.IGNORECASE)


def _arxiv_check(arxiv_id: str) -> dict:
    """Query the arXiv API for a paper by its ID. Authoritative for arxiv sources."""
    try:
        url = f"{ARXIV_API}?id_list={urllib.parse.quote(arxiv_id)}&max_results=1"
        req = urllib.request.Request(url, headers={"User-Agent": "research-plugin/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        return {"found": False, "error": str(e), "source": "arxiv"}
    # Minimal parse: look for <entry>...<title>...</title>...<published>YYYY-...</published>
    if "<entry>" not in body:
        return {"found": False, "source": "arxiv"}
    title_m = re.search(r"<title>([^<]+)</title>", body.split("<entry>", 1)[1])
    year_m = re.search(r"<published>(\d{4})", body.split("<entry>", 1)[1])
    title = title_m.group(1).strip() if title_m else None
    year = int(year_m.group(1)) if year_m else None
    return {"found": True, "title": title, "year": year, "source": "arxiv",
            "openalex_id": f"arxiv:{arxiv_id}"}


def _title_similarity(a: str, b: str) -> float:
    """Rough title overlap: Jaccard on lowercased word sets, ignoring short words."""
    def toks(s: str) -> set[str]:
        return {w for w in re.findall(r"\w+", (s or "").lower()) if len(w) > 3}
    sa, sb = toks(a), toks(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(len(sa | sb), 1)


def _openalex_check(doi: str | None, title: str | None) -> dict:
    """Return {found, year, title, openalex_id, source, error?}.
    For arxiv DOIs, route to arxiv API (more reliable than OpenAlex's arxiv coverage)."""
    # Prefer arxiv API for arxiv DOIs
    if doi:
        m = _ARXIV_DOI_RE.match(doi)
        if m:
            return _arxiv_check(m.group(1))

    q = {}
    if doi:
        q["filter"] = f"doi:{doi}"
    elif title:
        q["search"] = title
    else:
        return {"found": False, "error": "no doi or title", "source": "openalex"}
    q["per-page"] = "1"
    q["mailto"] = "research-plugin@local"
    url = f"{OPENALEX_BASE}?{urllib.parse.urlencode(q)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "research-plugin/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        return {"found": False, "error": str(e), "source": "openalex"}
    results = data.get("results", [])
    if not results:
        return {"found": False, "source": "openalex"}
    w = results[0]
    return {
        "found": True,
        "year": w.get("publication_year"),
        "title": w.get("title"),
        "openalex_id": w.get("id"),
        "source": "openalex",
    }


# Require the number NOT to be preceded by a letter or digit (excludes "GSM8K" etc.)
# and NOT be followed by a letter-unit that isn't in our whitelist (excludes "540B").
_NUM_RE = re.compile(
    r"(?<![A-Za-z\d])(-?\d+(?:\.\d+)?)\s*(%|ms|s|x|×|gb|mb|kb|tb|hz|khz|mhz|ghz)?(?![A-Za-z])",
    re.IGNORECASE,
)


def _parse_number_with_unit(s: str) -> list[tuple[float, str]]:
    out = []
    for m in _NUM_RE.finditer(s):
        val = float(m.group(1))
        unit = (m.group(2) or "").lower().replace("×", "x")
        out.append((val, unit))
    return out


def _fts_retrieve(slug: str, query: str, k: int = 5) -> list[str]:
    """Return top-k Raw chunks for `slug` matching `query`."""
    conn = db_connect()
    row = conn.execute("SELECT raw FROM entries WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    if not row or not row["raw"]:
        return []
    # Chunk by paragraph
    chunks = [c.strip() for c in re.split(r"\n\n+", row["raw"]) if c.strip()]
    # Score chunks by naive keyword overlap (FTS5 on a subset is overkill;
    # this is good enough for verification-time retrieval).
    q_terms = set(re.findall(r"\w+", query.lower()))
    scored = []
    for c in chunks:
        c_terms = set(re.findall(r"\w+", c.lower()))
        score = len(q_terms & c_terms)
        if score > 0:
            scored.append((score, c))
    scored.sort(reverse=True)
    return [c for _, c in scored[:k]]


def _verify_numeric(atom: dict[str, Any], slug: str) -> dict[str, Any]:
    """Check if claim's numbers appear in retrieved Raw chunks (± tolerance)."""
    chunks = _fts_retrieve(slug, atom["claim"], k=5)
    claim_nums = _parse_number_with_unit(atom["claim"])
    if not claim_nums:
        return {"verdict": "inconclusive", "evidence": "no numbers parsed from claim", "confidence": "❓"}
    if not chunks:
        return {"verdict": "inconclusive", "evidence": "no supporting raw chunks found", "confidence": "❓"}
    matches = []
    for val, unit in claim_nums:
        matched_this_val = False
        for c in chunks:
            if matched_this_val:
                break
            chunk_nums = _parse_number_with_unit(c)
            for cv, cu in chunk_nums:
                # Units must match exactly (prevents spurious unitless matches)
                if unit != cu:
                    continue
                # Tolerance: 1% relative, or 0.1 absolute, whichever is larger
                tol = max(abs(val) * 0.01, 0.1)
                if abs(val - cv) <= tol:
                    matches.append({"claim": f"{val}{unit}", "source": f"{cv}{cu}",
                                    "chunk_preview": c[:120]})
                    matched_this_val = True
                    break
    if len(matches) == len(claim_nums):
        return {"verdict": "passed", "evidence": matches, "confidence": "✅"}
    if matches:
        return {"verdict": "inconclusive", "evidence": {"matched": matches, "total": len(claim_nums)}, "confidence": "⚠️"}
    return {"verdict": "failed", "evidence": f"no numeric match in {len(chunks)} chunks", "confidence": "❌"}


def _verify_symbolic(atom: dict[str, Any], _slug: str) -> dict[str, Any]:
    try:
        sympy = importlib.import_module("sympy")
    except ImportError:
        return {"verdict": "inconclusive", "evidence": "sympy not installed", "confidence": "❓"}
    # Expect claim of form "lhs == rhs" or parseable equation
    claim = atom["claim"]
    m = re.search(r"(.+?)\s*(?:=|==|equals)\s*(.+)", claim)
    if not m:
        return {"verdict": "inconclusive", "evidence": "could not parse equation", "confidence": "❓"}
    try:
        lhs = sympy.sympify(m.group(1).strip())
        rhs = sympy.sympify(m.group(2).strip())
        diff = sympy.simplify(lhs - rhs)
        if diff == 0:
            return {"verdict": "passed", "evidence": f"{lhs} = {rhs} verified", "confidence": "✅"}
        return {"verdict": "failed", "evidence": f"difference: {diff}", "confidence": "❌"}
    except Exception as e:
        return {"verdict": "inconclusive", "evidence": f"sympy error: {e}", "confidence": "❓"}


def _verify_citation(atom: dict[str, Any], _slug: str) -> dict[str, Any]:
    """Check a citation via arXiv (for arxiv DOIs) or OpenAlex.
    Requires returned title to overlap with expected title if provided (guards
    against API false-positives like OpenAlex sometimes returning unrelated works)."""
    doi = atom.get("doi")
    expected_title = atom.get("title") or atom["claim"]
    result = _openalex_check(doi, expected_title)
    if not result.get("found"):
        err = result.get("error", f"not found in {result.get('source', 'lookup')}")
        return {"verdict": "failed", "evidence": err, "confidence": "❌"}
    returned_title = result.get("title") or ""
    sim = _title_similarity(expected_title, returned_title)
    # If caller provided a specific title to match, require meaningful overlap.
    if atom.get("title") and sim < 0.2:
        return {
            "verdict": "failed",
            "evidence": (
                f"Title mismatch: expected '{expected_title}' but {result.get('source')} "
                f"returned '{returned_title}' (similarity {sim:.2f})"
            ),
            "confidence": "❌",
        }
    return {
        "verdict": "passed",
        "evidence": f"Found via {result.get('source')}: {returned_title} ({result.get('year')}) — {result.get('openalex_id')}",
        "confidence": "✅",
    }


def _verify_code(atom: dict[str, Any], _slug: str) -> dict[str, Any]:
    """Run code sandbox-ish. v0.3: Docker if available, else subprocess with limits."""
    code = atom.get("code") or ""
    if not code:
        return {"verdict": "inconclusive", "evidence": "no code provided", "confidence": "❓"}
    docker = shutil.which("docker")
    if docker:
        try:
            proc = subprocess.run(
                [docker, "run", "--rm", "-i", "--network=none", "--memory=256m",
                 "--cpus=1", "python:3.12-slim", "python", "-c", code],
                capture_output=True, text=True, timeout=30,
            )
        except subprocess.TimeoutExpired:
            return {"verdict": "failed", "evidence": "timeout", "confidence": "❌"}
    else:
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=10,
            )
        except subprocess.TimeoutExpired:
            return {"verdict": "failed", "evidence": "timeout", "confidence": "❌"}
    if proc.returncode == 0:
        return {"verdict": "passed", "evidence": proc.stdout.strip()[:500], "confidence": "✅"}
    return {"verdict": "failed", "evidence": proc.stderr.strip()[:500], "confidence": "❌"}


VERIFIERS = {
    "numeric": _verify_numeric,
    "symbolic": _verify_symbolic,
    "citation": _verify_citation,
    "code": _verify_code,
}


def cmd_verify(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    row = conn.execute("SELECT path FROM entries WHERE slug = ?", (args.slug,)).fetchone()
    if not row:
        print(f"ERROR: no entry: {args.slug}", file=sys.stderr)
        conn.close()
        return 2
    entry_path = Path(row["path"])
    conn.close()

    atoms_path = args.atoms or str(entry_path.parent / f"{args.slug}.atoms.json")
    if not Path(atoms_path).exists():
        print(f"ERROR: no atoms file at {atoms_path}.", file=sys.stderr)
        print("Extract atoms first (the host agent writes a JSON list of "
              "{atom_id, type, claim, doi?, code?} to that path).", file=sys.stderr)
        return 2
    atoms = json.loads(Path(atoms_path).read_text())
    if args.atom:
        atoms = [a for a in atoms if a["atom_id"] == args.atom]
        if not atoms:
            print(f"ERROR: atom {args.atom} not in {atoms_path}", file=sys.stderr)
            return 2

    log_dir = index_path("verifier-log", args.slug)
    log_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for atom in atoms:
        verifier = VERIFIERS.get(atom.get("type"))
        if not verifier:
            result = {"verdict": "inconclusive", "evidence": f"unknown type: {atom.get('type')}", "confidence": "❓"}
        elif args.dry_run:
            result = {"verdict": "dry-run", "evidence": "skipped"}
        else:
            result = verifier(atom, args.slug)
        entry = {
            "atom_id": atom["atom_id"],
            "type": atom.get("type"),
            "claim": atom.get("claim"),
            "timestamp": now_iso(),
            **result,
        }
        (log_dir / f"{atom['atom_id']}.json").write_text(json.dumps(entry, indent=2, default=str))
        results.append(entry)
        print(f"  [{entry['verdict']:12s}] {atom['atom_id']}  ({atom.get('type')})  {atom.get('claim', '')[:80]}")

    # Roll up into entry frontmatter
    if not args.dry_run and not args.atom:
        passed = sum(1 for r in results if r["verdict"] == "passed")
        failed = sum(1 for r in results if r["verdict"] == "failed")
        inconclusive = sum(1 for r in results if r["verdict"] == "inconclusive")
        text = entry_path.read_text()
        fm, body = parse_frontmatter(text)
        fm["verification"] = {
            "run": now_iso(),
            "atoms": len(results),
            "passed": passed,
            "failed": failed,
            "inconclusive": inconclusive,
        }
        # Update confidence based on verification + corroboration
        corrob = int(fm.get("corroboration", 0))
        pass_rate = passed / max(len(results), 1)
        if corrob >= 2 and pass_rate >= 0.8:
            fm["confidence"] = "verified"
        elif corrob >= 1 and pass_rate >= 0.5:
            fm["confidence"] = "partial"
        else:
            fm["confidence"] = "inferred"
        entry_path.write_text(dump_frontmatter(fm, body))
        # Re-ingest to DB
        _reingest(entry_path)

    print(f"Verified {len(results)} atoms. Artifacts in {log_dir}")
    return 0


def _normalise_entry_frontmatter(fm: dict) -> dict:
    """Apply DB-safe defaults without rewriting the source markdown."""
    if not fm.get("slug"):
        raise ValueError("entry missing slug in frontmatter")
    out = dict(fm)
    out.setdefault("created", today_iso())
    out.setdefault("reviewed", today_iso())
    out.setdefault("status", "evergreen")
    out.setdefault("workflow", "general")
    out.setdefault("confidence", "inferred")
    out.setdefault("corroboration", 0)
    for list_key, default in [
        ("topics", [top_level_topic(out["slug"])]),
        ("projects", []),
        ("tags", []),
        ("sources", []),
        ("related", []),
        ("inbound", []),
    ]:
        if out.get(list_key) is None:
            out[list_key] = default
        elif not isinstance(out.get(list_key), list):
            out[list_key] = [out[list_key]]
    return out


def _reingest(entry_path: Path) -> str:
    """Re-read an entry file and upsert into DB without touching filesystem."""
    text = entry_path.read_text()
    fm, body = parse_frontmatter(text)
    fm = _normalise_entry_frontmatter(fm)
    sections = split_sections(body)
    verification = fm.get("verification") or {}
    row = (
        fm["slug"],
        str(entry_path.resolve()),
        fm.get("title", ""),
        json.dumps(fm.get("topics", [])),
        json.dumps(fm.get("projects", [])),
        json.dumps(fm.get("tags", [])),
        json.dumps(fm.get("sources", [])),
        fm.get("status", "evergreen"),
        fm.get("workflow", "general"),
        fm.get("created", today_iso()),
        fm.get("reviewed", today_iso()),
        fm.get("topic_velocity", "medium"),
        fm.get("confidence", "inferred"),
        int(fm.get("corroboration", 0) or 0),
        sections["tldr"],
        sections["notes"],
        sections["raw"],
        json.dumps(verification),
        json.dumps(fm.get("inbound", [])),
    )
    conn = db_connect()
    conn.execute(
        """
        INSERT INTO entries
          (slug, path, title, topics, projects, tags, sources, status, workflow,
           created, reviewed, topic_velocity, confidence, corroboration,
           tldr, notes, raw, verification, inbound)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
          path=excluded.path,
          title=excluded.title,
          topics=excluded.topics,
          projects=excluded.projects,
          tags=excluded.tags,
          sources=excluded.sources,
          status=excluded.status,
          workflow=excluded.workflow,
          created=excluded.created,
          reviewed=excluded.reviewed,
          topic_velocity=excluded.topic_velocity,
          confidence=excluded.confidence,
          corroboration=excluded.corroboration,
          tldr=excluded.tldr,
          notes=excluded.notes,
          raw=excluded.raw,
          verification=excluded.verification,
          inbound=excluded.inbound
        """,
        row,
    )
    conn.commit()
    conn.close()
    return fm["slug"]


def _topic_entry_paths() -> list[Path]:
    """Return canonical topic markdown paths under the configured content root."""
    topics_dir = content_path("topics")
    if not topics_dir.exists():
        return []
    return sorted(p for p in topics_dir.glob("*/*.md") if p.is_file())


def cmd_sync(args: argparse.Namespace) -> int:
    """Synchronize SQLite from canonical topic markdown without modifying entries."""
    ensure_layout()
    ensure_db()
    seen: list[str] = []
    seen_paths: dict[str, Path] = {}
    skipped: list[tuple[Path, str]] = []
    duplicates: list[tuple[str, Path, Path]] = []
    redirects = 0
    for entry_path in _topic_entry_paths():
        try:
            fm, _body = parse_frontmatter(entry_path.read_text(), fatal=False)
            slug = fm.get("slug")
            if not slug:
                if fm.get("status") == "archived" and fm.get("redirect"):
                    redirects += 1
                    continue
                raise ValueError("entry missing slug in frontmatter")
            if slug in seen_paths:
                duplicates.append((slug, seen_paths[slug], entry_path))
                continue
            seen.append(_reingest(entry_path))
            seen_paths[slug] = entry_path
        except ValueError as e:
            skipped.append((entry_path, str(e)))
        except (OSError, KeyError, yaml.YAMLError) as e:
            skipped.append((entry_path, str(e)))

    pruned = 0
    if args.prune_missing:
        conn = db_connect()
        if seen:
            placeholders = ",".join("?" for _ in seen)
            pruned = conn.execute(
                f"DELETE FROM entries WHERE slug NOT IN ({placeholders})",  # nosec: parameterized IN-clause, values bound as params
                seen,
            ).rowcount
        else:
            print("WARN: no topic entries found; refusing to prune all DB rows", file=sys.stderr)
        conn.commit()
        conn.close()

    if not args.no_index:
        # Reuse the full index flow so indexes, managed symlinks, and linked projects refresh.
        cmd_index(argparse.Namespace())

    print(f"Synced topic entries: {len(set(seen))}")
    if redirects:
        print(f"Ignored redirect stubs: {redirects}")
    if duplicates:
        print(f"Duplicate slugs: {len(duplicates)}")
        for slug, first, duplicate in duplicates[:10]:
            print(f"  - {slug}: kept {first}; duplicate {duplicate}")
        if len(duplicates) > 10:
            print(f"  ... {len(duplicates) - 10} more")
    if pruned:
        print(f"Pruned missing DB rows: {pruned}")
    if skipped:
        print(f"Skipped files: {len(skipped)}")
        for path, reason in skipped[:10]:
            print(f"  - {path}: {reason}")
        if len(skipped) > 10:
            print(f"  ... {len(skipped) - 10} more")
    return 0


# ---------- quantitative analysis ----------

ANALYSIS_EXTS = {".csv", ".tsv", ".json", ".jsonl", ".sqlite", ".sqlite3", ".db"}


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _analysis_runs_dir() -> Path:
    p = index_path("analysis-runs")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _analysis_input_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".csv":
        return "csv"
    if ext == ".tsv":
        return "tsv"
    if ext in (".json", ".jsonl"):
        return ext[1:]
    if ext in (".sqlite", ".sqlite3", ".db"):
        return "sqlite"
    return "unknown"


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text:
        return None
    # Remove common visual separators but do not guess at percentages/currency.
    text = text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _sample_rows(rows: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    return rows[: max(n, 0)]


def _summarize_table_rows(rows: list[dict[str, Any]], sample_size: int = 5) -> dict[str, Any]:
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                columns.append(key)
                seen.add(key)

    profile_cols: list[dict[str, Any]] = []
    for col in columns:
        values = [row.get(col) for row in rows]
        blanks = sum(1 for v in values if v is None or str(v).strip() == "")
        decimals: list[Decimal] = []
        for v in values:
            d = _decimal_or_none(v)
            if d is not None:
                decimals.append(d)
        nonblank = max(len(values) - blanks, 0)
        numeric_count = len(decimals)
        inferred_type = "number" if nonblank and numeric_count == nonblank else "mixed"
        if nonblank and numeric_count == 0:
            inferred_type = "text"
        if not nonblank:
            inferred_type = "empty"
        distinct_values = {str(v) for v in values if v is not None and str(v).strip() != ""}
        col_profile: dict[str, Any] = {
            "name": col,
            "inferred_type": inferred_type,
            "nonblank": nonblank,
            "blank": blanks,
            "distinct": len(distinct_values),
        }
        if decimals:
            total = sum(decimals, Decimal("0"))
            col_profile["numeric"] = {
                "count": numeric_count,
                "min": str(min(decimals)),
                "max": str(max(decimals)),
                "mean": str(total / Decimal(numeric_count)),
            }
        if 0 < len(distinct_values) <= 10:
            col_profile["values"] = sorted(distinct_values)[:10]
        profile_cols.append(col_profile)

    return {
        "row_count": len(rows),
        "columns": profile_cols,
        "sample_rows": _sample_rows(rows, sample_size),
    }


def _read_delimited_rows(path: Path, delimiter: str) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return [dict(row) for row in reader]


def _read_json_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            rows.append(obj if isinstance(obj, dict) else {"value": obj})
        return rows
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if isinstance(data, list):
        return [x if isinstance(x, dict) else {"value": x} for x in data]
    if isinstance(data, dict):
        for key in ("rows", "data", "items", "records"):
            maybe = data.get(key)
            if isinstance(maybe, list):
                return [x if isinstance(x, dict) else {"value": x} for x in maybe]
        return [data]
    return [{"value": data}]


def _profile_table_file(path: Path, sample_size: int = 5) -> dict[str, Any]:
    input_type = _analysis_input_type(path)
    if input_type == "csv":
        rows = _read_delimited_rows(path, ",")
    elif input_type == "tsv":
        rows = _read_delimited_rows(path, "\t")
    elif input_type in ("json", "jsonl"):
        rows = _read_json_rows(path)
    else:
        raise ValueError(f"unsupported table input type: {path.suffix}")
    profile = _summarize_table_rows(rows, sample_size=sample_size)
    profile.update({
        "path": str(path),
        "input_type": input_type,
        "sha256": _file_sha256(path),
    })
    return profile


def _profile_sqlite_db(path: Path, sample_size: int = 5) -> dict[str, Any]:
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    tables = [
        dict(r) for r in conn.execute(
            "SELECT name, type, sql FROM sqlite_master "
            "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    out_tables: list[dict[str, Any]] = []
    for table in tables:
        name = table["name"]
        quoted = '"' + name.replace('"', '""') + '"'
        row_count = conn.execute(f"SELECT COUNT(*) AS n FROM {quoted}").fetchone()["n"]  # nosec: identifier from sqlite_master, quote-escaped
        cols = [dict(r) for r in conn.execute(f"PRAGMA table_info({quoted})").fetchall()]
        fks = [dict(r) for r in conn.execute(f"PRAGMA foreign_key_list({quoted})").fetchall()]
        indexes = [dict(r) for r in conn.execute(f"PRAGMA index_list({quoted})").fetchall()]
        sample = [dict(r) for r in conn.execute(f"SELECT * FROM {quoted} LIMIT ?", (sample_size,)).fetchall()]  # nosec: identifier from sqlite_master, quote-escaped
        table_profile = {
            "name": name,
            "type": table["type"],
            "row_count": row_count,
            "schema_sql": table.get("sql"),
            "columns": [
                {
                    "name": c.get("name"),
                    "declared_type": c.get("type"),
                    "notnull": bool(c.get("notnull")),
                    "default": c.get("dflt_value"),
                    "primary_key_position": c.get("pk"),
                }
                for c in cols
            ],
            "foreign_keys": fks,
            "indexes": indexes,
            "sample_rows": sample,
        }
        if sample:
            table_profile["sample_profile"] = _summarize_table_rows(sample, sample_size=sample_size)
        out_tables.append(table_profile)
    conn.close()
    return {
        "path": str(path),
        "input_type": "sqlite",
        "sha256": _file_sha256(path),
        "tables": out_tables,
    }


def _profile_input(path: Path, sample_size: int = 5) -> dict[str, Any]:
    input_type = _analysis_input_type(path)
    if input_type == "sqlite":
        return _profile_sqlite_db(path, sample_size=sample_size)
    if input_type in ("csv", "tsv", "json", "jsonl"):
        return _profile_table_file(path, sample_size=sample_size)
    raise ValueError(f"unsupported input extension: {path.suffix}")


def _certainty_from_profile(profile: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    input_type = profile.get("input_type")
    if input_type == "sqlite":
        tables = profile.get("tables") or []
        if not tables:
            return "Low", ["database has no user tables/views"]
        no_rows = [t["name"] for t in tables if int(t.get("row_count") or 0) == 0]
        no_pk = [
            t["name"] for t in tables
            if t.get("type") == "table" and not any(c.get("primary_key_position") for c in t.get("columns", []))
        ]
        if no_rows:
            reasons.append(f"empty tables/views: {', '.join(no_rows[:5])}")
        if no_pk:
            reasons.append(f"tables without primary keys: {', '.join(no_pk[:5])}")
        if reasons:
            return "Medium", reasons
        return "High", ["structured SQLite input with table schemas and row counts"]
    row_count = int(profile.get("row_count") or 0)
    columns = profile.get("columns") or []
    if row_count == 0:
        return "Low", ["input has zero rows"]
    if not columns:
        return "Low", ["input has no detected columns"]
    blank_heavy = [
        c["name"] for c in columns
        if row_count and (int(c.get("blank") or 0) / max(row_count, 1)) > 0.2
    ]
    mixed_cols = [c["name"] for c in columns if c.get("inferred_type") == "mixed"]
    if blank_heavy or mixed_cols:
        if blank_heavy:
            reasons.append(f">20% blanks in: {', '.join(blank_heavy[:5])}")
        if mixed_cols:
            reasons.append(f"mixed type columns: {', '.join(mixed_cols[:5])}")
        return "Medium", reasons
    return "High", ["structured table input with detected columns and no major profile warnings"]


def _analysis_script_text() -> str:
    """Return the generated stdlib-only analysis script."""
    return r'''#!/usr/bin/env python3
"""Generated by research.py analyze-plan.

Self-contained stdlib analysis runner. It reads analysis-plan.json, validates
declared inputs by sha256, profiles the inputs, and writes results.json plus
audit.md. It intentionally does not install packages, download code, or call
network APIs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                columns.append(key)
    out_cols: list[dict[str, Any]] = []
    for col in columns:
        vals = [row.get(col) for row in rows]
        blanks = sum(1 for v in vals if v is None or str(v).strip() == "")
        nums = [d for d in (decimal_or_none(v) for v in vals) if d is not None]
        nonblank = len(vals) - blanks
        distinct = {str(v) for v in vals if v is not None and str(v).strip() != ""}
        inferred = "number" if nonblank and len(nums) == nonblank else "mixed"
        if nonblank and not nums:
            inferred = "text"
        if not nonblank:
            inferred = "empty"
        item: dict[str, Any] = {
            "name": col,
            "inferred_type": inferred,
            "nonblank": nonblank,
            "blank": blanks,
            "distinct": len(distinct),
        }
        if nums:
            item["numeric"] = {
                "count": len(nums),
                "min": str(min(nums)),
                "max": str(max(nums)),
                "sum": str(sum(nums, Decimal("0"))),
                "mean": str(sum(nums, Decimal("0")) / Decimal(len(nums))),
            }
        out_cols.append(item)
    return {"row_count": len(rows), "columns": out_cols, "sample_rows": rows[:5]}


def read_rows(path: Path, input_type: str) -> list[dict[str, Any]]:
    if input_type in ("csv", "tsv"):
        delim = "\t" if input_type == "tsv" else ","
        with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
            return [dict(r) for r in csv.DictReader(f, delimiter=delim)]
    if input_type == "jsonl":
        rows = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                obj = json.loads(line)
                rows.append(obj if isinstance(obj, dict) else {"value": obj})
        return rows
    if input_type == "json":
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if isinstance(data, list):
            return [x if isinstance(x, dict) else {"value": x} for x in data]
        if isinstance(data, dict):
            for key in ("rows", "data", "items", "records"):
                maybe = data.get(key)
                if isinstance(maybe, list):
                    return [x if isinstance(x, dict) else {"value": x} for x in maybe]
            return [data]
        return [{"value": data}]
    raise ValueError(f"unsupported table input type: {input_type}")


def profile_sqlite(path: Path) -> dict[str, Any]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    tables = [dict(r) for r in conn.execute(
        "SELECT name, type, sql FROM sqlite_master WHERE type IN ('table', 'view') "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    out = []
    for table in tables:
        name = table["name"]
        quoted = '"' + name.replace('"', '""') + '"'
        row_count = conn.execute(f"SELECT COUNT(*) AS n FROM {quoted}").fetchone()["n"]  # nosec: identifier from sqlite_master, quote-escaped
        cols = [dict(r) for r in conn.execute(f"PRAGMA table_info({quoted})")]
        fks = [dict(r) for r in conn.execute(f"PRAGMA foreign_key_list({quoted})")]
        indexes = [dict(r) for r in conn.execute(f"PRAGMA index_list({quoted})")]
        sample = [dict(r) for r in conn.execute(f"SELECT * FROM {quoted} LIMIT 5")]  # nosec: identifier from sqlite_master, quote-escaped
        out.append({
            "name": name,
            "type": table["type"],
            "row_count": row_count,
            "schema_sql": table.get("sql"),
            "columns": cols,
            "foreign_keys": fks,
            "indexes": indexes,
            "sample_rows": sample,
        })
    conn.close()
    return {"tables": out}


def certainty(profile: dict[str, Any], input_type: str) -> tuple[str, list[str]]:
    if input_type == "sqlite":
        tables = profile.get("tables") or []
        if not tables:
            return "Low", ["database has no user tables/views"]
        no_pk = [
            t["name"] for t in tables
            if t.get("type") == "table" and not any(c.get("pk") for c in t.get("columns", []))
        ]
        if no_pk:
            return "Medium", [f"tables without primary keys: {', '.join(no_pk[:5])}"]
        return "High", ["structured SQLite input; schema and row counts profiled"]
    rows = int(profile.get("row_count") or 0)
    if rows == 0:
        return "Low", ["input has zero rows"]
    cols = profile.get("columns") or []
    mixed = [c["name"] for c in cols if c.get("inferred_type") == "mixed"]
    if mixed:
        return "Medium", [f"mixed type columns: {', '.join(mixed[:5])}"]
    return "High", ["structured table input; deterministic stdlib profiling completed"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    plan_path = Path(args.plan).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = json.loads(plan_path.read_text())
    findings = []
    validations = []
    for inp in plan.get("inputs", []):
        path = Path(inp["path"]).resolve()
        actual_sha = file_sha256(path)
        expected_sha = inp.get("sha256")
        validations.append({
            "name": f"sha256:{path.name}",
            "passed": expected_sha == actual_sha,
            "expected": expected_sha,
            "actual": actual_sha,
        })
        input_type = inp.get("input_type")
        if input_type == "sqlite":
            profile = profile_sqlite(path)
        else:
            rows = read_rows(path, input_type)
            profile = summarize_rows(rows)
        level, reasons = certainty(profile, input_type)
        findings.append({
            "input": str(path),
            "input_type": input_type,
            "profile": profile,
            "certainty": level,
            "certainty_reasons": reasons,
        })
    all_valid = all(v["passed"] for v in validations)
    result = {
        "question": plan.get("question"),
        "status": "passed" if all_valid else "validation_failed",
        "validations": validations,
        "findings": findings,
        "limitations": plan.get("limitations", []),
    }
    (out_dir / "results.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    lines = [
        "# Analysis Audit\n\n",
        f"Question: {plan.get('question') or 'unspecified'}\n\n",
        f"Status: {result['status']}\n\n",
        "## Findings\n\n",
    ]
    for f in findings:
        lines.append(f"- `{f['input']}` ({f['input_type']}): certainty **{f['certainty']}** — {', '.join(f['certainty_reasons'])}\n")
    lines.append("\n## Validations\n\n")
    for v in validations:
        lines.append(f"- {v['name']}: {'passed' if v['passed'] else 'failed'}\n")
    if plan.get("limitations"):
        lines.append("\n## Limitations\n\n")
        for item in plan["limitations"]:
            lines.append(f"- {item}\n")
    (out_dir / "audit.md").write_text("".join(lines))
    print(out_dir / "results.json")
    print(out_dir / "audit.md")
    return 0 if all_valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
'''


def cmd_table_profile(args: argparse.Namespace) -> int:
    path = Path(args.input).expanduser().resolve()
    if not path.exists() or not path.is_file():
        print(f"ERROR: table input not found: {path}", file=sys.stderr)
        return 2
    try:
        profile = _profile_table_file(path, sample_size=args.sample)
    except (OSError, json.JSONDecodeError, csv.Error, ValueError) as e:
        print(f"ERROR: could not profile table: {e}", file=sys.stderr)
        return 2
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(profile, indent=2, default=str) + "\n")
        print(out)
    else:
        print(json.dumps(profile, indent=2, default=str))
    return 0


def cmd_db_profile(args: argparse.Namespace) -> int:
    path = Path(args.db).expanduser().resolve()
    if not path.exists() or not path.is_file():
        print(f"ERROR: database not found: {path}", file=sys.stderr)
        return 2
    try:
        profile = _profile_sqlite_db(path, sample_size=args.sample)
    except sqlite3.Error as e:
        print(f"ERROR: could not profile SQLite database: {e}", file=sys.stderr)
        return 2
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(profile, indent=2, default=str) + "\n")
        print(out)
    else:
        print(json.dumps(profile, indent=2, default=str))
    return 0


def cmd_analyze_plan(args: argparse.Namespace) -> int:
    ensure_layout()
    inputs = [Path(p).expanduser().resolve() for p in args.input]
    missing = [str(p) for p in inputs if not p.exists() or not p.is_file()]
    if missing:
        print(f"ERROR: missing input(s): {', '.join(missing)}", file=sys.stderr)
        return 2
    run_name = args.name or _slugify(args.question or "analysis")
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else _analysis_runs_dir() / f"{stamp}-{run_name}"
    run_dir.mkdir(parents=True, exist_ok=True)

    profiled_inputs: list[dict[str, Any]] = []
    limitations = [
        "Generated script performs deterministic profiling only until metric formulas or SQL are added to the plan.",
        "Certainty reflects input structure and validation status, not external source credibility.",
    ]
    for path in inputs:
        try:
            profile = _profile_input(path, sample_size=args.sample)
        except (OSError, json.JSONDecodeError, csv.Error, sqlite3.Error, ValueError) as e:
            print(f"ERROR: could not profile {path}: {e}", file=sys.stderr)
            return 2
        level, reasons = _certainty_from_profile(profile)
        profiled_inputs.append({
            "path": str(path),
            "input_type": profile["input_type"],
            "sha256": profile["sha256"],
            "profile_path": str(run_dir / f"{path.stem}.profile.json"),
            "profile": profile,
            "initial_certainty": level,
            "certainty_reasons": reasons,
        })
        Path(profiled_inputs[-1]["profile_path"]).write_text(json.dumps(profile, indent=2, default=str) + "\n")

    plan = {
        "question": args.question,
        "created": now_iso(),
        "workflow": "quantitative-analysis",
        "inputs": [
            {
                "path": p["path"],
                "input_type": p["input_type"],
                "sha256": p["sha256"],
                "profile_path": p["profile_path"],
                "initial_certainty": p["initial_certainty"],
                "certainty_reasons": p["certainty_reasons"],
            }
            for p in profiled_inputs
        ],
        "metrics": [],
        "validations": [
            "input sha256 must match the profiled file",
            "row counts and schemas should be reviewed before interpreting calculations",
        ],
        "certainty_rubric": {
            "High": "structured input, known schema, deterministic calculation, validations pass",
            "Medium": "some assumptions or partial validation, but data is usable",
            "Low": "ambiguous grain/schema, extraction risk, failed validation, or missing critical data",
        },
        "limitations": limitations,
        "script": str(run_dir / "analysis.py"),
        "plan_json": str(run_dir / "analysis-plan.json"),
    }
    yaml_path = run_dir / "analysis-plan.yaml"
    json_path = run_dir / "analysis-plan.json"
    script_path = run_dir / "analysis.py"
    script_path.write_text(_analysis_script_text())
    script_path.chmod(0o700)
    plan["script_sha256"] = _file_sha256(script_path)
    yaml_path.write_text(yaml.safe_dump(plan, sort_keys=False, allow_unicode=True))
    json_path.write_text(json.dumps(plan, indent=2, default=str) + "\n")

    print(f"Analysis plan: {yaml_path}")
    print(f"Plan JSON:     {json_path}")
    print(f"Script:        {script_path}")
    print("Next: python research.py analyze-run --plan " + str(yaml_path))
    return 0


def cmd_analyze_run(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan).expanduser().resolve()
    if not plan_path.exists():
        print(f"ERROR: plan not found: {plan_path}", file=sys.stderr)
        return 2
    try:
        plan = yaml.safe_load(plan_path.read_text()) or {}
    except yaml.YAMLError as e:
        print(f"ERROR: invalid plan YAML: {e}", file=sys.stderr)
        return 2
    run_dir = plan_path.parent
    script_path = Path(plan.get("script") or run_dir / "analysis.py").expanduser().resolve()
    json_path = Path(plan.get("plan_json") or run_dir / "analysis-plan.json").expanduser().resolve()
    if not script_path.exists():
        print(f"ERROR: analysis script not found: {script_path}", file=sys.stderr)
        return 2
    expected_script_hash = plan.get("script_sha256")
    if expected_script_hash and not args.allow_modified_script:
        actual_script_hash = _file_sha256(script_path)
        if actual_script_hash != expected_script_hash:
            print("ERROR: analysis script hash differs from analysis-plan.yaml.", file=sys.stderr)
            print(f"  Expected: {expected_script_hash}", file=sys.stderr)
            print(f"  Actual:   {actual_script_hash}", file=sys.stderr)
            print("Review the script, then rerun with --allow-modified-script if this edit is intentional.", file=sys.stderr)
            return 2
    if not json_path.exists():
        json_path.write_text(json.dumps(plan, indent=2, default=str) + "\n")
    proc = subprocess.run(
        [sys.executable, str(script_path), "--plan", str(json_path), "--out-dir", str(run_dir)],
        cwd=str(run_dir),
        capture_output=True,
        text=True,
        timeout=args.timeout,
    )
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        print(f"ERROR: analysis failed with exit code {proc.returncode}", file=sys.stderr)
        return proc.returncode
    print(f"Analysis artifacts: {run_dir}")
    return 0


# ---------- audit, sources, calculations, and run contracts ----------

TRUST_DIMENSIONS = {
    "citation_grounding",
    "uncertainty_calibration",
    "correction_behavior",
    "declared_opinion_bias_framing",
    "unsupported_absolute_language",
    "nuance",
    "discrepancy_history",
}


def cmd_source_record(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    path = Path(args.manifest).expanduser().resolve()
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: invalid source manifest: {exc}", file=sys.stderr)
        return 2
    if not isinstance(manifest, dict) or not manifest.get("url"):
        print("ERROR: source manifest requires an absolute url", file=sys.stderr)
        return 2
    if not manifest.get("content_hash") and not manifest.get("content_hash_unknown_reason"):
        print("ERROR: source manifest requires content_hash or content_hash_unknown_reason", file=sys.stderr)
        return 2
    try:
        _validate_hash_ref(manifest.get("content_hash"), "content_hash")
        _validate_hash_ref(manifest.get("normalized_hash"), "normalized_hash")
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not (manifest.get("published_at") or manifest.get("published") or manifest.get("published_at_unknown_reason")):
        print("ERROR: source manifest requires published_at or published_at_unknown_reason", file=sys.stderr)
        return 2
    if not (manifest.get("locator") or manifest.get("locator_unknown_reason")):
        print("ERROR: source manifest requires locator or locator_unknown_reason", file=sys.stderr)
        return 2
    actor = _actor_from_args(args)
    run_id = str(args.run_id or manifest.get("run_id") or os.environ.get("RESEARCH_RUN_ID") or _new_id("run"))
    entry_slug = str(args.entry_slug or manifest.get("entry_slug") or "")
    conn = db_connect()
    try:
        with conn:
            _ensure_run(conn, run_id, actor, objective="source capture")
            observations = _record_sources_for_entry(
                conn,
                sources=[manifest],
                run_id=run_id,
                entry_slug=entry_slug,
            )
            if not observations:
                raise ValueError("manifest URL could not be normalized")
            if entry_slug:
                _record_entry_graph(
                    conn,
                    slug=entry_slug,
                    title=entry_slug,
                    run_id=run_id,
                    observation_ids=observations,
                )
            _append_event(
                conn,
                event_type="source.observed",
                run_id=run_id,
                actor_type=actor["actor_type"],
                actor_id=actor["actor_id"],
                payload={"observation_id": observations[0], "entry_slug": entry_slug},
                actor_snapshot=actor,
            )
    except (ValueError, sqlite3.Error) as exc:
        print(f"ERROR: source record failed: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()
    print(json.dumps({"run_id": run_id, "observation_id": observations[0]}, indent=2))
    return 0


def _source_ledger_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT s.source_id, s.canonical_url, s.domain, s.source_kind, s.name,
               CASE WHEN MIN(o.captured_at)='0001-01-01T00:00:00Z'
                    THEN 'unknown' ELSE MIN(o.captured_at) END AS first_captured_at,
               CASE WHEN MAX(o.captured_at)='0001-01-01T00:00:00Z'
                    THEN 'unknown' ELSE MAX(o.captured_at) END AS last_captured_at,
               COUNT(DISTINCT o.observation_id) AS capture_count,
               COUNT(DISTINCT o.run_id) AS run_count,
               COUNT(DISTINCT NULLIF(o.entry_slug, '')) AS entry_count
        FROM sources s
        LEFT JOIN source_observations o ON o.source_id = s.source_id
        GROUP BY s.source_id
        ORDER BY last_captured_at DESC, s.canonical_url
        """
    ).fetchall()


def _write_source_indexes(conn: sqlite3.Connection) -> list[Path]:
    rows = _source_ledger_rows(conn)
    outputs: list[Path] = []
    ledger = content_path("SOURCE-LEDGER.md")
    lines = [
        "# Research Source Ledger\n\n",
        f"Generated: {now_iso()}\n\n",
        "| Source | Domain | First captured | Last captured | Runs | Entries |\n",
        "|---|---|---:|---:|---:|---:|\n",
    ]
    for row in rows:
        label = row["name"] or row["canonical_url"]
        lines.append(
            f"| [{label}]({row['canonical_url']}) | {row['domain']} | "
            f"{row['first_captured_at'] or ''} | {row['last_captured_at'] or ''} | "
            f"{row['run_count']} | {row['entry_count']} |\n"
        )
    ledger.write_text("".join(lines))
    outputs.append(ledger)

    projects: dict[str, list[sqlite3.Row]] = {}
    for row in conn.execute("SELECT slug, title, path, projects FROM entries ORDER BY title"):
        for project in json.loads(row["projects"] or "[]"):
            projects.setdefault(str(project), []).append(row)
    for project, entries in projects.items():
        project_dir = content_path("projects", project)
        project_dir.mkdir(parents=True, exist_ok=True)
        index = project_dir / "INDEX.md"
        project_lines = [f"# {project} research index\n\n", f"Generated: {now_iso()}\n\n"]
        for entry in entries:
            project_lines.append(f"- [{entry['title'] or entry['slug']}]({Path(entry['path']).name})\n")
        index.write_text("".join(project_lines))
        outputs.append(index)
    return outputs


def cmd_source_index(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    conn = db_connect()
    with conn:
        outputs = _write_source_indexes(conn)
    conn.close()
    for path in outputs:
        print(path)
    return 0


def cmd_legacy_source_import(args: argparse.Namespace) -> int:
    """Normalize historical entry source lists without inventing missing provenance."""
    ensure_layout()
    ensure_db()
    conn = db_connect()
    rows = conn.execute("SELECT slug, title, sources FROM entries ORDER BY slug").fetchall()
    planned_entries = 0
    planned_sources = 0
    imported_entries = 0
    imported_observations = 0
    skipped_sources = 0
    skipped_reasons: list[dict[str, str]] = []
    actor = {
        "actor_type": "migration",
        "actor_id": "legacy-source-import",
        "host": "unknown",
        "session_id": "unknown",
        "tool_version": "legacy-import-v1",
    }
    try:
        with conn:
            for row in rows:
                raw_sources = json.loads(row["sources"] or "[]")
                candidates: list[dict[str, Any]] = []
                for raw in raw_sources:
                    if not isinstance(raw, (str, dict)):
                        skipped_sources += 1
                        skipped_reasons.append({"entry_slug": row["slug"], "reason": "source is not a string or object"})
                        continue
                    source: dict[str, Any] = {"url": raw} if isinstance(raw, str) else dict(raw)
                    if not (source.get("url") or source.get("source_url")):
                        continue
                    raw_url = str(source.get("url") or source.get("source_url"))
                    if Path(raw_url).is_absolute() and not urllib.parse.urlsplit(raw_url).scheme:
                        source["url"] = Path(raw_url).resolve().as_uri()
                    raw_captured = source.get("captured_at") or source.get("captured")
                    if raw_captured:
                        try:
                            _validate_iso_date(raw_captured, "captured_at", timezone_required=True)
                        except ValueError:
                            source["legacy_captured_at_raw"] = raw_captured
                            source["captured_at"] = "0001-01-01T00:00:00Z"
                        else:
                            source["captured_at"] = raw_captured
                    else:
                        source["captured_at"] = "0001-01-01T00:00:00Z"
                    if source["captured_at"] == "0001-01-01T00:00:00Z":
                        source.setdefault("captured_at_unknown_reason", "not retained in historical entry or lacked timezone")
                    if source.get("content_hash"):
                        try:
                            _validate_hash_ref(source.get("content_hash"), "content_hash")
                        except ValueError:
                            source["legacy_content_hash_raw"] = source.pop("content_hash")
                    if not source.get("content_hash"):
                        source.setdefault("content_hash_unknown_reason", "not retained in historical entry")
                    source.setdefault("published_at_unknown_reason", "not retained in historical entry")
                    source.setdefault("capture_method", "legacy-entry-import")
                    source.setdefault("status", "legacy-provenance-unknown")
                    source.setdefault("legacy_import", True)
                    try:
                        canonical_url = _canonical_source_url(str(source.get("url") or source.get("source_url")))
                    except ValueError as exc:
                        skipped_sources += 1
                        skipped_reasons.append({"entry_slug": row["slug"], "reason": str(exc)})
                        continue
                    source_id = "src-" + _sha256_text(canonical_url)[:32]
                    already_normalized = conn.execute(
                        "SELECT 1 FROM source_observations WHERE entry_slug=? AND source_id=? LIMIT 1",
                        (row["slug"], source_id),
                    ).fetchone()
                    if not already_normalized:
                        candidates.append(source)
                if not candidates:
                    continue
                planned_entries += 1
                planned_sources += len(candidates)
                if not args.apply:
                    continue
                run_id = "legacy-" + _sha256_text(str(row["slug"]))[:24]
                _ensure_run(
                    conn,
                    run_id,
                    actor,
                    objective=f"Import historical source metadata for {row['slug']}",
                    outcome="normalized source ledger with unknown provenance preserved",
                )
                observation_ids = _record_sources_for_entry(
                    conn,
                    sources=candidates,
                    run_id=run_id,
                    entry_slug=str(row["slug"]),
                )
                _record_entry_graph(
                    conn,
                    slug=str(row["slug"]),
                    title=str(row["title"] or row["slug"]),
                    run_id=run_id,
                    observation_ids=observation_ids,
                )
                _append_event(
                    conn,
                    event_type="legacy.sources_imported",
                    run_id=run_id,
                    actor_type=actor["actor_type"],
                    actor_id=actor["actor_id"],
                    payload={
                        "entry_slug": row["slug"],
                        "source_observation_ids": observation_ids,
                        "provenance_status": "unknown",
                    },
                    actor_snapshot=actor,
                )
                imported_entries += 1
                imported_observations += len(observation_ids)
            if args.apply:
                _write_source_indexes(conn)
    except (ValueError, sqlite3.Error) as exc:
        print(f"ERROR: legacy source import failed: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()
    result = {
        "mode": "apply" if args.apply else "dry-run",
        "planned_entries": planned_entries,
        "planned_sources": planned_sources,
        "imported_entries": imported_entries,
        "imported_observations": imported_observations,
        "skipped_sources": skipped_sources,
        "skipped_reason_samples": skipped_reasons[:20],
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_trust_record(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    path = Path(args.manifest).expanduser().resolve()
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: invalid trust manifest: {exc}", file=sys.stderr)
        return 2
    subject = manifest.get("subject") or {}
    observations = manifest.get("observations") or []
    run_id = str(args.run_id or manifest.get("run_id") or "")
    errors: list[str] = []
    if not run_id:
        errors.append("missing run_id")
    if not subject.get("kind") or not subject.get("canonical_key"):
        errors.append("subject requires kind and canonical_key")
    if not manifest.get("topic_key"):
        errors.append("missing topic_key")
    if not observations:
        errors.append("observations must be non-empty")
    for item in observations:
        if item.get("dimension") not in TRUST_DIMENSIONS:
            errors.append(f"unsupported trust dimension: {item.get('dimension')}")
        if not item.get("rating") or not item.get("rationale"):
            errors.append("each trust observation requires rating and rationale")
    if errors:
        print(json.dumps({"status": "invalid", "errors": errors}, indent=2))
        return 2
    actor = _actor_from_args(args)
    conn = db_connect()
    ids: list[str] = []
    try:
        with conn:
            _ensure_run(conn, run_id, actor, objective="source trust observation")
            subject_id = _graph_entity(
                conn,
                kind=str(subject["kind"]),
                canonical_key=str(subject["canonical_key"]),
                label=str(subject.get("label") or subject["canonical_key"]),
                properties=subject.get("properties") or {},
            )
            for item in observations:
                trust_id = _new_id("trust")
                evidence_id = item.get("evidence_observation_id")
                if evidence_id and not conn.execute("SELECT 1 FROM source_observations WHERE observation_id=?", (evidence_id,)).fetchone():
                    raise ValueError(f"unknown evidence_observation_id: {evidence_id}")
                conn.execute(
                    """
                    INSERT INTO trust_observations
                      (trust_observation_id, subject_id, run_id, topic_key, observed_at,
                       dimension, rating, rationale, evidence_observation_id, formula_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trust_id, subject_id, run_id, str(manifest["topic_key"]), now_iso(),
                        str(item["dimension"]), str(item["rating"]), str(item["rationale"]),
                        evidence_id, str(item.get("formula_version") or "observation-v1"),
                    ),
                )
                ids.append(trust_id)
            _append_event(
                conn,
                event_type="trust.observed",
                run_id=run_id,
                actor_type=actor["actor_type"],
                actor_id=actor["actor_id"],
                payload={"subject_id": subject_id, "topic_key": manifest["topic_key"], "trust_observation_ids": ids},
                actor_snapshot=actor,
            )
    except (ValueError, sqlite3.Error) as exc:
        print(f"ERROR: trust record failed: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()
    print(json.dumps({"status": "recorded", "trust_observation_ids": ids}, indent=2))
    return 0


def cmd_graph_export(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    conn = db_connect()
    params: list[Any] = []
    where = ""
    if args.run_id:
        where = " WHERE e.run_id=?"
        params.append(args.run_id)
    rows = conn.execute(
        """
        SELECT e.edge_id, e.predicate, e.run_id, e.observed_at, e.status,
               s.entity_id AS subject_id, s.kind AS subject_kind, s.label AS subject_label,
               o.entity_id AS object_id, o.kind AS object_kind, o.label AS object_label
        FROM graph_edges e
        JOIN graph_entities s ON s.entity_id=e.subject_id
        JOIN graph_entities o ON o.entity_id=e.object_id
        """ + where + " ORDER BY e.observed_at, e.edge_id",
        params,
    ).fetchall()
    trust_where = " WHERE t.run_id=?" if args.run_id else ""
    trust_rows = conn.execute(
        """
        SELECT t.*, e.kind AS subject_kind, e.label AS subject_label
        FROM trust_observations t JOIN graph_entities e ON e.entity_id=t.subject_id
        """ + trust_where + " ORDER BY t.observed_at, t.trust_observation_id",
        params,
    ).fetchall()
    discrepancy_where = " WHERE run_id=?" if args.run_id else ""
    discrepancy_rows = conn.execute(
        "SELECT * FROM discrepancies" + discrepancy_where + " ORDER BY first_seen_at, discrepancy_id",
        params,
    ).fetchall()
    traversal_where = " WHERE run_id=?" if args.run_id else ""
    traversal_rows = conn.execute(
        "SELECT * FROM traversal_links" + traversal_where + " ORDER BY depth, discovery_order, traversal_link_id",
        params,
    ).fetchall()
    revision_where = " WHERE run_id=? AND change_from_observation_id IS NOT NULL" if args.run_id else " WHERE change_from_observation_id IS NOT NULL"
    revision_rows = conn.execute(
        """
        SELECT observation_id, change_from_observation_id, source_id, run_id,
               captured_at, published_at, modified_at, locator
        FROM source_observations
        """ + revision_where + " ORDER BY captured_at, observation_id",
        params,
    ).fetchall()
    observation_where = " WHERE o.run_id=?" if args.run_id else ""
    observation_rows = conn.execute(
        """
        SELECT o.observation_id, o.source_id, s.canonical_url, o.run_id,
               o.entry_slug, o.published_at, o.modified_at, o.captured_at,
               o.content_hash, o.normalized_hash, o.capture_method, o.extractor,
               o.extractor_version, o.locator, o.raw_ref, o.status,
               o.change_from_observation_id
        FROM source_observations o JOIN sources s ON s.source_id=o.source_id
        """ + observation_where + " ORDER BY o.captured_at, o.observation_id",
        params,
    ).fetchall()
    conn.close()
    output = Path(args.output).expanduser().resolve() if args.output else content_path("graphs", "research-graph.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "json":
        output.write_text(
            json.dumps(
                {
                    "generated_at": now_iso(),
                    "run_id": args.run_id,
                    "edges": [dict(row) for row in rows],
                    "trust_observations": [dict(row) for row in trust_rows],
                    "discrepancies": [dict(row) for row in discrepancy_rows],
                    "source_revisions": [dict(row) for row in revision_rows],
                    "source_observations": [dict(row) for row in observation_rows],
                    "traversal_links": [dict(row) for row in traversal_rows],
                },
                indent=2,
                ensure_ascii=False,
            ) + "\n"
        )
    else:
        labels: dict[str, str] = {}
        lines = ["# Research dependency graph\n\n", f"Generated: {now_iso()}\n\n", "```mermaid\nflowchart LR\n"]
        for row in rows:
            labels[row["subject_id"]] = f"{row['subject_kind']}: {row['subject_label']}"
            labels[row["object_id"]] = f"{row['object_kind']}: {row['object_label']}"
        for entity_id, label in sorted(labels.items()):
            safe_label = str(label).replace('"', "'").replace("\n", " ")
            lines.append(f"  {entity_id.replace('-', '_')}[\"{safe_label}\"]\n")
        for row in rows:
            lines.append(
                f"  {row['subject_id'].replace('-', '_')} -->|{row['predicate']}| {row['object_id'].replace('-', '_')}\n"
            )
        for row in trust_rows:
            trust_node = row["trust_observation_id"].replace("-", "_")
            safe = f"trust {row['dimension']}: {row['rating']} ({row['observed_at']})".replace('"', "'")
            lines.append(f"  {trust_node}[\"{safe}\"]\n")
            lines.append(f"  {row['subject_id'].replace('-', '_')} -.->|assessedBy| {trust_node}\n")
        for row in discrepancy_rows:
            left = "ent_" + _sha256_text(f"claim:{row['run_id']}:{row['left_claim_id']}")[:32]
            right = "ent_" + _sha256_text(f"claim:{row['run_id']}:{row['right_claim_id']}")[:32]
            lines.append(f"  {left} -->|{row['status']} discrepancy| {right}\n")
        for row in traversal_rows:
            link_node = row["traversal_link_id"].replace("-", "_")
            safe_url = str(row["canonical_url"] or row["displayed_url"]).replace('"', "'")
            lines.append(f"  {link_node}[\"link {row['depth']}: {row['decision']} {safe_url}\"]\n")
            if row["parent_observation_id"]:
                parent = "ent_" + _sha256_text(f"observation:{row['parent_observation_id']}")[:32]
                lines.append(f"  {parent} -.->|discovered| {link_node}\n")
        lines.append("```\n")
        output.write_text("".join(lines))
    print(output)
    return 0


def _private_or_local_host(host: str) -> bool:
    lowered = host.lower().rstrip(".")
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return not address.is_global


def _redact_url_credentials(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.username is None and parsed.password is None:
        return value
    host = parsed.hostname or "redacted-host"
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host + (f":{parsed.port}" if parsed.port else "")
    return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def cmd_traversal_record(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    path = Path(args.manifest).expanduser().resolve()
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: invalid traversal manifest: {exc}", file=sys.stderr)
        return 2
    run_id = str(args.run_id or manifest.get("run_id") or "")
    links = manifest.get("links")
    if not run_id or not isinstance(links, list) or not links:
        print("ERROR: traversal manifest requires run_id and a non-empty links list", file=sys.stderr)
        return 2
    actor = _actor_from_args(args)
    conn = db_connect()
    run = conn.execute("SELECT contract_json FROM research_runs WHERE run_id=?", (run_id,)).fetchone()
    if not run:
        conn.close()
        print(f"ERROR: run must be initialized before traversal: {run_id}", file=sys.stderr)
        return 2
    contract = json.loads(run["contract_json"] or "{}")
    contract_errors = _run_contract_errors(contract)
    if contract_errors:
        conn.close()
        print(json.dumps({"status": "invalid_contract", "errors": contract_errors}, indent=2))
        return 2
    policy = contract["traversal"]
    allowed_domains = [str(item).lower().rstrip(".") for item in policy["allowed_domains"]]
    existing = conn.execute(
        """
        SELECT COUNT(*) AS links,
               COALESCE(SUM(CASE WHEN decision IN ('queued','captured') THEN 1 ELSE 0 END),0) AS accepted,
               COALESCE(SUM(bytes),0) AS bytes,
               COALESCE(SUM(elapsed_ms),0) AS elapsed_ms
        FROM traversal_links WHERE run_id=?
        """,
        (run_id,),
    ).fetchone()
    accepted_count = int(existing["accepted"])
    used_bytes = int(existing["bytes"])
    used_ms = int(existing["elapsed_ms"])
    parent_observation_id = manifest.get("parent_observation_id")
    if parent_observation_id and not conn.execute(
        "SELECT 1 FROM source_observations WHERE observation_id=?", (parent_observation_id,)
    ).fetchone():
        conn.close()
        print(f"ERROR: unknown parent_observation_id: {parent_observation_id}", file=sys.stderr)
        return 2
    records: list[dict[str, Any]] = []
    try:
        with conn:
            for offset, link in enumerate(links):
                if not isinstance(link, dict):
                    raise ValueError(f"link {offset} must be an object")
                displayed = str(link.get("displayed_url") or link.get("url") or "")
                resolved = str(link.get("resolved_url") or displayed)
                depth = link.get("depth")
                order = link.get("discovery_order", int(existing["links"]) + offset + 1)
                reason = "accepted_by_policy"
                decision = "captured" if link.get("child_observation_id") else "queued"
                canonical = ""
                parsed = urllib.parse.urlsplit(resolved)
                displayed_parsed = urllib.parse.urlsplit(displayed)
                host = (parsed.hostname or "").lower().rstrip(".")
                has_credentials = any(
                    value is not None
                    for value in (parsed.username, parsed.password, displayed_parsed.username, displayed_parsed.password)
                )
                if has_credentials:
                    displayed = _redact_url_credentials(displayed)
                    resolved = _redact_url_credentials(resolved)
                    parsed = urllib.parse.urlsplit(resolved)
                try:
                    canonical = _canonical_source_url(resolved)
                except ValueError:
                    decision, reason = "rejected", "invalid_or_unsupported_url"
                if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
                    decision, reason = "rejected", "invalid_depth"
                    depth = -1
                elif depth > int(policy["max_depth"]):
                    decision, reason = "rejected", "depth_limit"
                elif parsed.scheme.lower() not in {"http", "https"}:
                    decision, reason = "rejected", "web_traversal_requires_http"
                elif has_credentials:
                    decision, reason = "rejected", "credential_bearing_url"
                elif _private_or_local_host(host):
                    decision, reason = "rejected", "private_or_local_destination"
                elif not any(host == domain or host.endswith("." + domain) for domain in allowed_domains):
                    decision, reason = "rejected", "domain_not_allowed"
                elif link.get("robots_allowed") is not True:
                    decision, reason = "rejected", "robots_not_confirmed_allowed"
                child_id = link.get("child_observation_id")
                if child_id and not conn.execute("SELECT 1 FROM source_observations WHERE observation_id=?", (child_id,)).fetchone():
                    decision, reason = "rejected", "unknown_child_observation"
                link_bytes = int(link.get("bytes") or 0)
                elapsed_ms = int(link.get("elapsed_ms") or 0)
                if link_bytes < 0 or elapsed_ms < 0:
                    decision, reason = "rejected", "negative_measurement"
                if decision in {"queued", "captured"} and accepted_count + 1 > int(policy["max_pages"]):
                    decision, reason = "rejected", "page_budget"
                if decision in {"queued", "captured"} and used_bytes + link_bytes > int(policy["max_bytes"]):
                    decision, reason = "rejected", "byte_budget"
                if decision in {"queued", "captured"} and used_ms + elapsed_ms > int(policy["max_seconds"]) * 1000:
                    decision, reason = "rejected", "time_budget"
                record_id = _new_id("link")
                conn.execute(
                    """
                    INSERT INTO traversal_links
                      (traversal_link_id, run_id, parent_observation_id, discovered_at,
                       discovery_order, depth, displayed_url, resolved_url, canonical_url,
                       decision, reason, evidence_gap, child_observation_id, bytes,
                       elapsed_ms, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id, run_id, parent_observation_id, now_iso(), int(order), int(depth),
                        displayed, resolved, canonical, decision, reason, link.get("evidence_gap"),
                        child_id if decision == "captured" else None, link_bytes, elapsed_ms,
                        _canonical_json({**link, "url": displayed, "displayed_url": displayed, "resolved_url": resolved}),
                    ),
                )
                if decision in {"queued", "captured"}:
                    accepted_count += 1
                    used_bytes += link_bytes
                    used_ms += elapsed_ms
                records.append({"traversal_link_id": record_id, "decision": decision, "reason": reason, "canonical_url": canonical})
            _append_event(
                conn,
                event_type="traversal.recorded",
                run_id=run_id,
                actor_type=actor["actor_type"],
                actor_id=actor["actor_id"],
                payload={"parent_observation_id": parent_observation_id, "records": records},
                actor_snapshot=actor,
            )
    except (ValueError, sqlite3.Error) as exc:
        print(f"ERROR: traversal record failed: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()
    print(json.dumps({"run_id": run_id, "records": records}, indent=2))
    return 0


def _doctor_report() -> dict[str, Any]:
    ensure_layout()
    ensure_db()
    conn = db_connect()
    chain_ok, chain_errors = _verify_event_chain(conn)
    disk_files = list(content_path("topics").glob("**/*.md"))
    malformed: list[dict[str, str]] = []
    slug_counts: dict[str, int] = {}
    for path in disk_files:
        try:
            fm, _ = parse_frontmatter(path.read_text(), fatal=False)
        except (OSError, ValueError) as exc:
            malformed.append({"path": str(path), "reason": str(exc)})
            continue
        slug = str(fm.get("slug") or "")
        if not slug:
            malformed.append({"path": str(path), "reason": "missing_slug"})
        else:
            slug_counts[slug] = slug_counts.get(slug, 0) + 1
    duplicates = sorted(slug for slug, count in slug_counts.items() if count > 1)
    db_entries = conn.execute("SELECT COUNT(*) AS n FROM entries").fetchone()["n"]
    counts = {
        "disk_topic_files": len(disk_files),
        "db_entries": db_entries,
        "runs": conn.execute("SELECT COUNT(*) AS n FROM research_runs").fetchone()["n"],
        "events": conn.execute("SELECT COUNT(*) AS n FROM audit_events").fetchone()["n"],
        "sources": conn.execute("SELECT COUNT(*) AS n FROM sources").fetchone()["n"],
        "source_observations": conn.execute("SELECT COUNT(*) AS n FROM source_observations").fetchone()["n"],
        "calculation_receipts": conn.execute("SELECT COUNT(*) AS n FROM calculation_receipts").fetchone()["n"],
    }
    provenance_rows = conn.execute(
        "SELECT actor_type, actor_id, host, session_id, tool_version FROM research_runs"
    ).fetchall()
    provenance_unknown = {
        field: sum(1 for row in provenance_rows if not row[field] or row[field] == "unknown")
        for field in ("actor_type", "actor_id", "host", "session_id", "tool_version")
    }
    provenance_snapshots = {
        row["run_id"]: row
        for row in conn.execute(
            """
            SELECT e.* FROM audit_events e
            JOIN (
              SELECT run_id, MAX(seq) AS seq FROM audit_events
              WHERE event_type IN ('run.created', 'run.provenance_enriched')
              GROUP BY run_id
            ) latest ON latest.seq=e.seq
            """
        )
    }
    provenance_snapshot_errors: list[dict[str, Any]] = []
    for row in conn.execute(
        "SELECT run_id, actor_type, actor_id, host, session_id, tool_version FROM research_runs"
    ):
        snapshot = provenance_snapshots.get(row["run_id"])
        if not snapshot:
            provenance_snapshot_errors.append({"run_id": row["run_id"], "reason": "missing_append_only_snapshot"})
            continue
        mismatched = [
            field for field in ("actor_type", "actor_id", "host", "session_id", "tool_version")
            if row[field] != snapshot[field]
        ]
        if mismatched:
            provenance_snapshot_errors.append({"run_id": row["run_id"], "reason": "snapshot_mismatch", "fields": mismatched})
    entries_missing_source_history: list[str] = []
    for row in conn.execute("SELECT slug, sources FROM entries"):
        source_items = json.loads(row["sources"] or "[]")
        if source_items and not conn.execute(
            "SELECT 1 FROM source_observations WHERE entry_slug=? LIMIT 1", (row["slug"],)
        ).fetchone():
            entries_missing_source_history.append(row["slug"])
    incomplete_observations = [
        dict(row)
        for row in conn.execute(
            """
            SELECT observation_id, entry_slug, source_id, status,
                   CASE WHEN content_hash='' THEN 1 ELSE 0 END AS missing_content_hash,
                   CASE WHEN published_at IS NULL OR published_at='' THEN 1 ELSE 0 END AS missing_published_at
            FROM source_observations
            WHERE status='incomplete' OR content_hash=''
            ORDER BY captured_at, observation_id
            """
        )
    ]
    receipt_integrity_errors: list[dict[str, str]] = []
    indexed_receipt_paths: set[str] = set()
    for row in conn.execute("SELECT receipt_id, receipt_hash, receipt_path FROM calculation_receipts ORDER BY created_at"):
        indexed_receipt_paths.add(str(Path(row["receipt_path"]).resolve()))
        if not row["receipt_hash"]:
            receipt_integrity_errors.append({"receipt_id": row["receipt_id"], "reason": "missing_receipt_hash"})
            continue
        try:
            receipt_payload = json.loads(Path(row["receipt_path"]).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            receipt_integrity_errors.append({"receipt_id": row["receipt_id"], "reason": f"unreadable_receipt:{exc}"})
            continue
        embedded_hash = str(receipt_payload.pop("receipt_hash", ""))
        actual_hash = "sha256:" + _sha256_text(_canonical_json(receipt_payload))
        if embedded_hash != row["receipt_hash"] or actual_hash != row["receipt_hash"]:
            receipt_integrity_errors.append({"receipt_id": row["receipt_id"], "reason": "receipt_hash_mismatch"})
    for receipt_file in index_path("calculation-receipts").glob("*.json"):
        if str(receipt_file.resolve()) not in indexed_receipt_paths:
            receipt_integrity_errors.append({"receipt_id": receipt_file.stem, "reason": "unindexed_receipt_file"})
    merge_integrity_errors: list[dict[str, str]] = []
    for row in conn.execute(
        "SELECT event_id, payload_json FROM audit_events WHERE event_type IN ('run.merge_validated','run.merge_rejected') ORDER BY seq"
    ):
        payload = json.loads(row["payload_json"] or "{}")
        attempt_path_value = payload.get("attempt_path")
        if not attempt_path_value:
            continue
        attempt_path = Path(attempt_path_value)
        if not attempt_path.is_file():
            merge_integrity_errors.append({"event_id": row["event_id"], "reason": "missing_merge_attempt"})
            continue
        actual_attempt_hash = "sha256:" + _file_sha256(attempt_path)
        if actual_attempt_hash != payload.get("attempt_hash"):
            merge_integrity_errors.append({"event_id": row["event_id"], "reason": "merge_attempt_hash_mismatch"})
            continue
        try:
            attempt = json.loads(attempt_path.read_text())
        except (OSError, json.JSONDecodeError):
            merge_integrity_errors.append({"event_id": row["event_id"], "reason": "invalid_merge_attempt"})
            continue
        input_provenance = attempt.get("input_provenance") or {}
        input_records = list(input_provenance.get("results") or [])
        if input_provenance.get("reconciliation"):
            input_records.append(input_provenance["reconciliation"])
        for item in input_records:
            snapshot_path = Path(str(item.get("snapshot_path") or ""))
            if not snapshot_path.is_file():
                merge_integrity_errors.append({"event_id": row["event_id"], "reason": "missing_merge_input_snapshot"})
                continue
            actual_input_hash = "sha256:" + _file_sha256(snapshot_path)
            if actual_input_hash != item.get("content_hash"):
                merge_integrity_errors.append({"event_id": row["event_id"], "reason": "merge_input_hash_mismatch"})
    conn.close()
    checks = {
        "event_chain": {"passed": chain_ok, "errors": chain_errors},
        "disk_index_parity": {"passed": len(slug_counts) == db_entries, "disk_valid_unique_slugs": len(slug_counts), "db_entries": db_entries},
        "frontmatter": {"passed": not malformed, "malformed": malformed},
        "duplicate_slugs": {"passed": not duplicates, "slugs": duplicates},
        "run_provenance": {
            "passed": (not provenance_rows or all(count == 0 for count in provenance_unknown.values())) and not provenance_snapshot_errors,
            "total": len(provenance_rows),
            "unknown_by_field": provenance_unknown,
            "snapshot_errors": provenance_snapshot_errors,
        },
        "source_history": {
            "passed": not entries_missing_source_history and not incomplete_observations,
            "entries_missing_normalized_history": sorted(entries_missing_source_history),
            "incomplete_observations": incomplete_observations,
        },
        "calculation_receipt_integrity": {
            "passed": not receipt_integrity_errors,
            "errors": receipt_integrity_errors,
        },
        "merge_attempt_integrity": {
            "passed": not merge_integrity_errors,
            "errors": merge_integrity_errors,
        },
    }
    return {"status": "passed" if all(v["passed"] for v in checks.values()) else "findings", "counts": counts, "checks": checks}


def cmd_doctor(args: argparse.Namespace) -> int:
    report = _doctor_report()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Research doctor: {report['status']}")
        for name, check in report["checks"].items():
            print(f"  {'PASS' if check['passed'] else 'FINDING'} {name}")
        print("  " + " ".join(f"{key}={value}" for key, value in report["counts"].items()))
    return 0 if report["status"] == "passed" else 1


def _decimal_value(value: Any) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError("calculation inputs must be numeric")
    try:
        parsed = Decimal(str(value))
        if not parsed.is_finite():
            raise ValueError(f"numeric input must be finite: {value}")
        return parsed
    except InvalidOperation as exc:
        raise ValueError(f"invalid numeric input: {value}") from exc


def _safe_calculate(expression: str, values: dict[str, Decimal]) -> Decimal | bool:
    tree = ast.parse(expression, mode="eval")

    def walk(node: ast.AST) -> Decimal | bool:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Name) and node.id in values:
            return values[node.id]
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)) and not isinstance(node.value, bool):
            return _decimal_value(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = walk(node.operand)
            if isinstance(value, bool):
                raise ValueError("boolean cannot be used as a number")
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            left, right = walk(node.left), walk(node.right)
            if isinstance(left, bool) or isinstance(right, bool):
                raise ValueError("boolean cannot be used as a number")
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise ZeroDivisionError("denominator is zero")
                return left / right
            exponent = int(right)
            if Decimal(exponent) != right or abs(exponent) > 100:
                raise ValueError("exponent must be an integer between -100 and 100")
            return left ** exponent
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            left, right = walk(node.left), walk(node.comparators[0])
            op = node.ops[0]
            if isinstance(op, ast.Eq):
                return left == right
            if isinstance(op, ast.NotEq):
                return left != right
            if isinstance(op, ast.Lt):
                return left < right
            if isinstance(op, ast.LtE):
                return left <= right
            if isinstance(op, ast.Gt):
                return left > right
            if isinstance(op, ast.GtE):
                return left >= right
        raise ValueError(f"unsupported calculation syntax: {type(node).__name__}")

    return walk(tree)


def _validate_calculation_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("run_id", "claim_id", "formula", "unit", "denominator", "grain", "inputs", "assumptions", "checks"):
        if field not in spec:
            errors.append(f"missing {field}")
    if not isinstance(spec.get("inputs"), list) or not spec.get("inputs"):
        errors.append("inputs must be a non-empty list")
    if not isinstance(spec.get("assumptions"), list):
        errors.append("assumptions must be a list")
    if not isinstance(spec.get("checks"), list) or not spec.get("checks"):
        errors.append("checks must be a non-empty list")
    for field in ("unit", "denominator", "grain"):
        value = str(spec.get(field) or "").strip().lower()
        if value in {"", "unknown", "tbd", "ambiguous", "none", "null", "not_applicable"}:
            errors.append(f"{field} must be explicit; use not_applicable: <reason> when it does not apply")
    names: list[str] = []
    for item in spec.get("inputs") or []:
        if not isinstance(item, dict) or not all(key in item for key in ("name", "value", "source_observation_id")):
            errors.append("each input requires name, value, and source_observation_id")
            continue
        name = str(item["name"])
        names.append(name)
        if not name.isidentifier():
            errors.append(f"input name must be a Python identifier: {name}")
    if len(names) != len(set(names)):
        errors.append("input names must be unique")
    for check in spec.get("checks") or []:
        if not isinstance(check, dict) or not check.get("name") or not check.get("expression"):
            errors.append("each check requires name and expression")
    return errors


def cmd_calculate(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    spec_path = Path(args.spec).expanduser().resolve()
    try:
        spec = json.loads(spec_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: invalid calculation spec: {exc}", file=sys.stderr)
        return 2
    errors = _validate_calculation_spec(spec)
    resolved_inputs: list[dict[str, Any]] = []
    lookup_conn = db_connect()
    for item in spec.get("inputs") or []:
        resolved = dict(item) if isinstance(item, dict) else {}
        observation_id = resolved.get("source_observation_id")
        row = lookup_conn.execute(
            "SELECT source_id, content_hash, normalized_hash FROM source_observations WHERE observation_id=?",
            (observation_id,),
        ).fetchone() if observation_id else None
        if not row:
            errors.append(f"unknown source_observation_id: {observation_id}")
        else:
            resolved["source_id"] = row["source_id"]
            resolved["source_content_hash"] = row["content_hash"]
            resolved["source_normalized_hash"] = row["normalized_hash"]
            if not row["content_hash"]:
                errors.append(f"source observation lacks a content hash: {observation_id}")
        resolved_inputs.append(resolved)
    correction_id = spec.get("correction_of_receipt_id")
    if correction_id and not lookup_conn.execute(
        "SELECT 1 FROM calculation_receipts WHERE receipt_id=?", (correction_id,)
    ).fetchone():
        lookup_conn.close()
        print(f"ERROR: unknown correction_of_receipt_id: {correction_id}", file=sys.stderr)
        return 2
    lookup_conn.close()
    actor = _actor_from_args(args)
    started = time.perf_counter_ns()
    result_text: str | None = None
    check_results: list[dict[str, Any]] = []
    status = "inconclusive" if errors else "passed"
    failure = ""
    try:
        values = {str(item["name"]): _decimal_value(item["value"]) for item in resolved_inputs}
        if not errors:
            result = _safe_calculate(str(spec["formula"]), values)
            if isinstance(result, bool):
                raise ValueError("formula must produce a number")
            result_text = format(result, "f")
            values["result"] = result
            for check in spec["checks"]:
                expression = str(check.get("expression") or "")
                check_value = _safe_calculate(expression, values) if expression else False
                if not isinstance(check_value, bool):
                    raise ValueError(f"check must be a boolean comparison: {expression}")
                passed = check_value
                check_results.append({"name": str(check.get("name") or expression), "expression": expression, "passed": passed})
            if not all(item["passed"] for item in check_results):
                status = "failed"
    except (ValueError, ZeroDivisionError, InvalidOperation, SyntaxError) as exc:
        status = "inconclusive"
        failure = str(exc)
    runtime_ms = max(0, (time.perf_counter_ns() - started) // 1_000_000)
    receipt_id = _new_id("calc")
    receipt_dir = index_path("calculation-receipts")
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / f"{receipt_id}.json"
    input_payload = resolved_inputs
    output_payload = {"result": result_text, "unit": spec.get("unit"), "status": status}
    receipt = {
        "receipt_id": receipt_id,
        "run_id": str(spec.get("run_id") or "unknown"),
        "claim_id": str(spec.get("claim_id") or "unknown"),
        "created_at": now_iso(),
        "correction_of_receipt_id": spec.get("correction_of_receipt_id"),
        "status": status,
        "failure": failure,
        "formula": str(spec.get("formula") or ""),
        "formula_hash": _sha256_text(str(spec.get("formula") or "")),
        "unit": str(spec.get("unit") or "unknown"),
        "denominator": str(spec.get("denominator") or "unknown"),
        "grain": str(spec.get("grain") or "unknown"),
        "assumptions": spec.get("assumptions") or [],
        "inputs": input_payload,
        "input_hash": _sha256_text(_canonical_json(input_payload)),
        "code_hash": _file_sha256(Path(__file__)),
        "command": [sys.executable, str(Path(__file__).resolve()), "calculate", "--spec", str(spec_path)],
        "runtime_ms": runtime_ms,
        "result_text": result_text,
        "output_hash": _sha256_text(_canonical_json(output_payload)),
        "checks": check_results,
        "validation_errors": errors,
        "environment": {
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
            "platform": platform.platform(),
            "timezone": str(datetime.now().astimezone().tzinfo),
        },
    }
    receipt["receipt_hash"] = "sha256:" + _sha256_text(_canonical_json(receipt))
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    conn = db_connect()
    try:
        with conn:
            _ensure_run(conn, receipt["run_id"], actor, objective="deterministic calculation")
            conn.execute(
                """
                INSERT INTO calculation_receipts
                  (receipt_id, run_id, claim_id, created_at, correction_of_receipt_id,
                   status, formula, formula_hash, unit, denominator, grain,
                   assumptions_json, inputs_json, input_hash, code_hash, command_json,
                   runtime_ms, result_text, output_hash, checks_json, environment_json,
                   receipt_hash, receipt_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_id, receipt["run_id"], receipt["claim_id"], receipt["created_at"],
                    receipt["correction_of_receipt_id"], status, receipt["formula"], receipt["formula_hash"],
                    receipt["unit"], receipt["denominator"], receipt["grain"],
                    _canonical_json(receipt["assumptions"]), _canonical_json(input_payload), receipt["input_hash"],
                    receipt["code_hash"], _canonical_json(receipt["command"]), runtime_ms, result_text,
                    receipt["output_hash"], _canonical_json(check_results), _canonical_json(receipt["environment"]),
                    receipt["receipt_hash"],
                    str(receipt_path),
                ),
            )
            run_entity = _graph_entity(conn, kind="run", canonical_key=receipt["run_id"], label=receipt["run_id"])
            claim_entity = _graph_entity(
                conn,
                kind="claim",
                canonical_key=f"{receipt['run_id']}:{receipt['claim_id']}",
                label=receipt["claim_id"],
            )
            calc_entity = _graph_entity(conn, kind="calculation", canonical_key=receipt_id, label=receipt_id)
            _graph_edge(conn, subject_id=claim_entity, predicate="wasGeneratedBy", object_id=calc_entity, run_id=receipt["run_id"], status=status)
            _graph_edge(conn, subject_id=calc_entity, predicate="wasGeneratedBy", object_id=run_entity, run_id=receipt["run_id"], status=status)
            for item in input_payload:
                observation_entity = _graph_entity(
                    conn,
                    kind="observation",
                    canonical_key=str(item["source_observation_id"]),
                    label=str(item["source_observation_id"]),
                )
                _graph_edge(
                    conn,
                    subject_id=calc_entity,
                    predicate="used",
                    object_id=observation_entity,
                    run_id=receipt["run_id"],
                    evidence_observation_id=str(item["source_observation_id"]),
                    status=status,
                )
            _append_event(
                conn,
                event_type="calculation.recorded",
                run_id=receipt["run_id"],
                actor_type=actor["actor_type"],
                actor_id=actor["actor_id"],
                payload={"receipt_id": receipt_id, "claim_id": receipt["claim_id"], "status": status, "output_hash": receipt["output_hash"], "receipt_hash": receipt["receipt_hash"]},
                actor_snapshot=actor,
            )
    except (ValueError, sqlite3.Error) as exc:
        try:
            receipt_path.unlink(missing_ok=True)
        except OSError:
            pass
        print(f"ERROR: could not persist calculation receipt: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()
    print(receipt_path)
    print(json.dumps({"receipt_id": receipt_id, "status": status, "result": result_text}, indent=2))
    return 0 if status == "passed" else 2


def _load_contract(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("run contract must be a JSON object")
    return data


def _run_contract_errors(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in (
        "objective", "intent", "outcome", "success_criteria", "wrong_answer_consequence",
        "decision_card", "section_contracts", "source_policy", "hypotheses", "tasks",
        "merge_strategy", "traversal",
    ):
        if not contract.get(field):
            errors.append(f"missing {field}")
    success_criteria = contract.get("success_criteria")
    if not isinstance(success_criteria, list) or not success_criteria or not all(
        isinstance(item, str) and item.strip() for item in success_criteria
    ):
        errors.append("success_criteria must be a non-empty list of strings")
    decision_card = contract.get("decision_card")
    if not isinstance(decision_card, dict) or not all(
        isinstance(decision_card.get(field), str) and decision_card[field].strip()
        for field in ("decision", "use")
    ):
        errors.append("decision_card requires decision and use")
    source_policy = contract.get("source_policy")
    if not isinstance(source_policy, dict):
        errors.append("source_policy must be an object")
    else:
        lanes = source_policy.get("coverage_lanes")
        if not isinstance(lanes, list) or not lanes or not all(isinstance(item, str) and item.strip() for item in lanes):
            errors.append("source_policy.coverage_lanes must be a non-empty list of strings")
        elif not {"primary", "independent", "counter-evidence", "currentness"}.issubset(set(lanes)):
            errors.append("source_policy.coverage_lanes must include primary, independent, counter-evidence, and currentness")
        for quality in ("good", "poor"):
            values = source_policy.get(quality)
            if not isinstance(values, list) or not values or not all(isinstance(item, str) and item.strip() for item in values):
                errors.append(f"source_policy.{quality} must be a non-empty list of strings")
    merge_strategy = contract.get("merge_strategy")
    if not isinstance(merge_strategy, dict):
        errors.append("merge_strategy must be an object")
    else:
        if merge_strategy.get("single_writer") is not True:
            errors.append("merge_strategy.single_writer must be true")
        if merge_strategy.get("preserve_contradictions") is not True:
            errors.append("merge_strategy.preserve_contradictions must be true")
    hypotheses = contract.get("hypotheses")
    if not isinstance(hypotheses, list) or not hypotheses:
        errors.append("hypotheses must be a non-empty list")
        hypotheses = []
    for index, hypothesis in enumerate(hypotheses):
        if not isinstance(hypothesis, dict) or not all(
            hypothesis.get(field) for field in ("hypothesis_id", "statement", "falsifiers", "decision_consequence")
        ):
            errors.append(f"hypothesis {index} requires hypothesis_id, statement, falsifiers, and decision_consequence")
        elif not isinstance(hypothesis.get("falsifiers"), list) or not all(
            isinstance(item, str) and item.strip() for item in hypothesis["falsifiers"]
        ):
            errors.append(f"hypothesis {index} falsifiers must be a non-empty list of strings")
    task_ids: list[str] = []
    owned_sections: list[str] = []
    tasks = contract.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        errors.append("tasks must be a non-empty list")
        tasks = []
    for index, task in enumerate(tasks):
        if not isinstance(task, dict) or not all(task.get(field) for field in ("task_id", "section", "question")):
            errors.append(f"task {index} requires task_id, section, and question")
            continue
        if not isinstance(task.get("depends_on"), list) or not all(isinstance(item, str) for item in task["depends_on"]):
            errors.append(f"task {index} depends_on must be a list of task IDs")
        task_ids.append(str(task["task_id"]))
        owned_sections.append(str(task["section"]))
    if len(task_ids) != len(set(task_ids)):
        errors.append("task_id values must be unique")
    if len(owned_sections) != len(set(owned_sections)):
        errors.append("each section must have one task owner")
    for index, task in enumerate(tasks):
        if isinstance(task, dict):
            unknown_dependencies = sorted(set(task.get("depends_on") or []) - set(task_ids))
            if unknown_dependencies:
                errors.append(f"task {index} has unknown dependencies: {unknown_dependencies}")
    section_contracts = contract.get("section_contracts")
    if not isinstance(section_contracts, list) or not section_contracts:
        errors.append("section_contracts must be a non-empty list")
    else:
        contract_sections: list[str] = []
        for index, section_contract in enumerate(section_contracts):
            if not isinstance(section_contract, dict) or not section_contract.get("section"):
                errors.append(f"section_contract {index} requires section")
                continue
            criteria = section_contract.get("completion_criteria")
            if not isinstance(criteria, list) or not criteria or not all(isinstance(item, str) and item.strip() for item in criteria):
                errors.append(f"section_contract {index} completion_criteria must be a non-empty list of strings")
            contract_sections.append(str(section_contract["section"]))
        if set(contract_sections) != set(owned_sections):
            errors.append("section_contracts must match task-owned sections exactly")
    traversal = contract.get("traversal")
    if not isinstance(traversal, dict):
        errors.append("traversal must be an object")
        traversal = {}
    depth = traversal.get("max_depth")
    if depth not in (1, 2, 3):
        errors.append("traversal.max_depth must be 1, 2, or 3")
    if depth == 3 and not traversal.get("depth_3_reason"):
        errors.append("depth 3 requires depth_3_reason")
    for field in ("max_pages", "max_bytes", "max_seconds"):
        value = traversal.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            errors.append(f"traversal.{field} must be a positive integer")
    domains = traversal.get("allowed_domains")
    if not isinstance(domains, list) or not domains or not all(
        isinstance(item, str) and item.strip() and "://" not in item and "/" not in item for item in domains
    ):
        errors.append("traversal.allowed_domains must be a non-empty list of domain names")
    if traversal and traversal.get("robots_policy") != "respect-fail-closed":
        errors.append("traversal.robots_policy must be respect-fail-closed")
    return errors


def cmd_run_init(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    source = Path(args.contract).expanduser().resolve()
    try:
        contract = _load_contract(source)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: invalid run contract: {exc}", file=sys.stderr)
        return 2
    errors = _run_contract_errors(contract)
    if errors:
        print(json.dumps({"status": "invalid", "errors": errors}, indent=2))
        return 2
    run_id = str(contract.get("run_id") or _new_id("run"))
    contract["run_id"] = run_id
    contract.setdefault("created_at", now_iso())
    actor = _actor_from_args(args)
    run_dir = index_path("runs", run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    contract_path = run_dir / "contract.json"
    contract_path.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n")
    initialized_contract_hash = _contract_hash(contract)
    task_dir = run_dir / "tasks"
    task_dir.mkdir()
    for task in contract["tasks"]:
        packet = {
            "run_id": run_id,
            "initialized_contract_hash": initialized_contract_hash,
            "task": task,
            "objective": contract["objective"],
            "source_policy": contract["source_policy"],
            "traversal": contract["traversal"],
            "required_result_fields": [
                "run_id", "initialized_contract_hash", "task_id", "claims",
                "source_observation_ids", "reused_observation_ids", "limitations",
            ],
        }
        (task_dir / f"{task['task_id']}.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
    conn = db_connect()
    with conn:
        _ensure_run(
            conn, run_id, actor, objective=str(contract["objective"]), intent=str(contract["intent"]),
            outcome=str(contract["outcome"]), contract=contract,
        )
        _append_event(
            conn, event_type="run.initialized", run_id=run_id,
            actor_type=actor["actor_type"], actor_id=actor["actor_id"],
            payload={"contract_path": str(contract_path), "contract_hash": _file_sha256(contract_path), "task_ids": [t["task_id"] for t in contract["tasks"]]},
            actor_snapshot=actor,
        )
    conn.close()
    print(
        json.dumps(
            {
                "run_id": run_id,
                "contract_hash": initialized_contract_hash,
                "contract": str(contract_path),
                "tasks": str(task_dir),
            },
            indent=2,
        )
    )
    return 0


def cmd_run_validate(args: argparse.Namespace) -> int:
    try:
        contract = _load_contract(Path(args.contract).expanduser().resolve())
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "invalid", "errors": [str(exc)]}, indent=2))
        return 2
    errors = _run_contract_errors(contract)
    print(json.dumps({"status": "valid" if not errors else "invalid", "errors": errors}, indent=2))
    return 0 if not errors else 2


def _ordered_pair(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left <= right else (right, left)


def cmd_run_merge(args: argparse.Namespace) -> int:
    ensure_db()
    try:
        contract_path_input = Path(args.contract).expanduser().resolve()
        contract = _load_contract(contract_path_input)
        result_input_blobs: list[tuple[Path, bytes, dict[str, Any]]] = []
        for raw_path in args.result:
            result_path = Path(raw_path).expanduser().resolve()
            raw_bytes = result_path.read_bytes()
            result = json.loads(raw_bytes.decode("utf-8"))
            if not isinstance(result, dict):
                raise ValueError(f"worker result must be a JSON object: {result_path}")
            result_input_blobs.append((result_path, raw_bytes, result))
        results = [item[2] for item in result_input_blobs]
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "invalid", "errors": [str(exc)]}, indent=2))
        return 2
    errors = _run_contract_errors(contract)
    initialized_run_id = str(contract.get("run_id") or "")
    guard_conn = db_connect()
    initialized = guard_conn.execute(
        "SELECT contract_hash FROM research_runs WHERE run_id=?", (initialized_run_id,)
    ).fetchone() if initialized_run_id else None
    guard_conn.close()
    binding_error = ""
    if not initialized:
        binding_error = "run contract must be initialized before merge"
    elif initialized["contract_hash"] != _contract_hash(contract):
        binding_error = "merge contract differs from the initialized contract"
    if binding_error:
        errors.append(binding_error)
        if initialized and initialized_run_id:
            actor = _actor_from_args(args)
            audit_conn = db_connect()
            with audit_conn:
                _append_event(
                    audit_conn,
                    event_type="run.merge_rejected",
                    run_id=initialized_run_id,
                    actor_type=actor["actor_type"],
                    actor_id=actor["actor_id"],
                    payload={"status": "invalid", "errors": errors, "candidate_contract_hash": _contract_hash(contract)},
                    actor_snapshot=actor,
                )
            audit_conn.close()
        print(json.dumps({"run_id": initialized_run_id or None, "status": "invalid", "errors": errors, "claims": [], "limitations": []}, indent=2))
        return 2
    assert initialized is not None
    initialized_contract_hash = str(initialized["contract_hash"])
    reconciliation_items: list[dict[str, Any]] = []
    reconciliation_input_blob: tuple[Path, bytes, dict[str, Any]] | None = None
    if args.reconciliation:
        try:
            reconciliation_path = Path(args.reconciliation).expanduser().resolve()
            reconciliation_bytes = reconciliation_path.read_bytes()
            reconciliation_manifest = json.loads(reconciliation_bytes.decode("utf-8"))
            if not isinstance(reconciliation_manifest, dict):
                raise ValueError("reconciliation manifest must be a JSON object")
            reconciliation_input_blob = (reconciliation_path, reconciliation_bytes, reconciliation_manifest)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"invalid reconciliation manifest: {exc}")
        else:
            if reconciliation_manifest.get("run_id") != initialized_run_id:
                errors.append("reconciliation manifest run_id does not match the contract")
            if reconciliation_manifest.get("initialized_contract_hash") != initialized_contract_hash:
                errors.append("reconciliation manifest contract hash does not match the initialized contract")
            items = reconciliation_manifest.get("reconciliations")
            if not isinstance(items, list):
                errors.append("reconciliation manifest requires a reconciliations list")
            else:
                reconciliation_items = [item for item in items if isinstance(item, dict)]
                if len(reconciliation_items) != len(items):
                    errors.append("each reconciliation must be an object")
    expected = {str(task["task_id"]) for task in contract.get("tasks") or [] if isinstance(task, dict) and task.get("task_id")}
    returned_ids = [str(result.get("task_id") or "") for result in results]
    returned = set(returned_ids)
    if returned != expected:
        errors.append(f"task result mismatch: expected {sorted(expected)}, received {sorted(returned)}")
    duplicate_task_ids = sorted({task_id for task_id in returned_ids if returned_ids.count(task_id) > 1})
    if duplicate_task_ids:
        errors.append(f"duplicate task results: {duplicate_task_ids}")
    claims: dict[str, dict[str, Any]] = {}
    declared_reused_observation_ids: set[str] = set()
    conn = db_connect()
    for result in results:
        task_id = str(result.get("task_id") or "")
        if result.get("run_id") != initialized_run_id:
            errors.append(f"task {task_id or '<missing>'} result run_id does not match initialized run")
        if result.get("initialized_contract_hash") != initialized_contract_hash:
            errors.append(f"task {task_id or '<missing>'} result contract hash does not match initialized contract")
        result_claims = result.get("claims")
        result_sources = result.get("source_observation_ids")
        reused_sources = result.get("reused_observation_ids")
        limitations = result.get("limitations")
        if not isinstance(result_claims, list):
            errors.append(f"task {task_id or '<missing>'} requires a claims list")
            result_claims = []
        if not isinstance(result_sources, list) or any(not isinstance(item, str) or not item for item in result_sources):
            errors.append(f"task {task_id or '<missing>'} requires a source_observation_ids string list")
            result_sources = []
        if not isinstance(reused_sources, list) or any(not isinstance(item, str) or not item for item in reused_sources):
            errors.append(f"task {task_id or '<missing>'} requires a reused_observation_ids string list")
            reused_sources = []
        elif not set(reused_sources).issubset(set(result_sources)):
            errors.append(f"task {task_id or '<missing>'} reused_observation_ids must be a subset of source_observation_ids")
        declared_reused_observation_ids.update(reused_sources)
        if not isinstance(limitations, list) or any(not isinstance(item, str) for item in limitations):
            errors.append(f"task {task_id or '<missing>'} requires a limitations string list")
        for claim in result_claims:
            if not isinstance(claim, dict):
                errors.append(f"task {task_id or '<missing>'} returned a non-object claim")
                continue
            claim_id = str(claim.get("claim_id") or "")
            if not claim_id:
                errors.append(f"task {result.get('task_id')} returned a claim without claim_id")
                continue
            if not isinstance(claim.get("statement"), str) or not claim["statement"].strip():
                errors.append(f"claim {claim_id} requires a non-empty atomic statement")
            if claim.get("claim_kind") not in {"factual", "quantitative", "opinion", "interpretation"}:
                errors.append(f"claim {claim_id} has an unsupported claim_kind")
            if claim_id in claims:
                errors.append(f"duplicate claim_id {claim_id}")
            claims[claim_id] = claim
            evidence_ids = claim.get("evidence_observation_ids")
            if not isinstance(evidence_ids, list) or not evidence_ids or any(not isinstance(item, str) or not item for item in evidence_ids):
                errors.append(f"claim {claim_id} has no evidence observations")
            else:
                missing_from_packet = sorted(set(evidence_ids) - set(result_sources))
                if missing_from_packet:
                    errors.append(f"claim {claim_id} evidence is absent from task source_observation_ids: {missing_from_packet}")
                for observation_id in evidence_ids:
                    observation = conn.execute(
                        "SELECT run_id, status, content_hash, locator, metadata_json FROM source_observations WHERE observation_id=?",
                        (observation_id,),
                    ).fetchone()
                    if not observation:
                        errors.append(f"claim {claim_id} references unknown observation {observation_id}")
                        continue
                    if observation["status"] in {"incomplete", "legacy-provenance-unknown"} or not observation["content_hash"]:
                        errors.append(f"claim {claim_id} references incomplete evidence observation {observation_id}")
                    if observation["run_id"] != initialized_run_id and observation_id not in reused_sources:
                        errors.append(f"claim {claim_id} cross-run evidence must be declared in reused_observation_ids: {observation_id}")
                    metadata = json.loads(observation["metadata_json"] or "{}")
                    if not observation["locator"] and not metadata.get("locator_unknown_reason"):
                        errors.append(f"claim {claim_id} evidence lacks locator or locator_unknown_reason: {observation_id}")
            if claim.get("claim_kind") == "quantitative":
                receipt_id = claim.get("calculation_receipt_id")
                receipt = conn.execute(
                    "SELECT status, run_id, claim_id FROM calculation_receipts WHERE receipt_id=?", (receipt_id,)
                ).fetchone() if receipt_id else None
                if not receipt or receipt["status"] != "passed":
                    errors.append(f"quantitative claim {claim_id} lacks a passed calculation receipt")
                elif receipt["run_id"] != contract.get("run_id") or receipt["claim_id"] != claim_id:
                    errors.append(f"quantitative claim {claim_id} receipt does not match this run and claim")
    contradiction_pairs: set[tuple[str, str]] = set()
    for claim in claims.values():
        claim_id = str(claim["claim_id"])
        targets = claim.get("contradicts") or []
        if not isinstance(targets, list) or any(not isinstance(item, str) or not item for item in targets):
            errors.append(f"claim {claim_id} contradicts must be a string list")
            continue
        for other in targets:
            if other == claim_id:
                errors.append(f"claim {claim_id} cannot contradict itself")
            elif other not in claims:
                errors.append(f"claim {claim_id} contradicts unknown claim {other}")
            elif claim_id not in (claims[other].get("contradicts") or []):
                errors.append(f"contradiction must be symmetric: {claim_id} vs {other}")
            else:
                contradiction_pairs.add(_ordered_pair(claim_id, str(other)))
    reconciled_pairs = {
        _ordered_pair(str(item.get("left_claim_id")), str(item.get("right_claim_id")))
        for item in reconciliation_items
        if item.get("status") in {"preserved", "resolved", "basis_aligned"}
    }
    reconciliation_by_pair = {
        _ordered_pair(str(item.get("left_claim_id")), str(item.get("right_claim_id"))): item
        for item in reconciliation_items
        if item.get("left_claim_id") and item.get("right_claim_id")
    }
    for pair in sorted(contradiction_pairs - reconciled_pairs):
        errors.append(f"unreconciled contradiction: {pair[0]} vs {pair[1]}")
    conn.close()
    merged: dict[str, Any] = {
        "run_id": contract.get("run_id"),
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "claims": [claims[key] for key in sorted(claims)],
        "limitations": [item for result in results for item in result.get("limitations") or []],
    }
    run_id = str(contract.get("run_id") or _new_id("run"))
    attempts_dir = index_path("runs", run_id, "merge-attempts")
    attempts_dir.mkdir(parents=True, exist_ok=True)
    attempt_dir = attempts_dir / f"{datetime.now().astimezone().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    input_dir = attempt_dir / "inputs"
    input_dir.mkdir(parents=True, exist_ok=False)
    result_input_records: list[dict[str, Any]] = []
    for index, (source_path, raw_bytes, result) in enumerate(result_input_blobs, start=1):
        content_hash = "sha256:" + hashlib.sha256(raw_bytes).hexdigest()
        task_id = str(result.get("task_id") or "missing")
        snapshot_path = input_dir / f"result-{index:02d}-{task_id}-{content_hash[7:19]}.json"
        snapshot_path.write_bytes(raw_bytes)
        result_input_records.append({
            "task_id": task_id,
            "claim_ids": sorted(str(claim.get("claim_id")) for claim in result.get("claims") or [] if isinstance(claim, dict)),
            "source_observation_ids": result.get("source_observation_ids") or [],
            "original_path": str(source_path),
            "snapshot_path": str(snapshot_path),
            "content_hash": content_hash,
            "bytes": len(raw_bytes),
        })
    reconciliation_input_record: dict[str, Any] | None = None
    if reconciliation_input_blob:
        source_path, raw_bytes, reconciliation_manifest = reconciliation_input_blob
        content_hash = "sha256:" + hashlib.sha256(raw_bytes).hexdigest()
        snapshot_path = input_dir / f"reconciliation-{content_hash[7:19]}.json"
        snapshot_path.write_bytes(raw_bytes)
        reconciliation_input_record = {
            "original_path": str(source_path),
            "snapshot_path": str(snapshot_path),
            "content_hash": content_hash,
            "bytes": len(raw_bytes),
            "pairs": [
                [item.get("left_claim_id"), item.get("right_claim_id")]
                for item in reconciliation_manifest.get("reconciliations") or []
                if isinstance(item, dict)
            ],
        }
    merged["input_provenance"] = {
        "contract_hash": initialized_contract_hash,
        "results": result_input_records,
        "reconciliation": reconciliation_input_record,
    }
    attempt_path = attempt_dir / "attempt.json"
    attempt_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    if args.output:
        Path(args.output).expanduser().resolve().write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    actor = _actor_from_args(args)
    conn = db_connect()
    try:
        with conn:
            _ensure_run(
                conn,
                run_id,
                actor,
                objective=str(contract.get("objective") or "research merge"),
                intent=str(contract.get("intent") or ""),
                outcome=str(contract.get("outcome") or ""),
                contract=contract,
            )
            if not errors:
                run_entity = _graph_entity(conn, kind="run", canonical_key=run_id, label=run_id)
                for claim_id, claim in claims.items():
                    claim_entity = _graph_entity(
                        conn,
                        kind="claim",
                        canonical_key=f"{run_id}:{claim_id}",
                        label=str(claim.get("statement") or claim_id),
                        properties={"claim_kind": claim.get("claim_kind")},
                    )
                    for observation_id in claim.get("evidence_observation_ids") or []:
                        observation_entity = _graph_entity(
                            conn, kind="observation", canonical_key=str(observation_id), label=str(observation_id)
                        )
                        _graph_edge(
                            conn,
                            subject_id=claim_entity,
                            predicate="wasDerivedFrom",
                            object_id=observation_entity,
                            run_id=run_id,
                            evidence_observation_id=str(observation_id),
                        )
                        if observation_id in declared_reused_observation_ids:
                            _graph_edge(
                                conn,
                                subject_id=run_entity,
                                predicate="reusedObservation",
                                object_id=observation_entity,
                                run_id=run_id,
                                evidence_observation_id=str(observation_id),
                            )
                for left_id, right_id in contradiction_pairs:
                    left_entity = _graph_entity(conn, kind="claim", canonical_key=f"{run_id}:{left_id}", label=left_id)
                    right_entity = _graph_entity(conn, kind="claim", canonical_key=f"{run_id}:{right_id}", label=right_id)
                    _graph_edge(
                        conn,
                        subject_id=left_entity,
                        predicate="contradicts",
                        object_id=right_entity,
                        run_id=run_id,
                        status="preserved",
                    )
                    reconciliation = reconciliation_by_pair.get((left_id, right_id), {})
                    discrepancy_id = "disc-" + _sha256_text(f"{run_id}:{left_id}:{right_id}")[:32]
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO discrepancies
                          (discrepancy_id, left_claim_id, right_claim_id, discrepancy_type,
                           first_seen_at, last_seen_at, status, resolution_claim_id,
                           run_id, metadata_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            discrepancy_id, left_id, right_id,
                            str(reconciliation.get("type") or "contradiction"),
                            now_iso(), now_iso(), str(reconciliation.get("status") or "preserved"),
                            reconciliation.get("resolution_claim_id"), run_id,
                            _canonical_json(reconciliation),
                        ),
                    )
            conn.execute(
                "UPDATE research_runs SET status=? WHERE run_id=?",
                ("merged" if not errors else "merge_rejected", run_id),
            )
            _append_event(
                conn,
                event_type="run.merge_validated" if not errors else "run.merge_rejected",
                run_id=run_id,
                actor_type=actor["actor_type"],
                actor_id=actor["actor_id"],
                payload={
                    "attempt_path": str(attempt_path),
                    "attempt_hash": "sha256:" + _file_sha256(attempt_path),
                    "result_input_hashes": [item["content_hash"] for item in result_input_records],
                    "reconciliation_input_hash": reconciliation_input_record["content_hash"] if reconciliation_input_record else None,
                    "task_claim_map": {item["task_id"]: item["claim_ids"] for item in result_input_records},
                    "status": merged["status"],
                    "claim_ids": sorted(claims),
                    "errors": errors,
                },
                actor_snapshot=actor,
            )
    except (ValueError, sqlite3.Error) as exc:
        print(f"ERROR: could not persist merge audit: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()
    print(json.dumps(merged, indent=2, ensure_ascii=False))
    return 0 if not errors else 2


def _span_events(conn: sqlite3.Connection, run_id: str, span_id: str) -> list[sqlite3.Row]:
    matching: list[sqlite3.Row] = []
    for row in conn.execute(
        "SELECT * FROM audit_events WHERE run_id=? AND event_type IN ('run.stage_started', 'run.stage_finished') ORDER BY seq",
        (run_id,),
    ):
        payload = json.loads(row["payload_json"] or "{}")
        if payload.get("span_id") == span_id:
            matching.append(row)
    return matching


def cmd_run_stage(args: argparse.Namespace) -> int:
    ensure_db()
    actor = _actor_from_args(args)
    conn = db_connect()
    try:
        if not args.span_id.strip() or not args.stage.strip():
            raise ValueError("--span-id and --stage must be non-empty")
        run = conn.execute("SELECT run_id FROM research_runs WHERE run_id=?", (args.run_id,)).fetchone()
        if not run:
            raise ValueError(f"research run is not initialized: {args.run_id}")
        existing = _span_events(conn, args.run_id, args.span_id)
        event_types = {row["event_type"] for row in existing}
        if args.action == "start" and event_types:
            raise ValueError(f"stage span already exists: {args.span_id}")
        if args.action == "finish" and "run.stage_started" not in event_types:
            raise ValueError(f"stage span has no start event: {args.span_id}")
        if args.action == "finish" and "run.stage_finished" in event_types:
            raise ValueError(f"stage span is already finished: {args.span_id}")
        if args.action == "finish":
            start_row = next(row for row in existing if row["event_type"] == "run.stage_started")
            start_payload = json.loads(start_row["payload_json"] or "{}")
            if start_payload.get("stage") != args.stage:
                raise ValueError(f"stage finish does not match its start: {args.span_id}")
            for field in ("worker_id", "task_id"):
                if start_payload.get(field) and getattr(args, field) != start_payload[field]:
                    raise ValueError(f"stage finish {field} does not match its start: {args.span_id}")
        metadata = json.loads(args.metadata or "{}")
        metrics = json.loads(args.metrics or "{}")
        if not isinstance(metadata, dict) or not isinstance(metrics, dict):
            raise ValueError("--metadata and --metrics must decode to JSON objects")
        payload = {
            "span_id": args.span_id,
            "stage": args.stage,
            "worker_id": args.worker_id,
            "task_id": args.task_id,
            "model": args.model,
            "status": args.status if args.action == "finish" else "started",
            "metadata": metadata,
            "metrics": metrics if args.action == "finish" else {},
        }
        with conn:
            event = _append_event(
                conn,
                event_type=f"run.stage_{'started' if args.action == 'start' else 'finished'}",
                run_id=args.run_id,
                actor_type=actor["actor_type"],
                actor_id=actor["actor_id"],
                payload=payload,
                actor_snapshot=actor,
            )
    except (json.JSONDecodeError, sqlite3.Error, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()
    print(json.dumps(event, indent=2, ensure_ascii=False))
    return 0


def _event_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("stage event timestamp lacks timezone")
    return parsed


def _max_interval_concurrency(spans: list[dict[str, Any]]) -> int:
    endpoints: list[tuple[datetime, int]] = []
    for span in spans:
        endpoints.append((_event_datetime(span["started_at"]), 1))
        endpoints.append((_event_datetime(span["finished_at"]), -1))
    active = 0
    maximum = 0
    for _, delta in sorted(endpoints, key=lambda item: (item[0], item[1])):
        active += delta
        maximum = max(maximum, active)
    return maximum


def cmd_run_metrics(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    try:
        if not conn.execute("SELECT 1 FROM research_runs WHERE run_id=?", (args.run_id,)).fetchone():
            raise ValueError(f"research run is not initialized: {args.run_id}")
        starts: dict[str, dict[str, Any]] = {}
        completed: list[dict[str, Any]] = []
        errors: list[str] = []
        for row in conn.execute(
            "SELECT * FROM audit_events WHERE run_id=? AND event_type IN ('run.stage_started', 'run.stage_finished') ORDER BY seq",
            (args.run_id,),
        ):
            payload = json.loads(row["payload_json"] or "{}")
            span_id = str(payload.get("span_id") or "")
            if not span_id:
                errors.append(f"event {row['event_id']} lacks span_id")
                continue
            if row["event_type"] == "run.stage_started":
                starts[span_id] = {"row": row, "payload": payload}
                continue
            start = starts.get(span_id)
            if not start:
                errors.append(f"stage finish lacks start: {span_id}")
                continue
            started_at = _event_datetime(start["row"]["occurred_at"])
            finished_at = _event_datetime(row["occurred_at"])
            duration = (finished_at - started_at).total_seconds()
            if duration < 0:
                errors.append(f"stage finish predates start: {span_id}")
                continue
            completed.append({
                "span_id": span_id,
                "stage": str(payload.get("stage") or start["payload"].get("stage") or "unknown"),
                "worker_id": payload.get("worker_id") or start["payload"].get("worker_id"),
                "task_id": payload.get("task_id") or start["payload"].get("task_id"),
                "model": payload.get("model") or start["payload"].get("model"),
                "status": payload.get("status"),
                "started_at": start["row"]["occurred_at"],
                "finished_at": row["occurred_at"],
                "duration_seconds": round(duration, 6),
                "metrics": payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {},
            })
        finished_ids = {span["span_id"] for span in completed}
        incomplete = sorted(span_id for span_id in starts if span_id not in finished_ids)
    except (json.JSONDecodeError, sqlite3.Error, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()

    stages: dict[str, dict[str, Any]] = {}
    metric_totals: dict[str, Decimal] = {}
    for span in completed:
        aggregate = stages.setdefault(span["stage"], {"spans": 0, "total_seconds": 0.0, "max_seconds": 0.0})
        aggregate["spans"] += 1
        aggregate["total_seconds"] += span["duration_seconds"]
        aggregate["max_seconds"] = max(aggregate["max_seconds"], span["duration_seconds"])
        for name, value in span["metrics"].items():
            try:
                numeric = Decimal(str(value))
            except InvalidOperation:
                continue
            if not numeric.is_finite():
                continue
            metric_totals[name] = metric_totals.get(name, Decimal("0")) + numeric
    for aggregate in stages.values():
        aggregate["total_seconds"] = round(aggregate["total_seconds"], 6)

    observed_wall = 0.0
    if completed:
        observed_wall = (
            max(_event_datetime(span["finished_at"]) for span in completed)
            - min(_event_datetime(span["started_at"]) for span in completed)
        ).total_seconds()
    worker_spans = [span for span in completed if span.get("worker_id")]
    worker_critical = max((span["duration_seconds"] for span in worker_spans), default=0.0)
    fanout_window = 0.0
    if worker_spans:
        fanout_window = (
            max(_event_datetime(span["finished_at"]) for span in worker_spans)
            - min(_event_datetime(span["started_at"]) for span in worker_spans)
        ).total_seconds()
    merge_spans = [span for span in completed if span["stage"] == "merge"]
    merge_seconds = sum(span["duration_seconds"] for span in merge_spans)
    active_path = worker_critical + merge_seconds
    pipeline_window = fanout_window
    if worker_spans and merge_spans:
        pipeline_window = (
            max(_event_datetime(span["finished_at"]) for span in merge_spans)
            - min(_event_datetime(span["started_at"]) for span in worker_spans)
        ).total_seconds()
    longest_stage = max(stages, key=lambda name: stages[name]["total_seconds"]) if stages else None
    report = {
        "schema_version": "research-run-metrics.v1",
        "status": "complete" if not errors and not incomplete else "incomplete",
        "run_id": args.run_id,
        "span_count": len(completed),
        "incomplete_span_ids": incomplete,
        "errors": errors,
        "observed_wall_seconds": round(observed_wall, 6),
        "worker_critical_path_seconds": round(worker_critical, 6),
        "worker_fanout_window_seconds": round(fanout_window, 6),
        "max_concurrent_workers": _max_interval_concurrency(worker_spans),
        "worker_parallelism_ratio": round(
            sum(span["duration_seconds"] for span in worker_spans) / fanout_window, 6
        ) if fanout_window > 0 else None,
        "merge_seconds": round(merge_seconds, 6),
        "active_compute_path_seconds": round(active_path, 6),
        "fanout_merge_window_seconds": round(pipeline_window, 6),
        "handoff_and_idle_gap_seconds": round(max(0.0, pipeline_window - active_path), 6),
        "longest_stage_by_total": longest_stage,
        "stages": stages,
        "reported_metric_totals": {name: str(value) for name, value in sorted(metric_totals.items())},
        "spans": completed,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "complete" else 1


# ---------- review ----------

def _months_since(d_str: str | None) -> float:
    if not d_str:
        return 0.0
    try:
        d = date.fromisoformat(str(d_str))
    except ValueError:
        return 0.0
    delta = date.today() - d
    return delta.days / 30.4375


def _velocity_weight(v: str | None) -> float:
    return {"high": 2.0, "medium": 1.0, "low": 0.4}.get(v or "medium", 1.0)


def _compute_staleness(r: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    months = _months_since(r.get("reviewed"))
    vw = _velocity_weight(r.get("topic_velocity"))
    inbound = json.loads(r.get("inbound") or "[]")
    orphan = 1 if not inbound else 0
    # source_version_drift and corroboration_loss would require external checks;
    # default to 0 here (can be flagged manually in future)
    drift = 0
    loss = 0
    staleness = 0.4 * months * vw + 0.2 * drift + 0.2 * orphan + 0.2 * loss
    return staleness, {
        "months_since_reviewed": round(months, 2),
        "velocity_weight": vw,
        "orphan": orphan,
        "source_version_drift": drift,
        "corroboration_loss": loss,
    }


def cmd_review(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    rows = [dict(r) for r in conn.execute(
        "SELECT slug, title, path, reviewed, topic_velocity, inbound, topics "
        "FROM entries WHERE status != 'archived'"
    ).fetchall()]
    conn.close()
    scored: list[dict[str, Any]] = []
    for r in rows:
        s, breakdown = _compute_staleness(r)
        if args.topic and args.topic not in json.loads(r.get("topics") or "[]"):
            continue
        scored.append({**r, "staleness": round(s, 3), "breakdown": breakdown})
    scored.sort(key=lambda row: float(row["staleness"]), reverse=True)
    top = scored[: args.n]

    if args.json:
        print(json.dumps(top, indent=2, default=str))
    else:
        if not top:
            print("No entries.")
        else:
            print(f"{'Score':>6}  {'Slug':50s}  {'Reviewed':10s}  {'Velocity':8s}  Title")
            for r in top:
                print(f"{r['staleness']:6.2f}  {r['slug']:50s}  {r['reviewed']:10s}  "
                      f"{(r.get('topic_velocity') or 'medium'):8s}  {r['title']}")

    # Write review-due.md
    lines = ["# Review Due\n", f"Last rebuilt: {today_iso()}. Top {len(top)} stale entries.\n\n",
             "| Staleness | Slug | Title | Reviewed | Velocity | Orphan |\n",
             "|---|---|---|---|---|---|\n"]
    for r in top:
        breakdown = r.get("breakdown")
        orphan = breakdown.get("orphan") if isinstance(breakdown, dict) else 0
        lines.append(
            f"| {r['staleness']} | [`{r['slug']}`]({r['path']}) | {r['title']} | "
            f"{r['reviewed']} | {r.get('topic_velocity') or 'medium'} | "
            f"{'yes' if orphan else 'no'} |\n"
        )
    content_path("review-due.md").write_text("".join(lines))
    return 0


# ---------- compress ----------

def cmd_compress(args: argparse.Namespace) -> int:
    """Archive current Raw section for later reversal. Notes/TL;DR regeneration
    is left to the host agent via a subsequent edit; this subcommand handles the
    reversible archival mechanic."""
    ensure_db()
    conn = db_connect()
    row = conn.execute("SELECT path FROM entries WHERE slug = ?", (args.slug,)).fetchone()
    if not row:
        print(f"ERROR: no entry: {args.slug}", file=sys.stderr)
        conn.close()
        return 2
    entry_path = Path(row["path"])
    conn.close()

    if not entry_path.exists():
        print(f"ERROR: entry file missing: {entry_path}", file=sys.stderr)
        return 2

    text = entry_path.read_text()
    fm, body = parse_frontmatter(text)
    sections = split_sections(body)

    # Archive pre-compress Raw content
    archive_raw = content_path("archive", "raw", f"{args.slug}.md")
    archive_raw.parent.mkdir(parents=True, exist_ok=True)
    ts = now_iso()
    archive_content = (
        f"---\nslug: {args.slug}\npre_compress_timestamp: {ts}\n---\n"
        f"## Raw (pre-compression)\n\n{sections['raw']}\n"
    )
    if archive_raw.exists():
        # Append
        archive_raw.write_text(archive_raw.read_text() + f"\n---\n\n{archive_content}")
    else:
        archive_raw.write_text(archive_content)

    # Log compression event
    log = index_path("verifier-log", args.slug)
    log.mkdir(parents=True, exist_ok=True)
    (log / f"compress-{ts.replace(':', '-')}.json").write_text(json.dumps({
        "event": "compress",
        "timestamp": ts,
        "raw_bytes_before": len(sections["raw"]),
        "archived_to": str(archive_raw),
    }, indent=2))

    # Trim Raw to a placeholder for host-agent per-source summaries.
    new_raw = (
        f"> Raw compressed {today_iso()}. Originals: [[archive/raw/{args.slug}]]\n\n"
        f"[Host agent: regenerate per-source 2–3 sentence summaries here, preserving URLs and "
        f"capture dates from the archived Raw.]\n"
    )
    new_body = re.sub(
        r"(## Raw\n)(.*?)(?=\n## |\Z)",
        lambda m: f"{m.group(1)}\n{new_raw}\n",
        body,
        count=1,
        flags=re.DOTALL,
    )
    if new_body == body:
        # No Raw section found — append placeholder
        new_body = body.rstrip() + f"\n\n## Raw\n\n{new_raw}"
    fm["reviewed"] = today_iso()
    entry_path.write_text(dump_frontmatter(fm, new_body))
    _reingest(entry_path)
    print(f"Compressed {args.slug}")
    print(f"  Original Raw archived to: {archive_raw}")
    print(f"  Now have the host agent edit the entry to regenerate per-source summaries.")
    return 0


# ---------- extract (Omniparse-only router) ----------
#
# Single backend: @tyroneross/omniparse CLI (Node.js, user-authored, MIT).
# Handles PDF, Excel, PPTX, Python, and directories. HTML URLs and plain
# text formats (.md/.txt/.json/.yaml) are routed to host-native fetch/read tools
# with a clear message — no extraction needed.
#
# All successful extracts flow through a SHA-256 content-hash cache at
# <index-root>/.extract-cache/<hash>-<flags>.md so re-reads are instant.
# --no-cache bypasses.

EXTRACT_CACHE_DIR = index_path(".extract-cache")

# Extensions Omniparse handles (PDF included).
OMNIPARSE_EXTS = {
    ".pdf",
    ".xlsx", ".xls", ".csv", ".tsv", ".ods", ".xlsb",
    ".pptx",
    ".py",
}

# Read-native formats — caller should use the host's read tool directly.
READ_NATIVE_EXTS = {".md", ".markdown", ".txt", ".json", ".yaml", ".yml"}

# Vendored Omniparse CLI — self-contained build lives alongside this script.
# Re-vendor by following vendor/omniparse/BUILD.md.
PLUGIN_ROOT = Path(__file__).resolve().parent
VENDORED_OMNIPARSE_BIN = PLUGIN_ROOT / "vendor" / "omniparse" / "dist" / "bin" / "omniparse.js"


def _find_omniparse() -> list[str] | None:
    """Command list to invoke Omniparse CLI, or None if unavailable.
    Resolution order:
      1. `omniparse` on PATH (allows a user-installed global override).
      2. Vendored self-contained build at vendor/omniparse/dist/bin/omniparse.js
         invoked via `node`.
    The research plugin ships a pre-built, self-contained vendored copy, so
    (2) is the primary code path. No node_modules install is required.
    """
    exe = shutil.which("omniparse")
    if exe:
        return [exe]
    node = shutil.which("node")
    if node and VENDORED_OMNIPARSE_BIN.exists():
        return [node, str(VENDORED_OMNIPARSE_BIN)]
    return None


def _cache_flag_signature(args: argparse.Namespace) -> str:
    """Stable representation of the Omniparse-affecting flags for cache key."""
    parts = [
        f"f={args.format or ''}",
        f"r={int(bool(args.recursive))}",
        f"sheet={args.sheet or ''}",
        f"no_notes={int(bool(args.no_notes))}",
    ]
    return "|".join(parts)


def _cache_key(path: Path, flag_sig: str) -> str:
    """SHA-256 of file bytes + flag signature; hex. Stable across runs.
    For directories, hashes a listing of (name, size, mtime) tuples."""
    h = hashlib.sha256()
    if path.is_dir():
        entries = []
        for p in sorted(path.rglob("*")):
            if p.is_file():
                st = p.stat()
                entries.append(f"{p.relative_to(path)}:{st.st_size}:{int(st.st_mtime)}")
        h.update("\n".join(entries).encode())
    else:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    h.update(flag_sig.encode())
    return h.hexdigest()


def _cache_get(key: str) -> str | None:
    p = EXTRACT_CACHE_DIR / f"{key}.md"
    if p.exists():
        return p.read_text()
    return None


def _cache_put(key: str, markdown: str) -> None:
    EXTRACT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (EXTRACT_CACHE_DIR / f"{key}.md").write_text(markdown)


def _run_omniparse(args: argparse.Namespace, path: Path) -> tuple[int, str | None]:
    """Invoke Omniparse CLI. Returns (exit_code, captured_stdout_or_None).
    stdout is captured so we can both emit it and cache it. When --output is
    set, we pass -o through and return (rc, None)."""
    cmd_prefix = _find_omniparse()
    if cmd_prefix is None:
        print(
            "ERROR: Omniparse CLI not found. The vendored copy at\n"
            f"  {VENDORED_OMNIPARSE_BIN}\n"
            "is missing or `node` is not on PATH. Install Node.js >=18, or\n"
            "rebuild the vendored dist by following:\n"
            f"  {PLUGIN_ROOT / 'vendor' / 'omniparse' / 'BUILD.md'}",
            file=sys.stderr,
        )
        return 3, None

    cli = list(cmd_prefix) + [str(path)]
    if args.format:
        cli += ["-f", args.format]
    if args.recursive:
        cli += ["-r"]
    if args.output:
        cli += ["-o", args.output]
    if args.quiet:
        cli += ["-q"]
    if args.sheet:
        cli += ["--sheet", args.sheet]
    if args.no_notes:
        cli += ["--no-notes"]

    try:
        proc = subprocess.run(cli, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        print("ERROR: Omniparse timed out (180s)", file=sys.stderr)
        return 4, None
    except FileNotFoundError as e:
        print(f"ERROR: could not invoke Omniparse: {e}", file=sys.stderr)
        return 4, None

    if proc.stderr and not args.quiet:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        return proc.returncode, None
    if args.output:
        print(f"Wrote {args.output}", file=sys.stderr)
        return 0, None
    return 0, proc.stdout


def cmd_extract(args: argparse.Namespace) -> int:
    target = args.target

    if target.startswith(("http://", "https://")):
        print(
            "This is a URL. Use the host agent's WebFetch tool for HTML pages. If you "
            "downloaded the file locally, re-run with the local path.",
            file=sys.stderr,
        )
        return 2

    path = Path(target).expanduser().resolve()
    if not path.exists():
        print(f"ERROR: path does not exist: {path}", file=sys.stderr)
        return 2

    # Directory: Omniparse walks recursively when -r is passed.
    if path.is_dir():
        if not args.recursive:
            print(
                f"'{path}' is a directory. Pass -r/--recursive to process its "
                f"contents (Omniparse walks and concatenates).",
                file=sys.stderr,
            )
            return 2
        return _extract_and_cache(args, path)

    ext = path.suffix.lower()

    # Route HTML and plain-text formats back to host-native tools.
    if ext in (".html", ".htm"):
        print(
            "Local HTML file. Use WebFetch for URLs, or Read for a local HTML "
            "file — Omniparse does not add value here.",
            file=sys.stderr,
        )
        return 2
    if ext in READ_NATIVE_EXTS:
        print(
            f"'{ext}' files are best handled by the host's read tool directly "
            f"(no extraction needed).",
            file=sys.stderr,
        )
        return 2
    if ext not in OMNIPARSE_EXTS:
        supported = ", ".join(sorted(OMNIPARSE_EXTS))
        print(
            f"Extension '{ext}' is not supported by Omniparse. Supported: "
            f"{supported}. For .md/.txt/.json/.yaml use the host's read tool.",
            file=sys.stderr,
        )
        return 2

    return _extract_and_cache(args, path)


def _extract_and_cache(args: argparse.Namespace, path: Path) -> int:
    """Cache-aware Omniparse dispatch. Streams stdout OR writes --output."""
    flag_sig = _cache_flag_signature(args)
    use_cache = not args.no_cache and args.output is None

    if use_cache:
        key = _cache_key(path, flag_sig)
        cached = _cache_get(key)
        if cached is not None:
            if not args.quiet:
                print(f"(cache hit: {key[:12]})", file=sys.stderr)
            sys.stdout.write(cached)
            return 0

    rc, captured = _run_omniparse(args, path)
    if rc != 0:
        return rc

    if captured is not None:
        sys.stdout.write(captured)
        if use_cache:
            _cache_put(_cache_key(path, flag_sig), captured)
    return 0


# ---------- recategorize ----------

def _infer_subprefix(slug: str, top: str) -> str:
    """Given a slug like 'prompting.techniques.few-shot', return 'prompting.techniques' (one level deeper than top)."""
    rest = slug[len(top) + 1:] if slug.startswith(top + ".") else slug
    parts = rest.split(".")
    if len(parts) <= 1:
        # No deeper segment; use the slug itself as a leaf marker
        return f"{top}.<leaf>"
    return f"{top}.{parts[0]}"


def cmd_recategorize(args: argparse.Namespace) -> int:
    """Read-only suggestion mode by default. With --apply --plan <file>, perform moves."""
    ensure_db()
    conn = db_connect()
    rows = [dict(r) for r in conn.execute(
        "SELECT slug, title, topics, tldr FROM entries WHERE status != 'archived' ORDER BY slug"
    ).fetchall()]
    conn.close()

    by_top: dict[str, list[dict]] = {}
    for r in rows:
        by_top.setdefault(top_level_topic(r["slug"]), []).append(r)

    suggestions: list[dict] = []
    for top, entries in sorted(by_top.items()):
        if len(entries) <= args.threshold:
            continue
        # Cluster by inferred sub-prefix
        clusters: dict[str, list[str]] = {}
        for e in entries:
            sub = _infer_subprefix(e["slug"], top)
            clusters.setdefault(sub, []).append(e["slug"])
        suggestion = {
            "top_level": top,
            "current_count": len(entries),
            "proposed_clusters": {k: sorted(v) for k, v in sorted(clusters.items(), key=lambda x: -len(x[1]))},
        }
        suggestions.append(suggestion)

    if args.json:
        print(json.dumps({"threshold": args.threshold, "suggestions": suggestions}, indent=2))
        return 0

    if not suggestions:
        print(f"No top-level topics exceed threshold of {args.threshold} entries.")
        return 0

    print(f"# Recategorization suggestions (threshold: {args.threshold} entries per top-level)\n")
    for s in suggestions:
        proposals = ", ".join(f"{k}.* ({len(v)})" for k, v in s["proposed_clusters"].items())
        print(f"- {s['top_level']}/ has {s['current_count']} entries \u2014 consider splitting: {proposals}")
        for cluster_name, slugs in s["proposed_clusters"].items():
            print(f"    {cluster_name}:")
            for sl in slugs:
                print(f"      - {sl}")
        print()

    if args.apply:
        if not args.plan:
            print("ERROR: --apply requires --plan <file.json> with explicit slug renames.", file=sys.stderr)
            return 2
        plan_path = Path(args.plan).expanduser().resolve()
        if not plan_path.exists():
            print(f"ERROR: plan file not found: {plan_path}", file=sys.stderr)
            return 2
        try:
            plan = json.loads(plan_path.read_text())
        except json.JSONDecodeError as e:
            print(f"ERROR: invalid JSON in plan: {e}", file=sys.stderr)
            return 2
        if not isinstance(plan, dict) or "renames" not in plan:
            print("ERROR: plan must be {\"renames\": {\"old.slug\": \"new.slug\", ...}}", file=sys.stderr)
            return 2
        renames = plan["renames"]
        moved = 0
        conn = db_connect()
        for old_slug, new_slug in renames.items():
            row = conn.execute("SELECT path FROM entries WHERE slug = ?", (old_slug,)).fetchone()
            if not row:
                print(f"  SKIP: {old_slug} (not in DB)")
                continue
            old_path = Path(row["path"])
            if not old_path.exists():
                print(f"  SKIP: {old_slug} (file missing)")
                continue
            new_top = top_level_topic(new_slug)
            new_path = content_path("topics", new_top, f"{new_slug}.md")
            new_path.parent.mkdir(parents=True, exist_ok=True)
            text = old_path.read_text()
            fm, body = parse_frontmatter(text)
            fm["slug"] = new_slug
            new_path.write_text(dump_frontmatter(fm, body))
            # Leave a redirect stub at the old location
            old_path.write_text(
                f"---\nstatus: archived\nredirect: ../../topics/{new_top}/{new_slug}.md\n"
                f"archived: {today_iso()}\n---\nMoved to [[{new_slug}]] via recategorize.\n"
            )
            conn.execute(
                "UPDATE entries SET slug = ?, path = ? WHERE slug = ?",
                (new_slug, str(new_path), old_slug),
            )
            moved += 1
            print(f"  MOVED: {old_slug} -> {new_slug}")
        conn.commit()
        conn.close()
        if moved:
            _rebuild_indexes()
            _rebuild_portfolio()
        print(f"\nApplied {moved} renames.")
    else:
        print("Read-only mode. To apply, build a JSON plan and re-run with: --apply --plan <plan.json>")
        print('Plan format: {"renames": {"old.slug": "new.slug", ...}}')
    return 0


# ---------- ingest ----------

def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\s.-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-.")
    return s or "untitled"


def _draft_entry_from_md(path: Path, project: str | None, topics: list[str]) -> dict:
    """Deterministic extraction: title from first H1 or filename, slug from filename."""
    text = path.read_text()
    # If it already has frontmatter, keep it; otherwise derive
    fm, body = parse_frontmatter(text)
    if not fm:
        body = text
        h1 = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
        title = h1.group(1).strip() if h1 else path.stem
        slug_base = _slugify(path.stem)
        # If no topic specified, use first slug segment or "ingest"
        top = topics[0] if topics else "ingest"
        slug = slug_base if "." in slug_base else f"{top}.{slug_base}"
        fm = {
            "slug": slug,
            "title": title,
            "topics": topics or [top],
            "projects": [project] if project else [],
            "status": "fleeting",
            "workflow": "general",
            "created": today_iso(),
            "reviewed": today_iso(),
            "topic_velocity": "medium",
            "tags": [],
            "confidence": "inferred",
            "corroboration": 0,
            "sources": [],
            "related": [],
            "inbound": [],
        }
    else:
        # Augment existing frontmatter
        if project and project not in (fm.get("projects") or []):
            fm.setdefault("projects", []).append(project)
        for t in topics:
            if t not in (fm.get("topics") or []):
                fm.setdefault("topics", []).append(t)
    # Ensure body has the three sections; if not, treat existing body as Notes
    if "## TL;DR" not in body and "## Notes" not in body and "## Raw" not in body:
        body = (
            "## TL;DR\n\n_Pending synthesis._\n\n"
            "## Notes\n\n" + body.strip() + "\n\n"
            "## Raw\n\n_Source preserved at ingest path._\n"
        )
    return {"frontmatter": fm, "body": body, "source_path": str(path)}


def cmd_ingest(args: argparse.Namespace) -> int:
    src = Path(args.path).expanduser().resolve()
    if not src.exists():
        print(f"ERROR: path not found: {src}", file=sys.stderr)
        return 2

    if args.inbox:
        # Just copy raw files to the content-root inbox, no draft, no save
        ensure_layout()
        inbox = content_path("inbox")
        inbox.mkdir(parents=True, exist_ok=True)
        copied = 0
        files = [src] if src.is_file() else [p for p in src.rglob("*.md")]
        for f in files:
            dest = inbox / f.name
            # If collision, suffix
            n = 2
            while dest.exists():
                dest = inbox / f"{f.stem}-{n}{f.suffix}"
                n += 1
            shutil.copy2(f, dest)
            copied += 1
            print(f"  inbox: {dest}")
        print(f"\nCopied {copied} file(s) to {inbox}")
        return 0

    topics = [t.strip() for t in (args.topics or "").split(",") if t.strip()]
    files = [src] if src.is_file() else sorted(src.rglob("*.md"))
    if not files:
        print(f"No markdown files found at {src}", file=sys.stderr)
        return 1

    drafts: list[dict] = []
    for f in files:
        if not f.suffix.lower() in (".md", ".markdown"):
            continue
        draft = _draft_entry_from_md(f, args.project, topics)
        drafts.append(draft)

    if args.json:
        print(json.dumps(drafts, indent=2, default=str))
    else:
        for d in drafts:
            fm = d["frontmatter"]
            print(f"\n--- DRAFT: {fm['slug']} (from {d['source_path']}) ---")
            print(dump_frontmatter(fm, d["body"]))

    if args.save:
        ensure_layout()
        ensure_db()
        saved = 0
        for d in drafts:
            fm = d["frontmatter"]
            tmp = content_path("inbox", f".ingest-{fm['slug']}.md")
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(dump_frontmatter(fm, d["body"]))
            cmd_save(argparse.Namespace(
                file=str(tmp),
                move_source=True,
                skip_symlink=False,
                skip_index=False,
                no_index=False,
                with_project_index=False,
            ))
            saved += 1
        print(f"\nSaved {saved} draft(s).")
    else:
        print("\n(dry run \u2014 pass --save to persist; or pipe to /research:save manually)")
    return 0


# ---------- evaluation audit ----------

def _normalized_sha256(value: object) -> str:
    text = str(value or "").strip().lower()
    return text.removeprefix("sha256:")


def _evaluation_file(root: Path, base: Path, raw_path: object) -> Path:
    relative = Path(str(raw_path or ""))
    if not str(relative) or relative.is_absolute():
        raise ValueError(f"evaluation artifact path must be relative: {raw_path!r}")
    target = (base / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"evaluation artifact escapes root: {raw_path!r}")
    return target


def _artifact_references(value: object) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if value.get("path") and value.get("sha256"):
            found.append(value)
        for child in value.values():
            found.extend(_artifact_references(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_artifact_references(child))
    return found


def _check_sha_manifest(root: Path, manifest: Path) -> tuple[int, list[str]]:
    checked = 0
    errors: list[str] = []
    for line_number, raw_line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or len(_normalized_sha256(parts[0])) != 64:
            errors.append(f"{manifest}:{line_number}: malformed SHA-256 row")
            continue
        relative = parts[1].lstrip("* ")
        try:
            target = _evaluation_file(root, manifest.parent, relative)
        except ValueError as exc:
            errors.append(f"{manifest}:{line_number}: {exc}")
            continue
        checked += 1
        if not target.is_file():
            errors.append(f"{manifest}:{line_number}: missing {relative}")
        elif _file_sha256(target) != _normalized_sha256(parts[0]):
            errors.append(f"{manifest}:{line_number}: hash mismatch {relative}")
    return checked, errors


def cmd_eval_check(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(json.dumps({"status": "invalid", "errors": [f"evaluation root is not a directory: {root}"]}, indent=2))
        return 2

    errors: list[str] = []
    manifest_files = sorted(root.rglob("MANIFEST.sha256"))
    manifest_artifacts = 0
    for manifest in manifest_files:
        try:
            checked, manifest_errors = _check_sha_manifest(root, manifest)
        except OSError as exc:
            checked, manifest_errors = 0, [f"{manifest}: {exc}"]
        manifest_artifacts += checked
        errors.extend(manifest_errors)

    trial_files = sorted(root.rglob("trial.json"))
    trial_artifacts = 0
    queries: set[str] = set()
    arms: set[str] = set()
    for trial_path in trial_files:
        try:
            trial = json.loads(trial_path.read_text(encoding="utf-8"))
            if not isinstance(trial, dict):
                raise ValueError("trial must be a JSON object")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{trial_path}: {exc}")
            continue
        if trial.get("query_id"):
            queries.add(str(trial["query_id"]))
        if trial.get("arm_id"):
            arms.add(str(trial["arm_id"]))
        for reference in _artifact_references(trial.get("artifacts")):
            trial_artifacts += 1
            try:
                target = _evaluation_file(root, trial_path.parent, reference["path"])
            except ValueError as exc:
                errors.append(f"{trial_path}: {exc}")
                continue
            expected = _normalized_sha256(reference["sha256"])
            if len(expected) != 64:
                errors.append(f"{trial_path}: malformed artifact hash for {reference['path']}")
            elif not target.is_file():
                errors.append(f"{trial_path}: missing artifact {reference['path']}")
            elif _file_sha256(target) != expected:
                errors.append(f"{trial_path}: hash mismatch {reference['path']}")

    audit_files = sorted((root / "audits").rglob("*.json")) if (root / "audits").is_dir() else []
    valid_audits = 0
    for audit_path in audit_files:
        try:
            payload = json.loads(audit_path.read_text(encoding="utf-8"))
            if not isinstance(payload, (dict, list)):
                raise ValueError("audit JSON must be an object or list")
            valid_audits += 1
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{audit_path}: {exc}")

    for required_query in args.require_query or []:
        if required_query not in queries:
            errors.append(f"required query is absent from trial manifests: {required_query}")
    if args.min_independent_audits and valid_audits < args.min_independent_audits:
        errors.append(
            f"independent audit count {valid_audits} is below required {args.min_independent_audits}"
        )

    report = {
        "schema_version": "research-eval-check.v1",
        "status": "pass" if not errors else "fail",
        "root": str(root),
        "manifest_files": len(manifest_files),
        "manifest_artifacts_checked": manifest_artifacts,
        "trial_files": len(trial_files),
        "trial_artifacts_checked": trial_artifacts,
        "queries": sorted(queries),
        "arms": sorted(arms),
        "independent_audit_json_files": valid_audits,
        "errors": errors,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not errors else 2


# ---------- main / argparse ----------

def main() -> int:
    ap = argparse.ArgumentParser(prog="research.py", description="Central research knowledge base.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="Bootstrap research content and index roots")
    sp.add_argument("--refresh-seeds", action="store_true", help="Re-apply seed data (preserves manual overrides)")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("save", help="Persist a markdown entry file")
    sp.add_argument("--file", required=True, help="Path to entry markdown with frontmatter")
    sp.add_argument("--move-source", action="store_true", help="Delete source file after copy to canonical path")
    sp.add_argument("--skip-symlink", action="store_true", help="Do not create project copy/symlink (used by hook)")
    sp.add_argument("--skip-index", action="store_true", help="Do not rebuild any indexes (legacy alias of --no-index)")
    sp.add_argument("--no-index", action="store_true", help="Skip per-project index + PORTFOLIO.md regen on this save")
    sp.add_argument(
        "--with-project-index",
        action="store_true",
        help="Opt-in: also regenerate <project>/RossLabs-Research.md (writes into the project dir)",
    )
    sp.add_argument("--run-id", help="Research run identifier; generated when omitted")
    sp.add_argument("--actor-type", help="Actor class, such as human, host-agent, or script")
    sp.add_argument("--actor-id", help="Stable actor identifier; defaults to unknown")
    sp.add_argument("--host", help="Host runtime name; defaults to unknown")
    sp.add_argument("--session-id", help="Host session identifier; defaults to unknown")
    sp.add_argument("--tool-version", help="Plugin/runtime version; defaults to unknown")
    sp.set_defaults(func=cmd_save)

    sp = sub.add_parser("search", help="Full-text search (FTS5 + BM25)")
    sp.add_argument("query")
    sp.add_argument("--tag")
    sp.add_argument("--topic")
    sp.add_argument("--project")
    sp.add_argument("--status")
    sp.add_argument("--entries-only", action="store_true", help="Search only canonical saved entries, not linked external files")
    sp.add_argument("--fts-query", action="store_true", help="Treat query as raw FTS5 syntax instead of safe plain text")
    sp.add_argument("-n", type=int, default=20)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("depth", help="Classify a research request as light, standard, or deep")
    sp.add_argument("query", help="Research topic or question to classify")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_depth)

    sp = sub.add_parser("list", help="Recent entries")
    sp.add_argument("-n", type=int, default=20)
    sp.add_argument("--status")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("link", help="Retroactive project symlink")
    sp.add_argument("slug")
    sp.add_argument("project_path", nargs="?", help="Defaults to cwd")
    sp.set_defaults(func=cmd_link)

    sp = sub.add_parser(
        "link-project",
        help="Register an existing project research directory (v0.3.1). "
        "Walks recursively, extracts title+summary, symlinks into the content-root projects dir.",
    )
    sp.add_argument("name", help="Short project name used for the symlink dir and registry key")
    sp.add_argument("path_arg", nargs="?", help="Path to the research directory to link")
    sp.add_argument("--path", help="Absolute path to the research directory to link")
    sp.add_argument("--no-index", action="store_true", help="Skip PORTFOLIO.md regen on this call")
    sp.set_defaults(func=cmd_link_project)

    sp = sub.add_parser("sync", help="Rebuild SQLite from canonical topic markdown")
    sp.add_argument("--prune-missing", action="store_true", help="Delete DB rows whose slug is not present under topics/")
    sp.add_argument("--no-index", action="store_true", help="Skip markdown index and symlink refresh after DB sync")
    sp.set_defaults(func=cmd_sync)

    sp = sub.add_parser("index", help="Rebuild markdown indexes + MOCs")
    sp.set_defaults(func=cmd_index)

    sp = sub.add_parser("archive", help="Move entry to archive, leave redirect stub")
    sp.add_argument("slug")
    sp.set_defaults(func=cmd_archive)

    sp = sub.add_parser("score", help="Inspect or set a domain's tier")
    sp.add_argument("domain", help="Domain or URL")
    sp.add_argument("--tier", choices=["T1", "T2", "T3", "T4"])
    sp.add_argument("--reason")
    sp.set_defaults(func=cmd_score)

    sp = sub.add_parser("verify", help="Run claim verification on an entry")
    sp.add_argument("slug")
    sp.add_argument("--atoms", help="Path to atoms JSON (default: <entry-dir>/<slug>.atoms.json)")
    sp.add_argument("--atom", help="Run a single atom by atom_id")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_verify)

    sp = sub.add_parser("table-profile", help="Profile a CSV/TSV/JSON table for quantitative analysis")
    sp.add_argument("input", help="Path to .csv, .tsv, .json, or .jsonl")
    sp.add_argument("--sample", type=int, default=5, help="Number of sample rows to include")
    sp.add_argument("-o", "--output", help="Write profile JSON to this path")
    sp.set_defaults(func=cmd_table_profile)

    sp = sub.add_parser("db-profile", help="Profile a SQLite database schema and tables")
    sp.add_argument("db", help="Path to .sqlite, .sqlite3, or .db")
    sp.add_argument("--sample", type=int, default=5, help="Number of sample rows per table")
    sp.add_argument("-o", "--output", help="Write profile JSON to this path")
    sp.set_defaults(func=cmd_db_profile)

    sp = sub.add_parser("analyze-plan", help="Create a stdlib Python analysis plan and script")
    sp.add_argument("--input", action="append", required=True, help="Input file; repeat for multiple inputs")
    sp.add_argument("--question", required=True, help="Quantitative/database question to answer")
    sp.add_argument("--name", help="Run name suffix")
    sp.add_argument("--sample", type=int, default=5, help="Sample rows for profiles")
    sp.add_argument("--out-dir", help="Write analysis artifacts to this directory")
    sp.set_defaults(func=cmd_analyze_plan)

    sp = sub.add_parser("analyze-run", help="Run a generated quantitative analysis plan")
    sp.add_argument("--plan", required=True, help="Path to analysis-plan.yaml")
    sp.add_argument("--timeout", type=int, default=30, help="Execution timeout in seconds")
    sp.add_argument("--allow-modified-script", action="store_true", help="Run even if analysis.py differs from the plan hash")
    sp.set_defaults(func=cmd_analyze_run)

    sp = sub.add_parser("source-record", help="Append one source capture manifest to the audit ledger")
    sp.add_argument("--manifest", required=True, help="JSON capture manifest produced by a host browser or local extractor")
    sp.add_argument("--run-id", help="Research run identifier")
    sp.add_argument("--entry-slug", help="Entry that uses this capture")
    sp.add_argument("--actor-type")
    sp.add_argument("--actor-id")
    sp.add_argument("--host")
    sp.add_argument("--session-id")
    sp.add_argument("--tool-version")
    sp.set_defaults(func=cmd_source_record)

    sp = sub.add_parser("source-index", help="Rebuild the overall source ledger and central project indexes")
    sp.set_defaults(func=cmd_source_index)

    sp = sub.add_parser("legacy-source-import", help="Normalize past entry source lists with provenance explicitly unknown")
    sp.add_argument("--apply", action="store_true", help="Write normalized observations; default is a dry-run count")
    sp.set_defaults(func=cmd_legacy_source_import)

    sp = sub.add_parser("trust-record", help="Append dated, topic-scoped trust observations")
    sp.add_argument("--manifest", required=True)
    sp.add_argument("--run-id")
    sp.add_argument("--actor-type")
    sp.add_argument("--actor-id")
    sp.add_argument("--host")
    sp.add_argument("--session-id")
    sp.add_argument("--tool-version")
    sp.set_defaults(func=cmd_trust_record)

    sp = sub.add_parser("graph-export", help="Export the research dependency graph as Mermaid or JSON")
    sp.add_argument("--run-id", help="Restrict edges to one research run")
    sp.add_argument("--format", choices=["mermaid", "json"], default="mermaid")
    sp.add_argument("--output")
    sp.set_defaults(func=cmd_graph_export)

    sp = sub.add_parser("traversal-record", help="Apply run limits and append accepted/rejected deep-link frontier records")
    sp.add_argument("--manifest", required=True)
    sp.add_argument("--run-id")
    sp.add_argument("--actor-type")
    sp.add_argument("--actor-id")
    sp.add_argument("--host")
    sp.add_argument("--session-id")
    sp.add_argument("--tool-version")
    sp.set_defaults(func=cmd_traversal_record)

    sp = sub.add_parser("doctor", help="Audit event integrity, index parity, provenance, and malformed entries")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("calculate", help="Execute a deterministic quantitative claim spec and append a receipt")
    sp.add_argument("--spec", required=True, help="JSON calculation specification")
    sp.add_argument("--actor-type")
    sp.add_argument("--actor-id")
    sp.add_argument("--host")
    sp.add_argument("--session-id")
    sp.add_argument("--tool-version")
    sp.set_defaults(func=cmd_calculate)

    sp = sub.add_parser("run-init", help="Validate a vendor-neutral research contract and emit task packets")
    sp.add_argument("--contract", required=True, help="JSON research run contract")
    sp.add_argument("--actor-type")
    sp.add_argument("--actor-id")
    sp.add_argument("--host")
    sp.add_argument("--session-id")
    sp.add_argument("--tool-version")
    sp.set_defaults(func=cmd_run_init)

    sp = sub.add_parser("run-validate", help="Validate a vendor-neutral research run contract")
    sp.add_argument("--contract", required=True)
    sp.set_defaults(func=cmd_run_validate)

    sp = sub.add_parser("run-merge", help="Validate and deterministically order worker research results")
    sp.add_argument("--contract", required=True)
    sp.add_argument("--result", action="append", required=True, help="Worker result JSON; repeat for each task")
    sp.add_argument("--reconciliation", help="Append-only reconciliation manifest bound to run_id and initialized contract hash")
    sp.add_argument("--output", help="Optional merged JSON output path")
    sp.add_argument("--actor-type")
    sp.add_argument("--actor-id")
    sp.add_argument("--host")
    sp.add_argument("--session-id")
    sp.add_argument("--tool-version")
    sp.set_defaults(func=cmd_run_merge)

    sp = sub.add_parser("run-stage", help="Append a timed orchestration stage start or finish event")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--span-id", required=True, help="Stable unique id shared by the start and finish events")
    sp.add_argument("--stage", required=True, help="Stage name such as plan, source, worker, merge, or audit")
    sp.add_argument("--action", choices=["start", "finish"], required=True)
    sp.add_argument("--worker-id")
    sp.add_argument("--task-id")
    sp.add_argument("--model")
    sp.add_argument("--status", default="passed")
    sp.add_argument("--metadata", default="{}", help="JSON object with vendor-neutral stage context")
    sp.add_argument("--metrics", default="{}", help="JSON object with reported tokens, tools, cost, or other counters")
    sp.add_argument("--actor-type")
    sp.add_argument("--actor-id")
    sp.add_argument("--host")
    sp.add_argument("--session-id")
    sp.add_argument("--tool-version")
    sp.set_defaults(func=cmd_run_stage)

    sp = sub.add_parser("run-metrics", help="Calculate stage timing, fan-out critical path, merge overhead, and reported counters")
    sp.add_argument("--run-id", required=True)
    sp.set_defaults(func=cmd_run_metrics)

    sp = sub.add_parser("eval-check", help="Verify frozen external evaluation artifacts and independent audit records")
    sp.add_argument("--root", required=True, help="External evaluation root; no files are written")
    sp.add_argument("--require-query", action="append", help="Query id that must appear; repeat as needed")
    sp.add_argument("--min-independent-audits", type=int, default=0)
    sp.set_defaults(func=cmd_eval_check)

    sp = sub.add_parser("review", help="Surface stale entries")
    sp.add_argument("-n", type=int, default=20)
    sp.add_argument("--topic")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_review)

    sp = sub.add_parser("compress", help="Archive Raw, prepare for a host-agent rewrite")
    sp.add_argument("slug")
    sp.set_defaults(func=cmd_compress)

    sp = sub.add_parser("recategorize", help="Suggest top-level taxonomy splits (read-only by default)")
    sp.add_argument("--threshold", type=int, default=8, help="Min entries per top-level before suggesting a split")
    sp.add_argument("--apply", action="store_true", help="Apply slug renames from --plan")
    sp.add_argument("--plan", help="JSON file with {\"renames\": {old: new, ...}}")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_recategorize)

    sp = sub.add_parser("ingest", help="Bulk ingest markdown files; print drafts (or --save)")
    sp.add_argument("path", help="File or directory of .md files")
    sp.add_argument("--project", help="Auto-tag drafts with this project")
    sp.add_argument("--topics", help="Comma-separated topics for drafts")
    sp.add_argument("--inbox", action="store_true", help="Just copy files to the content-root inbox, no draft/save")
    sp.add_argument("--save", action="store_true", help="Persist each draft via the normal save flow")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_ingest)

    sp = sub.add_parser(
        "extract",
        help="Extract PDF / Excel / PPTX / Python / directory via Omniparse (cached)",
        description=(
            "Routes all extraction through @tyroneross/omniparse. HTML URLs and "
            ".md/.txt/.json/.yaml files are rejected with a pointer to "
            "the host agent's WebFetch/Read tools. Results are cached at "
            "<index-root>/.extract-cache/ keyed by file SHA-256 + flag signature."
        ),
    )
    sp.add_argument("target", help="Local file path or directory (URLs are rejected — use WebFetch)")
    sp.add_argument("--no-cache", action="store_true", help="Skip content-hash cache (force re-extract)")
    sp.add_argument("-f", "--format", choices=["markdown", "text", "json"], help="Output format for Omniparse (default: markdown)")
    sp.add_argument("-o", "--output", help="Write to file instead of stdout")
    sp.add_argument("-r", "--recursive", action="store_true", help="Process directory contents (required for directories)")
    sp.add_argument("-q", "--quiet", action="store_true", help="Suppress progress messages")
    sp.add_argument("--sheet", help="Excel: specific sheet name")
    sp.add_argument("--no-notes", action="store_true", help="PPTX: exclude speaker notes")
    sp.set_defaults(func=cmd_extract)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
