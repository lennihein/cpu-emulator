from typing import Callable

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
