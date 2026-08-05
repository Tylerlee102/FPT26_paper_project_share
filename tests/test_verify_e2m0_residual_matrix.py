from __future__ import annotations

from scripts.verify_e2m0_residual_matrix import EXPECTED_BYTES, VARIANT, verify_all


def test_real_preregistered_e2m0_matrices_verify() -> None:
    result = verify_all()
    assert result["status"] == "PASS", result["failures"]
    assert result["candidate"] == VARIANT
    assert result["logical_state_bytes"] == EXPECTED_BYTES
    assert result["run_count"] == 28
    assert result["token_row_count"] == 258_048
    assert result["checkpoint_row_count"] == 224
    assert result["candidate_software_stability"] == "PASS"
    assert result["selected_method_hardware_pareto"] == "NOT_RUN"
    assert result["matrices"]["held_out"]["runs"] == 12
