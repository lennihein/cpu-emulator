from unittest import TestCase

from src.instructions import Instruction, all_instructions
from src.parser import Parser


class ParserTest(TestCase):
    """Test the parser."""

    def test_program(self):
        """Test parsing of a simple program."""
        addi = all_instructions["addi"]
        beq = all_instructions["beq"]

        p = Parser.from_default()
        instrs = p.parse(
            """
            a:
            addi r1, r0, 100
            beq r0, r0, a
            """
        )

        self.assertEqual(
            instrs,
            [
                Instruction(addi, [1, 0, 100]),
                Instruction(beq, [0, 0, 0]),
            ],
        )

    def test_exceptions(self):
        """Test that the correct exceptions are raised on invalid instructions."""
        addi = all_instructions["addi"]
        beq = all_instructions["beq"]

        p = Parser.from_default()
        p.add_instruction(addi)
        p.add_instruction(beq)

        with self.assertRaises(ValueError) as exc:
            p.parse("invalid r0, 0")
        self.assertEqual(str(exc.exception),
                         "Unknown instruction type 'invalid'")

        with self.assertRaises(ValueError) as exc:
            p.parse("addi r0, 0")
        self.assertEqual(
            str(exc.exception),
            "Wrong number of operands for 'addi' instruction: 3 expected, 2 given",
        )
