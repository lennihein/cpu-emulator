"""All the instructions in our instruction set, and the types used to describe them."""

import operator
from dataclasses import dataclass
from typing import Callable, Literal, Union

from .word import Word

OperandKind = Union[Literal["reg"], Literal["imm"], Literal["label"]]


class InstructionType:
    """Information about a type of instruction, e.g. `add reg, reg, reg` or `subi reg, reg, imm`."""

    name: str
    operand_types: list[OperandKind]
    compute_result: Callable[..., Word]
    cycles: int

    def __init__(self, name, compute_result, cycles=1):
        self.name = name
        self.compute_result = compute_result
        self.cycles = cycles

    def __repr__(self):
        return f"<InstructionType '{self.name} {', '.join(self.operand_types)}'>"


class InstrReg(InstructionType):
    operand_types = ["reg", "reg", "reg"]

    compute_result: Callable[[Word, Word], Word]


class InstrImm(InstructionType):
    operand_types = ["reg", "reg", "imm"]

    compute_result: Callable[[Word, Word], Word]


class InstrBranch(InstructionType):
    operand_types = ["label", "reg", "reg"]

    condition: Callable[[Word, Word], bool]


class InstrLoad(InstructionType):
    operand_types = ["reg", "reg", "imm"]

    width: int


class InstrStore(InstructionType):
    operand_types = ["reg", "reg", "imm"]

    width: int


@dataclass
class Instruction:
    """A concrete instruction in program code."""

    ty: InstructionType
    ops: list[int]


add = InstrReg("add", operator.add)
sub = InstrReg("sub", operator.sub)
sll = InstrReg("sll", operator.lshift)
srl = InstrReg("srl", Word.shift_right_logical)
sra = InstrReg("sra", Word.shift_right_arithmetic)
xor = InstrReg("xor", operator.xor)
or_ = InstrReg("or", operator.or_)
and_ = InstrReg("and", operator.and_)

addi = InstrImm("addi", operator.add)
subi = InstrImm("subi", operator.sub)
slli = InstrImm("slli", operator.lshift)
srli = InstrImm("srli", Word.shift_right_logical)
srai = InstrImm("srai", Word.shift_right_arithmetic)
xori = InstrImm("xori", operator.xor)
ori = InstrImm("ori", operator.or_)
andi = InstrImm("andi", operator.and_)

all_instructions = [
    add,
    sub,
    sll,
    srl,
    sra,
    xor,
    or_,
    and_,
    addi,
    subi,
    slli,
    srli,
    srai,
    xori,
    ori,
    andi,
]
