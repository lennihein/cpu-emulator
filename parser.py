from typing import Callable, Iterable, Literal, Union

Operand = Union[Literal["reg"], Literal["imm"], Literal["label"]]
Word = int


class InstructionType:
    name: str
    operands: list[Operand]


class InstrReg(InstructionType):
    operands = ["reg", "reg", "reg"]

    result: Callable[[Word, Word], Word]


class InstrImm(InstructionType):
    operands = ["reg", "reg", "imm"]

    result: Callable[[Word, Word], Word]


class InstrBranch(InstructionType):
    operands = ["label", "reg", "reg"]

    condition: Callable[[Word, Word], bool]


class InstrLoad(InstructionType):
    operands = ["reg", "reg", "imm"]

    width: int


class InstrStore(InstructionType):
    operands = ["reg", "reg", "imm"]

    width: int


class Instruction:
    ty: InstructionType
    ops: list[int]

    def __init__(self, ty: InstructionType, ops: list[int]):
        self.ty = ty
        self.ops = ops


class Parser:
    instructions: dict[str, InstructionType]

    def __init__(self):
        self.instructions = {}

    @staticmethod
    def split_instructions(src: str) -> Iterable[str]:
        for line in src.splitlines():
            strip = line.strip()

            if not strip or strip.startswith("//"):
                continue
            yield strip

    @staticmethod
    def parse_operand(op: str, ty: Operand, labels: dict[str, int]) -> int:
        if ty == "reg":
            if not op.startswith("r"):
                raise ValueError(f"Unknown register {op:r}")
            return int(op[1:])

        if ty == "imm":
            return int(op, 0)

        if ty == "label":
            return labels[op]

        raise ValueError(f"Unknown operand type {ty:r}")

    def parse_instruction(self, instr: str, labels: dict[str, int]) -> Instruction:
        # Split into mnemonic and operands
        name, op = instr.split(maxsplit=1)
        # Split operands
        ops = [x.strip() for x in op.split(",")]

        # Get instruction type
        ty = self.instructions[name]

        # Parse each operand
        assert len(ops) == len(ty.operands)
        ops_parsed = [self.parse_operand(op, op_ty, labels) for op, op_ty in zip(ops, ty.operands)]

        # Create instruction object
        return Instruction(ty, ops_parsed)

    def parse(self, src: str) -> list[Instruction]:
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
        self.instructions[inst.name] = inst

    # cpu.add_instruction(InstrRegRegReg("add", (lambda a, b: a + b)))
    # cpu.add_instruction(Instruction.regregreg("add", (lambda a, b: a + b)))
