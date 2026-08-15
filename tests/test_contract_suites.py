#!/usr/bin/env python3
"""pytest wrapper that makes every `*_check.py` suite fail the run when it fails.

Each check exposes `main() -> int` and is executed standalone as
`python3 tests/<name>_check.py`, where a non-zero return becomes the process
exit code. Under pytest, a collected `main()` returning 1 is only a warning —
the run still reports green. This wrapper asserts on the returned status so a
broken contract turns the suite red on both paths.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
CHECKS = sorted(p.name for p in TESTS_DIR.glob("*_check.py"))

assert CHECKS, "no *_check.py suites found — discovery is broken"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_check_{name[:-3]}", TESTS_DIR / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("check", CHECKS)
def test_contract_suite(check: str, capsys) -> None:
    module = _load(check)
    main = getattr(module, "main", None)
    assert callable(main), f"{check} exposes no callable main()"
    try:
        status = main()
    except SystemExit as exc:  # a check that exits directly
        status = exc.code
    output = capsys.readouterr().out
    assert status in (0, None), f"{check} failed (status={status}):\n{output}"


def test_every_check_is_wrapped() -> None:
    """Guards against a new suite landing outside this wrapper."""
    on_disk = {p.name for p in TESTS_DIR.glob("*_check.py")}
    assert on_disk == set(CHECKS), (
        f"suite set changed during collection: {on_disk ^ set(CHECKS)}"
    )
