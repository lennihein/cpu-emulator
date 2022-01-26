"""
Assembly code parser, used to convert assembly code with labels into a list of instructions.

Before any code can be parsed, the available instruction types have to be registered with the
parser.

Example:
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
"""

from typing import Iterable

from .instructions import Instruction, InstructionType, OperandKind, all_instructions


class Parser:
    """Assembly code parser. Converts assembly code with labels to a list of instructions."""

    _instr_types: dict[str, InstructionType]

    def __init__(self):
        """Create a new parser without knowledge of any instructions."""
        self._instr_types = {}

    @classmethod
    def from_default(cls):
        """Create a new parser with knowledge of our instruction set."""
        p = cls()
        for instr in all_instructions:
            p.add_instruction(instr)
        return p

    @staticmethod
    def _split_instructions(src: str) -> Iterable[str]:
        """Split assembly code into instructions and labels."""
        for line in src.splitlines():
            strip = line.strip()

            if not strip or strip.startswith("//"):
                continue
            yield strip

    @staticmethod
    def _parse_operand(op: str, ty: OperandKind, labels: dict[str, int]) -> int:
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

    def _parse_instruction(self, instr: str, labels: dict[str, int]) -> Instruction:
        """Parse a single instruction."""
        # Split into mnemonic and operands
        name, op = instr.split(maxsplit=1)
        # Split operands
        ops = [x.strip() for x in op.split(",")]

        # Get instruction type
        if name not in self._instr_types:
            raise ValueError(f"Unknown instruction type {name!r}")
        ty = self._instr_types[name]

        # Parse each operand
        if len(ops) != len(ty.operand_types):
            raise ValueError(
                f"Wrong number of operands for {name!r} instruction: "
                + f"{len(ty.operand_types)} expected, {len(ops)} given"
            )
        ops_parsed = [
            self._parse_operand(op, op_ty, labels) for op, op_ty in zip(ops, ty.operand_types)
        ]

        # Create instruction object
        return Instruction(ty, ops_parsed)

    def parse(self, src: str) -> list[Instruction]:
        """Parse assembly code into a list of instructions."""
        # Split by instructions
        split = list(self._split_instructions(src))

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

            instrs.append(self._parse_instruction(instr, labels))
        return instrs

    def add_instruction(self, instr: InstructionType):
        """Add an instruction type to this parser."""
        self._instr_types[instr.name] = instr
