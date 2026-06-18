from __future__ import annotations

import unittest
import shutil
from pathlib import Path

import numpy as np

from golden.gdn_fp32 import gdn_decode_step
from golden.vectors import generate_synthetic_vector, load_vector, save_vector, vector_digest, write_manifest


class TestVectors(unittest.TestCase):
    def test_synthetic_vectors_are_deterministic(self) -> None:
        a = generate_synthetic_vector(0, seed=0xFB72, num_heads=2, head_dim=8)
        b = generate_synthetic_vector(0, seed=0xFB72, num_heads=2, head_dim=8)

        self.assertEqual(vector_digest(a), vector_digest(b))
        np.testing.assert_array_equal(a.q, b.q)
        np.testing.assert_array_equal(a.state_in, b.state_in)

    def test_generated_outputs_match_golden(self) -> None:
        vector = generate_synthetic_vector(1, seed=0xFB72, num_heads=2, head_dim=8)

        output, state_out = gdn_decode_step(
            vector.q,
            vector.k,
            vector.v,
            vector.beta,
            vector.gate,
            vector.state_in,
        )

        np.testing.assert_allclose(output, vector.output, atol=0.0, rtol=0.0)
        np.testing.assert_allclose(state_out, vector.state_out, atol=0.0, rtol=0.0)

    def test_vector_round_trip_and_manifest(self) -> None:
        vector = generate_synthetic_vector(2, seed=0xFB72, num_heads=2, head_dim=8)
        tmp = Path.cwd() / "build" / "test_vectors"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            path = save_vector(vector, tmp)
            manifest = write_manifest([path], tmp)
            loaded = load_vector(path)

            self.assertTrue(Path(manifest).exists())
            self.assertEqual(vector_digest(vector), vector_digest(loaded))
            np.testing.assert_array_equal(loaded.output, vector.output)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
