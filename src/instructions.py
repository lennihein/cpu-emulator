"""All the instructions in our instruction set, and the types used to describe them."""

import operator
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Iterable, Literal, NewType, Union

from .word import Word

OperandKind = Union[Literal["reg"], Literal["imm"], Literal["label"]]

# ID of a register, used as index into the register file
RegID = NewType("RegID", int)


class InstructionType(ABC):
    """Information about a type of instruction, e.g. `add reg, reg, reg` or `subi reg, reg, imm`."""

    operand_types: list[OperandKind]
    name: str

    @abstractmethod
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"<InstructionType '{self.name} {', '.join(self.operand_types)}'>"


class InstrReg(InstructionType):
    """An ALU instruction that operates solely on registers."""

    operand_types = ["reg", "reg", "reg"]

    compute_result: Callable[[Word, Word], Word]
    cycles: int

    def __init__(self, name, compute_result, cycles=1):
        super().__init__(name)

        self.compute_result = compute_result
        self.cycles = cycles


class InstrImm(InstructionType):
    """An ALU instruction that takes an immediate operand."""

    operand_types = ["reg", "reg", "imm"]

    compute_result: Callable[[Word, Word], Word]
    cycles: int

    def __init__(self, name, compute_result, cycles=1):
        super().__init__(name)

        self.compute_result = compute_result
        self.cycles = cycles


class InstrLoad(InstructionType):
    """A load instruction, loading a word or a zero-extended byte."""

    operand_types = ["reg", "reg", "imm"]

    width_byte: bool

    def __init__(self, name, width_byte):
        super().__init__(name)

        self.width_byte = width_byte


class InstrStore(InstructionType):
    """A store instruction, storing a word or a byte."""

    operand_types = ["reg", "reg", "imm"]

    width_byte: bool

    def __init__(self, name, width_byte):
        super().__init__(name)

        self.width_byte = width_byte


class InstrBranch(InstructionType):
    """A branch instruction, branching to the destination when the condition is met."""

    operand_types = ["reg", "reg", "label"]

    condition: Callable[[Word, Word], bool]
    cycles: int

    def __init__(self, name, condition, cycles=1):
        super().__init__(name)

        self.condition = condition
        self.cycles = cycles


@dataclass
class Instruction:
    """A concrete instruction in program code."""

    ty: InstructionType
    ops: list[int]


def _all_instructions() -> Iterable[InstructionType]:
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


all_instructions = dict((instr.name, instr) for instr in _all_instructions())
