import logging
import sys
import unittest

from src.instructions import Instruction, InstructionType, addi
from src.parser import Parser

logger = logging.getLogger()
logger.level = logging.DEBUG
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


class parserTests(unittest.TestCase):
    def test_parser(self):

        j = InstructionType("j", None)
        j.operand_types = ["label"]
        p = Parser()

        p.add_instruction(addi)
        p.add_instruction(j)
        instrs = p.parse(
            """a:
                addi r1, r0, 100
                j a
                """
        )

        self.assertTrue(
            instrs
            == [
                Instruction(addi, [1, 0, 100]),
                Instruction(j, [0]),
            ]
        )

        with self.assertRaises(Exception) as context:
            p.parse("invalid r0, 0")
        self.assertTrue("Unknown instruction type" in str(context.exception))

        with self.assertRaises(Exception) as context:
            p.parse("addi r0, 0")
        self.assertTrue("Wrong" in str(context.exception))


if __name__ == "__main__":
    unittest.main()
