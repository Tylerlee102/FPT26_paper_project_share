from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_e2m0_residual_matrix import (
    DEFAULT_REGISTRATION,
    build_specs,
    load_registration,
    require_held_out_prerequisites,
)


def test_registration_source_hashes_are_frozen_and_current() -> None:
    registration = load_registration(DEFAULT_REGISTRATION)
    assert registration["candidate_name"].endswith("_r7")
    assert registration["logical_state_bytes"]["candidate"] == 538_256


def test_preregistered_matrix_shapes_are_exact() -> None:
    registration = json.loads(DEFAULT_REGISTRATION.read_text(encoding="utf-8"))
    split, tokens, checkpoints, specs = build_specs(
        "development_robustness", registration
    )
    assert (split, tokens, checkpoints) == ("development", 1024, (64, 256, 1024))
    assert len(specs) == 14
    assert len(set(specs)) == 14

    split, tokens, checkpoints, specs = build_specs(
        "extended_development", registration
    )
    assert split == "development"
    assert tokens == 8192
    assert checkpoints == (64, 256, 1024, 4096, 8192)
    assert len(specs) == 2

    split, tokens, checkpoints, specs = build_specs("held_out", registration)
    assert split == "held_out"
    assert tokens == 8192
    assert len(specs) == 12
    assert len(set(specs)) == 12


def test_held_out_is_blocked_before_development_manifests_exist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(
        "scripts.run_e2m0_residual_matrix.PREREQUISITE_MANIFESTS",
        (missing,),
    )
    with pytest.raises(RuntimeError, match="prerequisite is missing"):
        require_held_out_prerequisites(DEFAULT_REGISTRATION)
