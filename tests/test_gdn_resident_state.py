from __future__ import annotations

from dataclasses import replace
import unittest

import numpy as np

from golden.gdn_mxfp4_encoded import (
    EncodedState,
    encode_state,
    encode_token,
    recurrence_core_step_encoded,
)
from golden.gdn_resident_state import (
    ResidentCommand,
    ResidentStateOracle,
    ResidentStatus,
)


class TestResidentStateOracle(unittest.TestCase):
    def setUp(self) -> None:
        self.oracle = ResidentStateOracle(
            num_sequences=2,
            num_layers=36,
            value_heads=2,
            qk_heads=1,
            key_dim=2,
            value_dim=3,
            block_size=16,
        )
        self.token = encode_token(
            np.array([[0.5, 0.0]], dtype=np.float32),
            np.array([[1.0, 0.0]], dtype=np.float32),
            np.array([[2.0, -1.0, 3.0], [4.0, 1.0, -2.0]], dtype=np.float32),
            np.array([1.0, 0.5], dtype=np.float32),
            np.array([1.0, 0.25], dtype=np.float32),
            block_size=16,
        )

    def assertStateEqual(self, left: EncodedState, right: EncodedState) -> None:
        self.assertEqual(left.block_size, right.block_size)
        np.testing.assert_array_equal(left.elements, right.elements)
        np.testing.assert_array_equal(left.scales, right.scales)

    def test_reset_is_canonical_and_idempotent(self) -> None:
        first = self.oracle.reset(0, 0)
        first.state.elements[0, 0, 0] = 7
        second = self.oracle.reset(0, 0)

        self.assertEqual(first.status, ResidentStatus.OK)
        self.assertEqual(second.status, ResidentStatus.OK)
        self.assertEqual(second.generation, 0)
        self.assertEqual(second.cumulative_counters.as_dict(), {
            name: 0 for name in second.cumulative_counters.as_dict()
        })
        np.testing.assert_array_equal(second.state.elements, 0)
        np.testing.assert_array_equal(second.state.scales, 127)
        self.assertEqual(second.state.elements.shape, (2, 2, 3))
        self.assertEqual(second.state.scales.shape, (2, 2, 1))

    def test_step_and_readback_before_initialization_are_rejected(self) -> None:
        step = self.oracle.step(0, 0, self.token)
        readback = self.oracle.readback(0, 0)

        self.assertEqual(step.status, ResidentStatus.UNINITIALIZED_STATE)
        self.assertEqual(readback.status, ResidentStatus.UNINITIALIZED_STATE)
        self.assertIsNone(readback.state)
        self.assertEqual(step.command_counters.rejected_commands, 1)
        self.assertEqual(readback.cumulative_counters.rejected_commands, 2)
        self.assertEqual(readback.generation, 0)

    def test_load_copies_input_and_readback_returns_copy(self) -> None:
        source = encode_state(
            np.arange(12, dtype=np.float32).reshape(2, 2, 3), block_size=16
        )
        expected = EncodedState(
            source.elements.copy(), source.scales.copy(), source.block_size
        )
        loaded = self.oracle.load(0, 0, source)
        source.elements.fill(0)
        source.scales.fill(0)
        loaded.state.elements.fill(0)

        readback = self.oracle.readback(0, 0)
        self.assertEqual(loaded.status, ResidentStatus.OK)
        self.assertEqual(loaded.generation, 1)
        self.assertEqual(loaded.command_counters.committed_state_generations, 1)
        self.assertStateEqual(readback.state, expected)

        readback.state.elements.fill(0)
        self.assertStateEqual(self.oracle.readback(0, 0).state, expected)

    def test_invalid_load_is_atomic_and_counted(self) -> None:
        valid = encode_state(np.ones((2, 2, 3), dtype=np.float32), block_size=16)
        self.assertEqual(self.oracle.load(0, 0, valid).status, ResidentStatus.OK)
        before = self.oracle.readback(0, 0)
        invalid = EncodedState(
            elements=before.state.elements.copy(),
            scales=before.state.scales.copy(),
            block_size=16,
        )
        invalid.elements[0, 0, 0] = 8

        rejected = self.oracle.load(0, 0, invalid)
        after = self.oracle.readback(0, 0)

        self.assertEqual(rejected.status, ResidentStatus.INVALID_ENCODING)
        self.assertEqual(rejected.generation, before.generation)
        self.assertEqual(rejected.command_counters.invalid_encodings, 1)
        self.assertEqual(rejected.command_counters.rejected_commands, 1)
        self.assertEqual(after.cumulative_counters.invalid_encodings, 1)
        self.assertStateEqual(after.state, before.state)

    def test_shape_mismatch_is_distinct_and_atomic(self) -> None:
        self.oracle.reset(0, 0)
        wrong_shape = encode_state(
            np.ones((2, 2, 4), dtype=np.float32), block_size=16
        )

        rejected = self.oracle.load(0, 0, wrong_shape)

        self.assertEqual(rejected.status, ResidentStatus.SHAPE_MISMATCH)
        self.assertEqual(rejected.command_counters.invalid_encodings, 0)
        self.assertEqual(rejected.command_counters.rejected_commands, 1)
        self.assertEqual(rejected.generation, 0)
        np.testing.assert_array_equal(rejected.state.elements, 0)

    def test_block_size_mismatch_is_a_shape_error(self) -> None:
        wrong_state = encode_state(
            np.ones((2, 2, 3), dtype=np.float32), block_size=32
        )
        wrong_token = replace(self.token, block_size=32)

        load = self.oracle.load(0, 0, wrong_state)
        self.oracle.reset(0, 0)
        step = self.oracle.step(0, 0, wrong_token)

        self.assertEqual(load.status, ResidentStatus.SHAPE_MISMATCH)
        self.assertEqual(step.status, ResidentStatus.SHAPE_MISMATCH)
        self.assertEqual(load.command_counters.invalid_encodings, 0)
        self.assertEqual(step.command_counters.invalid_encodings, 0)
        self.assertEqual(load.command_counters.rejected_commands, 1)
        self.assertEqual(step.command_counters.rejected_commands, 1)

    def test_step_matches_encoded_oracle_and_commits_once(self) -> None:
        reset = self.oracle.reset(0, 0)
        direct = recurrence_core_step_encoded(self.token, reset.state)

        stepped = self.oracle.step(0, 0, self.token)
        readback = self.oracle.readback(0, 0)

        self.assertEqual(stepped.status, ResidentStatus.OK)
        self.assertEqual(stepped.generation, 1)
        self.assertEqual(stepped.command_counters.committed_state_generations, 1)
        self.assertEqual(
            stepped.command_counters.element_saturations,
            direct.counters.element_saturations,
        )
        self.assertEqual(
            stepped.command_counters.alignment_underflows,
            direct.counters.alignment_underflows,
        )
        np.testing.assert_array_equal(stepped.output_mantissas, direct.output_mantissas)
        np.testing.assert_array_equal(stepped.output_exponents, direct.output_exponents)
        np.testing.assert_array_equal(stepped.output_fp32, direct.output_fp32)
        self.assertStateEqual(readback.state, direct.state)
        self.assertEqual(readback.generation, 1)

    def test_invalid_step_preserves_state_and_generation(self) -> None:
        self.oracle.reset(0, 0)
        self.oracle.step(0, 0, self.token)
        before = self.oracle.readback(0, 0)
        invalid_q = self.token.q_elements.copy()
        invalid_q[0, 0] = 8
        invalid = replace(self.token, q_elements=invalid_q)

        rejected = self.oracle.step(0, 0, invalid)
        after = self.oracle.readback(0, 0)

        self.assertEqual(rejected.status, ResidentStatus.INVALID_ENCODING)
        self.assertEqual(after.generation, before.generation)
        self.assertStateEqual(after.state, before.state)
        self.assertEqual(
            after.cumulative_counters.committed_state_generations,
            before.cumulative_counters.committed_state_generations,
        )
        self.assertEqual(
            after.cumulative_counters.rejected_commands,
            before.cumulative_counters.rejected_commands + 1,
        )

    def test_sequence_and_layer_slots_do_not_alias(self) -> None:
        self.oracle.reset(0, 0)
        self.oracle.reset(1, 35)
        first = self.oracle.step(0, 0, self.token)
        second = self.oracle.readback(1, 35)

        self.assertEqual(first.generation, 1)
        self.assertEqual(second.generation, 0)
        self.assertFalse(np.array_equal(first.state.elements, second.state.elements))
        np.testing.assert_array_equal(second.state.elements, 0)

    def test_all_36_layer_ids_are_addressable_and_isolated(self) -> None:
        for layer_id in range(36):
            reset = self.oracle.reset(0, layer_id)
            self.assertEqual(reset.status, ResidentStatus.OK)
            if layer_id % 2:
                stepped = self.oracle.step(0, layer_id, self.token)
                self.assertEqual(stepped.status, ResidentStatus.OK)

        for layer_id in range(36):
            readback = self.oracle.readback(0, layer_id)
            self.assertEqual(readback.status, ResidentStatus.OK)
            self.assertEqual(readback.generation, layer_id % 2)
            if layer_id % 2:
                self.assertTrue(np.any(readback.state.elements != 0))
            else:
                np.testing.assert_array_equal(readback.state.elements, 0)

    def test_invalid_selectors_do_not_create_cumulative_slot_state(self) -> None:
        bad_sequence = self.oracle.reset(2, 0)
        bad_layer = self.oracle.reset(0, 36)
        non_integer = self.oracle.reset(True, 0)

        self.assertEqual(bad_sequence.status, ResidentStatus.INVALID_SEQUENCE_ID)
        self.assertEqual(bad_layer.status, ResidentStatus.INVALID_LAYER_ID)
        self.assertEqual(non_integer.status, ResidentStatus.INVALID_SEQUENCE_ID)
        for result in (bad_sequence, bad_layer, non_integer):
            self.assertEqual(result.command_counters.rejected_commands, 1)
            self.assertEqual(result.cumulative_counters.rejected_commands, 0)
            self.assertIsNone(result.state)

    def test_invalid_command_and_payload_rules_are_counted(self) -> None:
        invalid_command = self.oracle.execute(99, 0, 0)
        missing_load = self.oracle.execute(ResidentCommand.LOAD, 0, 0)
        unexpected = self.oracle.execute(
            ResidentCommand.RESET, 0, 0, token=self.token
        )

        self.assertEqual(invalid_command.status, ResidentStatus.INVALID_COMMAND)
        self.assertEqual(missing_load.status, ResidentStatus.MISSING_PAYLOAD)
        self.assertEqual(unexpected.status, ResidentStatus.UNEXPECTED_PAYLOAD)
        self.assertEqual(unexpected.cumulative_counters.rejected_commands, 3)
        self.assertEqual(unexpected.cumulative_counters.invalid_encodings, 0)

    def test_reset_starts_a_new_generation_epoch(self) -> None:
        self.oracle.reset(0, 0)
        self.oracle.step(0, 0, self.token)
        self.oracle.step(0, 0, self.token)

        reset = self.oracle.reset(0, 0)

        self.assertEqual(reset.generation, 0)
        self.assertEqual(reset.cumulative_counters.committed_state_generations, 0)
        np.testing.assert_array_equal(reset.state.elements, 0)
        np.testing.assert_array_equal(reset.state.scales, 127)


if __name__ == "__main__":
    unittest.main()
