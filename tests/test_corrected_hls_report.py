from __future__ import annotations

from scripts.corrected_hls_report import _parse_loop_results


def test_parse_loop_results_separates_targeted_and_transport_loops() -> None:
    log = "\n".join(
        [
            "Pipelining result : Target II = 1, Final II = 1, Depth = 7, loop 'update_lanes'",
            "Pipelining result : Target II = NA, Final II = 33, Depth = 44, loop 'load_blocks'",
        ]
    )

    targeted, untargeted = _parse_loop_results(log)

    assert targeted == [
        {"loop": "update_lanes", "target_ii": 1, "final_ii": 1, "depth": 7}
    ]
    assert untargeted == [
        {"loop": "load_blocks", "target_ii": None, "final_ii": 33, "depth": 44}
    ]
