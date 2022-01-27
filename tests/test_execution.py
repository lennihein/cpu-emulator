from unittest import TestCase

from src.execution import ExecutionEngine
from src.instructions import InstrReg
from src.mmu import MMU
from src.parser import Parser
from src.word import Word


class ExecutionTest(TestCase):
    """Test the Execution Engine."""

    def test_program(self):
        """Test execution of a simple program."""
        code = """
            addi r1, r0, 1
            add r2, r1, r1
            addi r3, r2, 1
            mul r4, r2, r2
            add r5, r2, r3
            sw r4, r0, 0
            sw r5, r2, -2
            sb r1, r3, -2
            lw r6, r0, 0
            sw r4, r5, -5
        """

        # Instruction that takes a long time
        mul = InstrReg("mul", lambda a, b: Word(a.value * b.value), cycles=10)

        # Default instruction set with the additional instruction
        p = Parser.from_default()
        p.add_instruction(mul)

        # Create execution engine with MMU
        rs = ExecutionEngine(MMU(0x1000))

        # Issue all instructions in the code
        for instr in p.parse(code):
            while not rs.try_issue(instr):
                # Tick until slot is ready
                rs.tick()
        # Additional ticks to finish execution
        for _ in range(100):
            rs.tick()

        # Check that the registers have the correct values
        self.assertEqual(rs._registers[:7], [Word(x)
                         for x in (0, 1, 2, 3, 4, 5, 0x105)])