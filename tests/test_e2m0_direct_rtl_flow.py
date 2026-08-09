import inspect
from pathlib import Path

from scripts.e2m0_direct_rtl_flow import run_flow


ROOT = Path(__file__).resolve().parents[1]


def test_direct_rtl_flow_supports_cached_long_runs() -> None:
    source = inspect.getsource(run_flow)
    assert "args.token_limit" not in source
    assert "build_cache_key" in source
    assert "36 * 3600 if token_limit == 64" in source
    assert 'evidence / "benchmarks"' in source
    assert "| tee" in source
