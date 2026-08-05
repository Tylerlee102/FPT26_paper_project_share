import numpy as np

from scripts.hf_safetensors_range import bf16_storage_to_float32, validate_aliases
from scripts.qwen_recurrent_capture import _causal_depthwise_conv, _rms_norm


def test_bf16_storage_conversion() -> None:
    expected = np.array([0.0, 1.0, -2.5, 3.25], dtype=np.float32)
    storage = (expected.view(np.uint32) >> np.uint32(16)).astype(np.uint16)
    np.testing.assert_array_equal(bf16_storage_to_float32(storage), expected)


def test_causal_depthwise_conv_uses_pytorch_cross_correlation_order() -> None:
    values = np.array([[[1.0], [2.0], [3.0], [4.0]]], dtype=np.float32)
    weight = np.array([[10.0, 20.0, 30.0]], dtype=np.float32)
    raw_expected = np.array([30.0, 80.0, 140.0, 200.0], dtype=np.float32)
    expected = raw_expected / (1.0 + np.exp(-raw_expected))
    actual = _causal_depthwise_conv(values, weight)[0, :, 0]
    np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=0.0)


def test_gemma_style_rms_norm_is_one_centered() -> None:
    values = np.array([[[3.0, 4.0]]], dtype=np.float32)
    weight = np.array([0.0, 1.0], dtype=np.float32)
    actual = _rms_norm(values, weight, 0.0)
    scale = np.sqrt(np.mean(values * values, axis=-1, keepdims=True))
    np.testing.assert_allclose(actual, values / scale * np.array([1.0, 2.0]), rtol=1e-6)


def test_alias_validation_rejects_duplicates() -> None:
    try:
        validate_aliases(["a", "a"])
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate aliases were accepted")
