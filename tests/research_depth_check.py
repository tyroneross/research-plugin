#!/usr/bin/env python3
"""Regression checks for deterministic research depth classification."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research.py"


def classify(query: str) -> dict:
    proc = subprocess.run(
        ["python3", str(RESEARCH), "depth", query, "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"depth command failed for {query!r}: {proc.stderr}")
    return json.loads(proc.stdout)


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []

    light = classify("what is Redis?")
    require(light["depth"] == "light", f"expected light, got {light}", failures)
    require(light["persist"] is False, f"light task should not persist: {light}", failures)

    default_research = classify("just research Redis")
    require(
        default_research["depth"] == "standard",
        f"plain research request should default to standard: {default_research}",
        failures,
    )
    require(
        default_research["source_budget"] == {"target": 5, "minimum": 3, "maximum": 8},
        f"standard research should use expanded source budget: {default_research}",
        failures,
    )
    require(
        "coverage" in default_research,
        f"standard research should include coverage requirements: {default_research}",
        failures,
    )

    quick_research = classify("quick research Redis")
    require(
        quick_research["depth"] == "light",
        f"explicit quick research should stay light: {quick_research}",
        failures,
    )

    explicit_deep = classify("deep research Redis")
    require(
        explicit_deep["depth"] == "deep",
        f"explicit deep request should classify deep: {explicit_deep}",
        failures,
    )
    require(
        explicit_deep["source_budget"] == {"target": 10, "minimum": 7, "maximum": 15},
        f"deep research should use expanded source budget: {explicit_deep}",
        failures,
    )

    standard = classify("latest OpenAI API pricing today")
    require(standard["depth"] == "standard", f"expected standard, got {standard}", failures)
    require(standard["web_required"] is True, f"freshness task should require web: {standard}", failures)

    deep = classify(
        "compare Redis vs Dragonfly for session store architecture risks and recommend a strategy"
    )
    require(deep["depth"] == "deep", f"expected deep, got {deep}", failures)
    require(deep["persist"] is True, f"deep task should persist: {deep}", failures)
    require(deep["source_budget"]["minimum"] >= 7, f"deep task source floor too low: {deep}", failures)
    require(
        deep["coverage"]["source_mix"]["counter_evidence"] >= 2,
        f"deep task should require counter-evidence coverage: {deep}",
        failures,
    )

    expansive = classify("expansive and thorough research into AI browser agents")
    require(
        expansive["depth"] == "deep",
        f"expansive thorough request should classify deep: {expansive}",
        failures,
    )

    inline = classify("brief summary inline only of this file")
    require(inline["depth"] == "light", f"expected inline light, got {inline}", failures)
    require(inline["persist"] is False, f"inline-only task should not persist: {inline}", failures)

    if failures:
        print("FAIL research depth checks:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS research depth checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
