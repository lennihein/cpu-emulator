from typing import Callable

class Word:
    WIDTH: int = 16
    value: int

    def __init__(self, value: int):
        self.value = value % (1 << self.WIDTH)

    @classmethod
    def from_int(cls, value: int):
        return cls(value)

    @classmethod
    def from_bytes(cls, b: bytes[2]):
        ...

    # careful: operations on differently sized ints results in an object of the lhs type
    # also, we have no idea what happens if you use bitwise operations on a Word and a Byte

    def __add__(self, rhs: "Word"):
        return self.from_int(self.value + rhs.value)

    def __sub__(self, rhs: "Word"):
        return Word(self.value - rhs.value)

    def __lshift__(self, rhs: "Word"):
        return Word(self.value << rhs.value)

    def __rshift__(self, rhs: "Word"):
        return Word(self.value >> rhs.value)

    def __and__(self, rhs: "Word"):
        return Word(self.value & rhs.value)

    def __or__(self, rhs: "Word"):
        return Word(self.value | rhs.value)

    def __xor__(self, rhs: "Word"):
        return Word(self.value ^ rhs.value)

    def __invert__(self):
        return Word(~self.value)

    def __eq__(self, rhs: "Word"):
        return self.value == rhs.value

    def __ne__(self, rhs: "Word"):
        return self.value != rhs.value


class Byte:
    value: int


Operand = ["reg", "imm", "mem", "label"]

class InstructionType:
    name: str
    function: Callable[[Word, Word], Word]
    operands: list[Operand]

    def regregreg(self, function: Callable[[Word, Word], Word], name:str):
        self.name: str = name
        self.function: Callable[[Word, Word], Word] = function

    def __str__(self):
        return self.name


class Instruction:
    type: InstructionType
    

class Parser:

    def parse(src: str) -> list[Instruction]:
        pass


class CPU:
    instructions: dict[str, InstructionType]
    snapshots: list
    
    def add_instruction(inst: InstructionType):
        pass

    # cpu.add_instruction(InstrRegRegReg("add", (lambda a, b: a + b)))
    # cpu.add_instruction(Instruction.regregreg("add", (lambda a, b: a + b)))


class MMU:
    # [Data, Cached]
    memory: list[tuple[Byte, bool]]

    def __init__(self, memSize: int) -> None:
        self.memory = [[None, False]] * memSize
                
    def read_word(self, idx: int) -> tuple[Word, int]:
        pass

    def read_byte(self, idx: int) -> tuple[Byte, int]:
        pass

    def write_word(self, idx: int, data: Word) -> None:
        pass


class GUI:

    cpu: CPU

    def __init__(self, cpu: CPU) -> None:
        self.cpu = cpu
