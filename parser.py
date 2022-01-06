"""
Assembly code parser, used to convert assembly code with labels into a list of instructions.

Before any code can be parsed, the available instruction types have to be registered with the
parser.

# Example

>>> addi = InstructionType("addi", ["reg", "reg", "imm"])
>>> j = InstructionType("j", ["label"])
>>> p = Parser()
>>> p.add_instruction(addi)
>>> p.add_instruction(j)
>>> instrs = p.parse('''
...     a:
...     addi r1, r0, 100
...     j a
... ''')
>>> assert instrs == [
...     Instruction(addi, [1, 0, 100]),
...     Instruction(j, [0]),
... ]
>>> p.parse("invalid r0, 0")
Traceback (most recent call last):
    ...
ValueError: Unknown instruction type 'invalid'
>>> p.parse("addi r0, 0")
Traceback (most recent call last):
    ...
ValueError: Wrong number of operands for 'addi' instruction: 3 expected, 2 given
"""

from dataclasses import dataclass
from typing import Callable, Iterable, Literal, Union

from word import Word

Operand = Union[Literal["reg"], Literal["imm"], Literal["label"]]


@dataclass
class InstructionType:
    name: str
    operands: list[Operand]


@dataclass
class InstrReg(InstructionType):
    operands = ["reg", "reg", "reg"]

    result: Callable[[Word, Word], Word]


@dataclass
class InstrImm(InstructionType):
    operands = ["reg", "reg", "imm"]

    result: Callable[[Word, Word], Word]


@dataclass
class InstrBranch(InstructionType):
    operands = ["label", "reg", "reg"]

    condition: Callable[[Word, Word], bool]


@dataclass
class InstrLoad(InstructionType):
    operands = ["reg", "reg", "imm"]

    width: int


@dataclass
class InstrStore(InstructionType):
    operands = ["reg", "reg", "imm"]

    width: int


@dataclass
class Instruction:
    """A concrete instruction in program code."""

    ty: InstructionType
    ops: list[int]


class Parser:
    """Assembly code parser. Converts assembly code with labels to a list of instructions."""

    instructions: dict[str, InstructionType]

    def __init__(self):
        """Create a new parser without knowledge of any instructions."""
        self.instructions = {}

    @staticmethod
    def split_instructions(src: str) -> Iterable[str]:
        """Split assembly code into instructions and labels."""
        for line in src.splitlines():
            strip = line.strip()

            if not strip or strip.startswith("//"):
                continue
            yield strip

    @staticmethod
    def parse_operand(op: str, ty: Operand, labels: dict[str, int]) -> int:
        """Parse a single operand of the given type."""
        if ty == "reg":
            if not op.startswith("r"):
                raise ValueError(f"Unknown register {op!r}")
            return int(op[1:])

        if ty == "imm":
            return int(op, 0)

        if ty == "label":
            return labels[op]

        raise ValueError(f"Unknown operand type {ty!r}")

    def parse_instruction(self, instr: str, labels: dict[str, int]) -> Instruction:
        """Parse a single instruction."""
        # Split into mnemonic and operands
        name, op = instr.split(maxsplit=1)
        # Split operands
        ops = [x.strip() for x in op.split(",")]

        # Get instruction type
        if name not in self.instructions:
            raise ValueError(f"Unknown instruction type {name!r}")
        ty = self.instructions[name]

        # Parse each operand
        if len(ops) != len(ty.operands):
            raise ValueError(
                f"Wrong number of operands for {name!r} instruction: {len(ty.operands)} expected, {len(ops)} given"
            )
        ops_parsed = [self.parse_operand(op, op_ty, labels) for op, op_ty in zip(ops, ty.operands)]

        # Create instruction object
        return Instruction(ty, ops_parsed)

    def parse(self, src: str) -> list[Instruction]:
        """Parse assembly code into a list of instructions."""
        # Split by instructions
        split = list(self.split_instructions(src))

        # First pass to parse all labels
        labels = {}
        i = 0
        for label in split:
            if label.endswith(":"):
                labels[label[:-1]] = i
            else:
                i += 1

        # Second pass to actually parse instructions
        instrs = []
        for instr in split:
            if instr.endswith(":"):
                continue

            instrs.append(self.parse_instruction(instr, labels))
        return instrs

    def add_instruction(self, inst: InstructionType):
        """Add an instruction type to this parser."""
        self.instructions[inst.name] = inst
