from unittest import TestCase

from benedict import benedict as bd
from src.bpu import BPU
from src.execution import ExecutionEngine
from src.instructions import InstrReg
from src.memory import MemorySubsystem
from src.parser import Parser
from src.word import Word


class ExecutionTest(TestCase):
    """Test the Execution Engine."""

    def test_program(self):
        """Test execution of a simple program."""
        code = """
            // Set r1 to 1
            addi r1, r0, 1
            // Set r2 to 2
            add r2, r1, r1
            // Set r3 to 3
            addi r3, r2, 1
            // Set r4 to 4
            mul r4, r2, r2
            // Set r5 to 5
            add r5, r2, r3
            // Store 4 to address 0
            sw r4, r0, 0
            // Store 5 to address 0
            sw r5, r2, -2
            // Overwrite to 0x0105
            sb r1, r3, -2
            // Load 0x105 into r6
            lw r6, r0, 0
            // Store 4 to address 0
            sw r4, r5, -5
            // Execute fence and query cycle counter
            fence
            rdtsc r10
            // Flush address 0, flush all
            flush r0, 0
            flushall
        """

        # Instruction that takes a long time
        mul = InstrReg("mul", lambda a, b: Word(a.value * b.value), cycles=10)

        # Default instruction set with the additional instruction
        p = Parser.from_default()
        p.add_instruction(mul)

        # Create execution engine with MS and BPU
        config = bd.from_yaml("config.yml")
        exe = ExecutionEngine(MemorySubsystem(config), BPU(config), config)

        # Issue all instructions in the code
        for pc, instr in enumerate(p.parse(code)):
            while not exe.try_issue(instr, pc):
                # Tick until slot is ready
                exe.tick()
        # Additional ticks to finish execution
        for _ in range(100):
            exe.tick()

        # Check that the registers have the correct values
        target = (0, 1, 2, 3, 4, 5, 0x105)
        self.assertEqual(exe._registers[: len(target)], [Word(x) for x in target])
