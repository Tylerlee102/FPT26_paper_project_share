import csv
import hashlib
import json
from pathlib import Path

from scripts.aggregate_e2m0_encoded_extended import aggregate


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _fixture(
    tmp_path: Path, *, with_replay: bool, quality_pass: bool = True
) -> tuple[Path, Path]:
    source = tmp_path / "oracle.py"
    source.write_text("frozen\n", encoding="utf-8")
    input_dir = tmp_path / "extended"
    input_dir.mkdir()
    seed = 64370
    candidate = "candidate"
    checkpoints = [1, 2]
    registration = {
        "registration_status": "PASS",
        "candidate_name": candidate,
        "frozen_source_sha256": {"oracle.py": _sha256(source)},
        "extended_development_gate": {
            "status": "NOT_RUN",
            "seed": seed,
            "trace_family": "high_retention",
            "initial_state_modes": ["random", "zero"],
            "tokens": 2,
            "checkpoints": checkpoints,
        },
    }
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(json.dumps(registration), encoding="utf-8")

    for mode, passing_cosine in (("random", 0.995), ("zero", 0.996)):
        cosine = passing_cosine if quality_pass else 0.98
        stem = f"high_retention_{seed:08x}_{mode}_2"
        token_path = input_dir / f"{stem}_tokens.csv"
        checkpoint_path = input_dir / f"{stem}_checkpoints.csv"
        rows = []
        for token in (1, 2):
            rows.append(
                {
                    "variant": "fp32",
                    "token_index": token,
                    "output_cosine_fp32": 1.0,
                    "state_rel_l2": 0.0,
                    "state_max_abs": 0.0,
                    "cumulative_element_saturations": 0,
                    "cumulative_accumulator_saturations": 0,
                    "cumulative_scale_clamps": 0,
                    "cumulative_alignment_underflows": 0,
                    "cumulative_e2m0_residual_clips": 0,
                    "folds": 0,
                    "logical_state_bytes": 10,
                }
            )
            candidate_row = dict(rows[-1])
            candidate_row.update(
                variant=candidate,
                output_cosine_fp32=cosine,
                state_rel_l2=0.05,
                state_max_abs=0.01,
                cumulative_alignment_underflows=token * 3,
                cumulative_e2m0_residual_clips=token * 2,
                folds=token - 1,
            )
            rows.append(candidate_row)
        _write_csv(token_path, rows)
        _write_csv(checkpoint_path, rows)
        manifest = {
            "status": "PASS" if quality_pass else "FAIL",
            "initial_state_mode": mode,
            "variant": candidate,
            "configuration": {
                "seed": seed,
                "split": "extended_development",
                "trace_family": "high_retention",
                "tokens": 2,
                "checkpoints": checkpoints,
            },
            "gate": {"gate_pass": quality_pass},
            "input_stream_sha256": mode.upper(),
            "outputs": {
                token_path.relative_to(tmp_path).as_posix(): _sha256(token_path),
                checkpoint_path.relative_to(tmp_path).as_posix(): _sha256(
                    checkpoint_path
                ),
            },
        }
        manifest_path = input_dir / f"{stem}_manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        if with_replay:
            verification = {
                "status": "PASS",
                "candidate_gate": "PASS" if quality_pass else "FAIL",
                "failures": [],
                "manifest_sha256": _sha256(manifest_path),
                "recomputed": True,
            }
            (input_dir / f"{stem}_verification.json").write_text(
                json.dumps(verification), encoding="utf-8"
            )
    return registration_path, input_dir


def test_extended_summary_waits_for_full_deterministic_recompute(tmp_path: Path) -> None:
    registration, input_dir = _fixture(tmp_path, with_replay=False)
    result = aggregate(
        root=tmp_path, registration_path=registration, input_dir=input_dir
    )
    assert result["status"] == "NOT_RUN"
    assert result["extended_run_gate"] == "PASS"
    assert result["full_deterministic_recompute"] == "NOT_RUN"


def test_extended_summary_passes_only_after_both_replays(tmp_path: Path) -> None:
    registration, input_dir = _fixture(tmp_path, with_replay=True)
    result = aggregate(
        root=tmp_path, registration_path=registration, input_dir=input_dir
    )
    assert result["status"] == "PASS"
    assert result["run_count"] == 2
    assert result["recomputed_run_count"] == 2
    assert result["minimum_checkpoint_output_cosine"] == 0.995
    assert result["maximum_final_state_relative_l2"] == 0.05
    assert result["total_alignment_underflows"] == 12
    assert result["total_e2m0_residual_clips"] == 8
    assert result["total_folds"] == 2


def test_extended_summary_preserves_replay_pass_when_quality_fails(
    tmp_path: Path,
) -> None:
    registration, input_dir = _fixture(
        tmp_path, with_replay=True, quality_pass=False
    )
    result = aggregate(
        root=tmp_path, registration_path=registration, input_dir=input_dir
    )
    assert result["status"] == "FAIL"
    assert result["extended_run_gate"] == "FAIL"
    assert result["full_deterministic_recompute"] == "PASS"
    assert result["recomputed_run_count"] == 2
    assert result["failures"] == []
