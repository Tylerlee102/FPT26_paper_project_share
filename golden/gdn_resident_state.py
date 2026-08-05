"""Resident-state command oracle for the encoded MXFP4 GDN core.

This module freezes the control-plane behavior that HLS C simulation, RTL
cosimulation, and board execution must reproduce. Arithmetic remains owned by
``gdn_mxfp4_encoded``; this layer owns state identity, validation, atomic
commit, counters, status codes, and generation tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np

from .gdn_mxfp4_encoded import (
    ArithmeticCounters,
    EncodedState,
    EncodedStepResult,
    EncodedToken,
    _validate_encoded_array,
    _validate_state,
    decode_q1_15,
    recurrence_core_step_encoded,
)


class ResidentCommand(IntEnum):
    RESET = 0
    LOAD = 1
    STEP = 2
    READBACK = 3


class ResidentStatus(IntEnum):
    OK = 0
    INVALID_COMMAND = 1
    INVALID_SEQUENCE_ID = 2
    INVALID_LAYER_ID = 3
    UNINITIALIZED_STATE = 4
    MISSING_PAYLOAD = 5
    UNEXPECTED_PAYLOAD = 6
    INVALID_ENCODING = 7
    SHAPE_MISMATCH = 8


@dataclass
class ResidentCounters:
    element_saturations: int = 0
    accumulator_saturations: int = 0
    scale_clamps: int = 0
    alignment_underflows: int = 0
    state_scale_changes: int = 0
    invalid_encodings: int = 0
    rejected_commands: int = 0
    committed_state_generations: int = 0

    @classmethod
    def from_arithmetic(cls, counters: ArithmeticCounters) -> "ResidentCounters":
        return cls(
            element_saturations=counters.element_saturations,
            accumulator_saturations=counters.accumulator_saturations,
            scale_clamps=counters.scale_clamps,
            alignment_underflows=counters.alignment_underflows,
            state_scale_changes=counters.state_scale_changes,
        )

    def add(self, other: "ResidentCounters") -> None:
        for name in self.as_dict():
            setattr(self, name, getattr(self, name) + getattr(other, name))

    def copy(self) -> "ResidentCounters":
        return ResidentCounters(**self.as_dict())

    def as_dict(self) -> dict[str, int]:
        return {
            "element_saturations": self.element_saturations,
            "accumulator_saturations": self.accumulator_saturations,
            "scale_clamps": self.scale_clamps,
            "alignment_underflows": self.alignment_underflows,
            "state_scale_changes": self.state_scale_changes,
            "invalid_encodings": self.invalid_encodings,
            "rejected_commands": self.rejected_commands,
            "committed_state_generations": self.committed_state_generations,
        }


@dataclass(frozen=True)
class ResidentResult:
    command_code: int
    status: ResidentStatus
    sequence_id: int
    layer_id: int
    generation: int
    command_counters: ResidentCounters
    cumulative_counters: ResidentCounters
    state: EncodedState | None = None
    output_mantissas: np.ndarray | None = None
    output_exponents: np.ndarray | None = None
    output_fp32: np.ndarray | None = None
    error_detail: str = ""


@dataclass
class _ResidentSlot:
    initialized: bool = False
    state: EncodedState | None = None
    generation: int = 0
    counters: ResidentCounters = field(default_factory=ResidentCounters)


def _copy_state(state: EncodedState | None) -> EncodedState | None:
    if state is None:
        return None
    return EncodedState(
        elements=np.array(state.elements, dtype=np.uint8, copy=True),
        scales=np.array(state.scales, dtype=np.uint8, copy=True),
        block_size=int(state.block_size),
    )


def _integer_code(value: object) -> int | None:
    if isinstance(value, (bool, np.bool_)):
        return None
    if isinstance(value, (int, np.integer)):
        return int(value)
    return None


class ResidentStateOracle:
    """Persistent command processor with state isolated by sequence and layer."""

    def __init__(
        self,
        *,
        num_sequences: int = 1,
        num_layers: int = 36,
        value_heads: int = 32,
        qk_heads: int = 16,
        key_dim: int = 128,
        value_dim: int = 128,
        block_size: int = 32,
    ) -> None:
        dimensions = {
            "num_sequences": num_sequences,
            "num_layers": num_layers,
            "value_heads": value_heads,
            "qk_heads": qk_heads,
            "key_dim": key_dim,
            "value_dim": value_dim,
        }
        for name, value in dimensions.items():
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if value_heads % qk_heads != 0:
            raise ValueError("value_heads must be divisible by qk_heads")
        if block_size not in (16, 32):
            raise ValueError("block_size must be 16 or 32")

        self.num_sequences = num_sequences
        self.num_layers = num_layers
        self.value_heads = value_heads
        self.qk_heads = qk_heads
        self.key_dim = key_dim
        self.value_dim = value_dim
        self.block_size = block_size
        self._slots: dict[tuple[int, int], _ResidentSlot] = {}

    @property
    def state_shape(self) -> tuple[int, int, int]:
        return (self.value_heads, self.key_dim, self.value_dim)

    def _canonical_zero(self) -> EncodedState:
        blocks = (self.value_dim + self.block_size - 1) // self.block_size
        return EncodedState(
            elements=np.zeros(self.state_shape, dtype=np.uint8),
            scales=np.full(
                (self.value_heads, self.key_dim, blocks),
                127,
                dtype=np.uint8,
            ),
            block_size=self.block_size,
        )

    def _slot(self, sequence_id: int, layer_id: int) -> _ResidentSlot:
        return self._slots.setdefault((sequence_id, layer_id), _ResidentSlot())

    def _result(
        self,
        *,
        command_code: int,
        status: ResidentStatus,
        sequence_id: int,
        layer_id: int,
        slot: _ResidentSlot | None,
        command_counters: ResidentCounters | None = None,
        step_result: EncodedStepResult | None = None,
        error_detail: str = "",
    ) -> ResidentResult:
        per_command = command_counters or ResidentCounters()
        return ResidentResult(
            command_code=command_code,
            status=status,
            sequence_id=sequence_id,
            layer_id=layer_id,
            generation=slot.generation if slot is not None else 0,
            command_counters=per_command.copy(),
            cumulative_counters=(
                slot.counters.copy() if slot is not None else ResidentCounters()
            ),
            state=_copy_state(slot.state) if slot is not None and slot.initialized else None,
            output_mantissas=(
                np.array(step_result.output_mantissas, copy=True)
                if step_result is not None
                else None
            ),
            output_exponents=(
                np.array(step_result.output_exponents, copy=True)
                if step_result is not None
                else None
            ),
            output_fp32=(
                np.array(step_result.output_fp32, copy=True)
                if step_result is not None
                else None
            ),
            error_detail=error_detail,
        )

    def _reject(
        self,
        *,
        command_code: int,
        status: ResidentStatus,
        sequence_id: int,
        layer_id: int,
        slot: _ResidentSlot | None,
        invalid_encoding: bool = False,
        error_detail: str = "",
    ) -> ResidentResult:
        counters = ResidentCounters(
            invalid_encodings=1 if invalid_encoding else 0,
            rejected_commands=1,
        )
        if slot is not None:
            slot.counters.add(counters)
        return self._result(
            command_code=command_code,
            status=status,
            sequence_id=sequence_id,
            layer_id=layer_id,
            slot=slot,
            command_counters=counters,
            error_detail=error_detail,
        )

    def _validate_loaded_state(self, state: object) -> EncodedState:
        if not isinstance(state, EncodedState):
            raise TypeError("LOAD state payload must be EncodedState")
        elements, scales = _validate_state(state)
        if state.block_size != self.block_size:
            raise RuntimeError(
                f"state block size must be {self.block_size}, got {state.block_size}"
            )
        if elements.shape != self.state_shape:
            raise RuntimeError(
                f"state shape must be {self.state_shape}, got {elements.shape}"
            )
        return EncodedState(
            elements=np.array(elements, dtype=np.uint8, copy=True),
            scales=np.array(scales, dtype=np.uint8, copy=True),
            block_size=self.block_size,
        )

    def _validate_token(self, token: object) -> EncodedToken:
        if not isinstance(token, EncodedToken):
            raise TypeError("STEP token payload must be EncodedToken")
        if token.block_size != self.block_size:
            raise RuntimeError(
                f"token block size must be {self.block_size}, got {token.block_size}"
            )

        q_elements, q_scales = _validate_encoded_array(
            "q",
            token.q_elements,
            token.q_scales,
            token.block_size,
            require_canonical_zero=True,
        )
        k_elements, k_scales = _validate_encoded_array(
            "k",
            token.k_elements,
            token.k_scales,
            token.block_size,
            require_canonical_zero=True,
        )
        v_elements, v_scales = _validate_encoded_array(
            "v",
            token.v_elements,
            token.v_scales,
            token.block_size,
            require_canonical_zero=True,
        )
        expected_qk = (self.qk_heads, self.key_dim)
        expected_v = (self.value_heads, self.value_dim)
        if q_elements.shape != expected_qk or k_elements.shape != expected_qk:
            raise RuntimeError(
                f"q and k shapes must both be {expected_qk}, got "
                f"{q_elements.shape} and {k_elements.shape}"
            )
        if v_elements.shape != expected_v:
            raise RuntimeError(
                f"v shape must be {expected_v}, got {v_elements.shape}"
            )

        alpha_codes = np.asarray(token.alpha_codes)
        beta_codes = np.asarray(token.beta_codes)
        decode_q1_15(alpha_codes)
        decode_q1_15(beta_codes)
        expected_gate = (self.value_heads,)
        if alpha_codes.shape != expected_gate or beta_codes.shape != expected_gate:
            raise RuntimeError(
                f"alpha and beta shapes must both be {expected_gate}, got "
                f"{alpha_codes.shape} and {beta_codes.shape}"
            )

        return EncodedToken(
            q_elements=np.array(q_elements, dtype=np.uint8, copy=True),
            q_scales=np.array(q_scales, dtype=np.uint8, copy=True),
            k_elements=np.array(k_elements, dtype=np.uint8, copy=True),
            k_scales=np.array(k_scales, dtype=np.uint8, copy=True),
            v_elements=np.array(v_elements, dtype=np.uint8, copy=True),
            v_scales=np.array(v_scales, dtype=np.uint8, copy=True),
            alpha_codes=np.array(alpha_codes, dtype=np.uint16, copy=True),
            beta_codes=np.array(beta_codes, dtype=np.uint16, copy=True),
            block_size=self.block_size,
        )

    def execute(
        self,
        command: object,
        sequence_id: object,
        layer_id: object,
        *,
        state: object | None = None,
        token: object | None = None,
    ) -> ResidentResult:
        command_code = _integer_code(command)
        sequence_code = _integer_code(sequence_id)
        layer_code = _integer_code(layer_id)
        rendered_command = command_code if command_code is not None else -1
        rendered_sequence = sequence_code if sequence_code is not None else -1
        rendered_layer = layer_code if layer_code is not None else -1

        if sequence_code is None or not 0 <= sequence_code < self.num_sequences:
            return self._reject(
                command_code=rendered_command,
                status=ResidentStatus.INVALID_SEQUENCE_ID,
                sequence_id=rendered_sequence,
                layer_id=rendered_layer,
                slot=None,
                error_detail="sequence_id is outside the configured range",
            )
        if layer_code is None or not 0 <= layer_code < self.num_layers:
            return self._reject(
                command_code=rendered_command,
                status=ResidentStatus.INVALID_LAYER_ID,
                sequence_id=sequence_code,
                layer_id=rendered_layer,
                slot=None,
                error_detail="layer_id is outside the configured range",
            )

        slot = self._slot(sequence_code, layer_code)
        try:
            operation = ResidentCommand(command_code)
        except (TypeError, ValueError):
            return self._reject(
                command_code=rendered_command,
                status=ResidentStatus.INVALID_COMMAND,
                sequence_id=sequence_code,
                layer_id=layer_code,
                slot=slot,
                error_detail="command code is not RESET, LOAD, STEP, or READBACK",
            )

        if operation in (ResidentCommand.RESET, ResidentCommand.READBACK):
            if state is not None or token is not None:
                return self._reject(
                    command_code=command_code,
                    status=ResidentStatus.UNEXPECTED_PAYLOAD,
                    sequence_id=sequence_code,
                    layer_id=layer_code,
                    slot=slot,
                    error_detail=f"{operation.name} does not accept a payload",
                )
        elif operation is ResidentCommand.LOAD:
            if state is None:
                return self._reject(
                    command_code=command_code,
                    status=ResidentStatus.MISSING_PAYLOAD,
                    sequence_id=sequence_code,
                    layer_id=layer_code,
                    slot=slot,
                    error_detail="LOAD requires a complete encoded state",
                )
            if token is not None:
                return self._reject(
                    command_code=command_code,
                    status=ResidentStatus.UNEXPECTED_PAYLOAD,
                    sequence_id=sequence_code,
                    layer_id=layer_code,
                    slot=slot,
                    error_detail="LOAD does not accept a token payload",
                )
        elif operation is ResidentCommand.STEP:
            if token is None:
                return self._reject(
                    command_code=command_code,
                    status=ResidentStatus.MISSING_PAYLOAD,
                    sequence_id=sequence_code,
                    layer_id=layer_code,
                    slot=slot,
                    error_detail="STEP requires a complete encoded token",
                )
            if state is not None:
                return self._reject(
                    command_code=command_code,
                    status=ResidentStatus.UNEXPECTED_PAYLOAD,
                    sequence_id=sequence_code,
                    layer_id=layer_code,
                    slot=slot,
                    error_detail="STEP consumes resident state, not a state payload",
                )

        if operation is ResidentCommand.RESET:
            slot.initialized = True
            slot.state = self._canonical_zero()
            slot.generation = 0
            slot.counters = ResidentCounters()
            return self._result(
                command_code=command_code,
                status=ResidentStatus.OK,
                sequence_id=sequence_code,
                layer_id=layer_code,
                slot=slot,
            )

        if operation is ResidentCommand.LOAD:
            try:
                loaded = self._validate_loaded_state(state)
            except RuntimeError as exc:
                return self._reject(
                    command_code=command_code,
                    status=ResidentStatus.SHAPE_MISMATCH,
                    sequence_id=sequence_code,
                    layer_id=layer_code,
                    slot=slot,
                    error_detail=str(exc),
                )
            except (AttributeError, TypeError, ValueError) as exc:
                return self._reject(
                    command_code=command_code,
                    status=ResidentStatus.INVALID_ENCODING,
                    sequence_id=sequence_code,
                    layer_id=layer_code,
                    slot=slot,
                    invalid_encoding=True,
                    error_detail=str(exc),
                )
            slot.state = loaded
            slot.initialized = True
            slot.generation += 1
            counters = ResidentCounters(committed_state_generations=1)
            slot.counters.add(counters)
            return self._result(
                command_code=command_code,
                status=ResidentStatus.OK,
                sequence_id=sequence_code,
                layer_id=layer_code,
                slot=slot,
                command_counters=counters,
            )

        if not slot.initialized or slot.state is None:
            return self._reject(
                command_code=command_code,
                status=ResidentStatus.UNINITIALIZED_STATE,
                sequence_id=sequence_code,
                layer_id=layer_code,
                slot=slot,
                error_detail=f"{operation.name} requires RESET or LOAD first",
            )

        if operation is ResidentCommand.READBACK:
            return self._result(
                command_code=command_code,
                status=ResidentStatus.OK,
                sequence_id=sequence_code,
                layer_id=layer_code,
                slot=slot,
            )

        try:
            validated_token = self._validate_token(token)
            step_result = recurrence_core_step_encoded(validated_token, slot.state)
        except RuntimeError as exc:
            return self._reject(
                command_code=command_code,
                status=ResidentStatus.SHAPE_MISMATCH,
                sequence_id=sequence_code,
                layer_id=layer_code,
                slot=slot,
                error_detail=str(exc),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            return self._reject(
                command_code=command_code,
                status=ResidentStatus.INVALID_ENCODING,
                sequence_id=sequence_code,
                layer_id=layer_code,
                slot=slot,
                invalid_encoding=True,
                error_detail=str(exc),
            )

        slot.state = _copy_state(step_result.state)
        slot.generation += 1
        counters = ResidentCounters.from_arithmetic(step_result.counters)
        counters.committed_state_generations = 1
        slot.counters.add(counters)
        return self._result(
            command_code=command_code,
            status=ResidentStatus.OK,
            sequence_id=sequence_code,
            layer_id=layer_code,
            slot=slot,
            command_counters=counters,
            step_result=step_result,
        )

    def reset(self, sequence_id: object, layer_id: object) -> ResidentResult:
        return self.execute(ResidentCommand.RESET, sequence_id, layer_id)

    def load(
        self, sequence_id: object, layer_id: object, state: object
    ) -> ResidentResult:
        return self.execute(
            ResidentCommand.LOAD, sequence_id, layer_id, state=state
        )

    def step(
        self, sequence_id: object, layer_id: object, token: object
    ) -> ResidentResult:
        return self.execute(
            ResidentCommand.STEP, sequence_id, layer_id, token=token
        )

    def readback(self, sequence_id: object, layer_id: object) -> ResidentResult:
        return self.execute(ResidentCommand.READBACK, sequence_id, layer_id)
