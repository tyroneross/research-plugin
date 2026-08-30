from __future__ import annotations

import inspect

import research


def test_verifier_registry_uses_one_dispatch_contract() -> None:
    for verifier in research.VERIFIERS.values():
        assert len(inspect.signature(verifier).parameters) == 2


def test_optional_symbolic_verifier_is_callable_without_static_dependency() -> None:
    result = research._verify_symbolic({"claim": "1 = 1"}, "unused-entry")

    assert result["verdict"] in {"passed", "inconclusive"}


def test_ordered_pair_has_stable_two_item_shape() -> None:
    assert research._ordered_pair("claim-b", "claim-a") == ("claim-a", "claim-b")
