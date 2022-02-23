"""All the instructions in our instruction set, and the types used to describe them."""

import operator
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Iterable, Literal, NewType, Optional, Union

from .word import Word

OperandKind = Union[Literal["reg"], Literal["imm"], Literal["label"]]

# ID of a register, used as index into the register file
RegID = NewType("RegID", int)


class InstructionKind(ABC):
    """Information about a kind of instruction, e.g. `add reg, reg, reg` or `subi reg, reg, imm`."""

    operand_types: list[OperandKind]
    name: str

    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"<InstructionKind '{self.name} {', '.join(self.operand_types)}'>"

    @abstractmethod
    def sources(self) -> Iterable[int]:
        """Return the indices of all source operands."""

    @abstractmethod
    def destination(self) -> Optional[int]:
        """Return the index of the destination operand, if any."""


class InstrReg(InstructionKind):
    """An ALU instruction that operates solely on registers."""

    operand_types = ["reg", "reg", "reg"]

    # Wrap callable type in `Optional` to prevent `mypy` from mistaking it as a method
    compute_result: Optional[Callable[[Word, Word], Word]]
    cycles: int

    def __init__(self, name: str, compute_result: Callable[[Word, Word], Word], cycles: int = 1):
        super().__init__(name)

        self.compute_result = compute_result
        self.cycles = cycles

    def sources(self) -> Iterable[int]:
        return [1, 2]

    def destination(self) -> Optional[int]:
        return 0


class InstrImm(InstructionKind):
    """An ALU instruction that takes an immediate operand."""

    operand_types = ["reg", "reg", "imm"]

    # Wrap callable type in `Optional` to prevent `mypy` from mistaking it as a method
    compute_result: Optional[Callable[[Word, Word], Word]]
    cycles: int

    def __init__(self, name: str, compute_result: Callable[[Word, Word], Word], cycles: int = 1):
        super().__init__(name)

        self.compute_result = compute_result
        self.cycles = cycles

    def sources(self) -> Iterable[int]:
        return [1, 2]

    def destination(self) -> Optional[int]:
        return 0


class InstrLoad(InstructionKind):
    """A load instruction, loading a word or a zero-extended byte."""

    operand_types = ["reg", "reg", "imm"]

    width_byte: bool

    def __init__(self, name: str, width_byte: bool):
        super().__init__(name)

        self.width_byte = width_byte

    def sources(self) -> Iterable[int]:
        return [1, 2]

    def destination(self) -> Optional[int]:
        return 0

    @property
    def width(self) -> int:
        if self.width_byte:
            return 1
        else:
            return Word.WIDTH_BYTES


class InstrStore(InstructionKind):
    """A store instruction, storing a word or a byte."""

    operand_types = ["reg", "reg", "imm"]

    width_byte: bool

    def __init__(self, name: str, width_byte: bool):
        super().__init__(name)

        self.width_byte = width_byte

    def sources(self) -> Iterable[int]:
        return [1, 2, 0]

    def destination(self) -> Optional[int]:
        return None

    @property
    def width(self) -> int:
        if self.width_byte:
            return 1
        else:
            return Word.WIDTH_BYTES


class InstrFlush(InstructionKind):
    """A flush instruction, flushing a line from the cache."""

    operand_types = ["reg", "imm"]

    width: int

    def __init__(self, name: str):
        super().__init__(name)

        # TODO: Width of cacheline
        self.width = 32

    def sources(self) -> Iterable[int]:
        return [0, 1]

    def destination(self) -> Optional[int]:
        return None


class InstrBranch(InstructionKind):
    """A branch instruction, branching to the destination when the condition is met."""

    operand_types = ["reg", "reg", "label"]

    # Wrap callable type in `Optional` to prevent `mypy` from mistaking it as a method
    condition: Optional[Callable[[Word, Word], bool]]
    cycles: int

    def __init__(self, name: str, condition: Callable[[Word, Word], bool], cycles: int = 1):
        super().__init__(name)

        self.condition = condition
        self.cycles = cycles

    def sources(self) -> Iterable[int]:
        return [0, 1]

    def destination(self) -> Optional[int]:
        return None


class InstrCyclecount(InstructionKind):
    """A cyclecount instruction, reading the cycle counter."""

    operand_types = ["reg"]

    def sources(self) -> Iterable[int]:
        return []

    def destination(self) -> Optional[int]:
        return 0


class InstrFence(InstructionKind):
    """A fence instruction, ordering execution of other instructions."""

    operand_types: list[OperandKind] = []

    def sources(self) -> Iterable[int]:
        return []

    def destination(self) -> Optional[int]:
        return None


@dataclass
class Instruction:
    """A concrete instruction in program code."""

    # TODO: Rename to `kind`
    ty: InstructionKind
    ops: list[int]

    def sources(self) -> Iterable[tuple[int, OperandKind]]:
        """Return value and type of all source operands."""
        for idx in self.ty.sources():
            yield self.ops[idx], self.ty.operand_types[idx]

    def destination(self) -> Optional[RegID]:
        """Return the destination register, if any."""
        idx = self.ty.destination()
        if idx is None:
            return None
        else:
            assert self.ty.operand_types[idx] == "reg"
            return RegID(self.ops[idx])


def _all_instructions() -> Iterable[InstructionKind]:
    """Generate all instructions of our ISA."""
    # ALU instructions, with and without immediate operand
    for name, op in [
        ("add", operator.add),
        ("sub", operator.sub),
        ("sll", operator.lshift),
        ("srl", Word.shift_right_logical),
        ("sra", Word.shift_right_arithmetic),
        ("xor", operator.xor),
        ("or", operator.or_),
        ("and", operator.and_),
    ]:
        yield InstrReg(name, op)
        yield InstrImm(name + "i", op)

    # Memory instructions
    yield InstrLoad("lw", False)
    yield InstrLoad("lb", True)
    yield InstrStore("sw", False)
    yield InstrStore("sb", True)
    yield InstrFlush("flush")

    # Branch instructions
    for name, op in [
        ("beq", operator.eq),
        ("bne", operator.ne),
        ("bltu", Word.unsigned_lt),
        ("bleu", Word.unsigned_le),
        ("bgtu", Word.unsigned_gt),
        ("bgeu", Word.unsigned_ge),
        ("blts", Word.signed_lt),
        ("bles", Word.signed_le),
        ("bgts", Word.signed_gt),
        ("bges", Word.signed_ge),
    ]:
        yield InstrBranch(name, op)

    # Cyclecount instruction
    yield InstrCyclecount("cyclecount")
    # Fence instruction
    yield InstrFence("fence")


all_instructions = dict((instr.name, instr) for instr in _all_instructions())
