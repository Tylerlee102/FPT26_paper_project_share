from __future__ import annotations

from scripts.qwen_public_asset_audit import classify


def test_public_asset_classification_does_not_promote_tiny_random_model() -> None:
    models = [
        {"id": "Qwen/Qwen3-Next-80B-A3B-Instruct"},
        {"id": "someone/qwen3-next-tiny-random"},
    ]
    datasets = {
        "Qwen3-Next": [{"id": "owner/prompts", "tags": ["text"]}],
        "Qwen3-Next activations": [],
    }

    result = classify(models, datasets)

    assert result["official_qwen3_next_models"] == [
        "Qwen/Qwen3-Next-80B-A3B-Instruct"
    ]
    assert result["activation_dataset_candidates"] == []
    assert result["usable_public_activation_capture"] == "NOT_FOUND"
    assert result["closed_loop_quality_status"] == "BLOCKED_EXTERNAL"


def test_public_asset_classification_flags_activation_dataset_for_review() -> None:
    result = classify(
        [],
        {"query": [{"id": "owner/qwen3-next-activations", "tags": []}]},
    )

    assert result["activation_dataset_candidates"] == [
        "owner/qwen3-next-activations"
    ]
    assert result["usable_public_activation_capture"] == "REVIEW_REQUIRED"
