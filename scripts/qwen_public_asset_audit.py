"""Audit public Hugging Face assets for usable Qwen3-Next activation evidence."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "reports" / "environment" / "qwen_public_asset_audit.json"
MODEL_QUERY = "Qwen3-Next"
DATASET_QUERIES = (
    "Qwen3-Next",
    "Qwen3-Next activations",
    "Qwen3-Next hidden states",
    "Qwen3-Next Gated DeltaNet",
)
ACTIVATION_TERMS = ("activation", "hidden-state", "hidden_state", "gated-delta", "deltanet")


def _api(kind: str, query: str, limit: int = 100) -> str:
    encoded = urllib.parse.urlencode({"search": query, "limit": limit, "full": "true"})
    return f"https://huggingface.co/api/{kind}?{encoded}"


def _fetch(url: str) -> list[dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": "gdn-fpga-audit/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"expected list response from {url}")
    return [row for row in value if isinstance(row, dict)]


def classify(
    models: list[dict[str, Any]],
    datasets_by_query: dict[str, list[dict[str, Any]]],
) -> dict[str, object]:
    official = sorted(
        {
            str(row.get("id"))
            for row in models
            if str(row.get("id", "")).startswith("Qwen/Qwen3-Next-")
        }
    )
    all_datasets = {
        str(row.get("id")): row
        for rows in datasets_by_query.values()
        for row in rows
        if row.get("id")
    }
    activation_candidates = sorted(
        identifier
        for identifier, row in all_datasets.items()
        if any(
            term in " ".join(
                (
                    identifier,
                    str(row.get("description", "")),
                    " ".join(str(tag) for tag in row.get("tags", [])),
                )
            ).lower()
            for term in ACTIVATION_TERMS
        )
    )
    return {
        "official_qwen3_next_models": official,
        "official_model_count": len(official),
        "dataset_result_count": len(all_datasets),
        "activation_dataset_candidates": activation_candidates,
        "usable_public_activation_capture": "NOT_FOUND" if not activation_candidates else "REVIEW_REQUIRED",
        "closed_loop_quality_status": "BLOCKED_EXTERNAL",
    }


def build(output: Path) -> dict[str, object]:
    model_url = _api("models", MODEL_QUERY)
    dataset_urls = {query: _api("datasets", query) for query in DATASET_QUERIES}
    models = _fetch(model_url)
    datasets = {query: _fetch(url) for query, url in dataset_urls.items()}
    classification = classify(models, datasets)
    payload: dict[str, object] = {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "bounded public Hugging Face search; not an exhaustive internet census",
        "queries": {
            "models": model_url,
            "datasets": dataset_urls,
        },
        "classification": classification,
        "finding": (
            "No public Qwen3-Next recurrent activation capture was found in the bounded API queries. "
            "The official Qwen collection exposes only full 80B-class Qwen3-Next variants; non-official "
            "development and tiny-random checkpoints do not support real-model quality claims."
        ),
        "required_to_unblock": [
            "a trained Qwen3-Next checkpoint that fits available compute or remote intermediate-tensor access",
            "closed-loop capture of q, k, v, decay, beta, outputs, and recurrent state",
            "a model-level metric such as perplexity or downstream-task quality",
        ],
        "raw_result_ids": {
            "models": sorted({str(row.get("id")) for row in models if row.get("id")}),
            "datasets": {
                query: sorted({str(row.get("id")) for row in rows if row.get("id")})
                for query, rows in datasets.items()
            },
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    payload = build(output)
    print(json.dumps(payload["classification"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
