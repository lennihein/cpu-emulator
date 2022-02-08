import unittest
from src.frontend import Frontend
import logging
import sys

logger = logging.getLogger()
logger.level = logging.DEBUG
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


class FrontendTest(unittest.TestCase):

    def test_frontend(self):
        #preparations for building a working frontend
        from src import bpu, parser, instructions
        cpu_bpu = bpu.BPU()
        addi = instructions.all_instructions["addi"]
        beq = instructions.all_instructions["beq"]
        p = parser.Parser()
        p.add_instruction(addi)
        p.add_instruction(beq)
        instrs = p.parse('''
            a:
            addi r1, r0, 100
            addi r1, r0, 99
            beq r0, r0, a
            addi r1, r0, 98
            addi r1, r0, 97
        ''')
        cpu_bpu.update(2, True) 

        #build queue
        front = Frontend(cpu_bpu, instrs, 3)

        #check raised errors when queue is empty
        with self.assertRaises(Exception) as context:
            front.pop_instruction_from_queue()
        self.assertTrue('instruction queue is empty' in str(context.exception))
        with self.assertRaises(Exception) as context:
            front.fetch_instruction_from_queue()
        self.assertTrue('instruction queue is empty' in str(context.exception))

        #check that the queue is filled but not overfilled
        front.add_instructions_to_queue()
        self.assertEqual(len(front.instr_queue), 3)
        self.assertIs(front.instr_queue[0], instrs[0])
        self.assertIs(front.instr_queue[1], instrs[1])
        self.assertIs(front.instr_queue[2], instrs[2])

        #check that trying to add instructions to a full queue does not change the queue
        front.add_instructions_to_queue()
        self.assertEqual(len(front.instr_queue), 3)
        self.assertIs(front.instr_queue[0], instrs[0])
        self.assertIs(front.instr_queue[1], instrs[1])
        self.assertIs(front.instr_queue[2], instrs[2])

        #check handling of jump instruction and get_pc function
        self.assertEqual(front.get_pc(), front.pc)
        self.assertEqual(front.get_pc(), 0)

        #fetching should return the first instruction and leave the queue unchanged
        next_instr = front.fetch_instruction_from_queue()
        self.assertIs(next_instr, instrs[0])
        self.assertEqual(len(front.instr_queue), 3)
        self.assertIs(front.instr_queue[0], instrs[0])
        self.assertIs(front.instr_queue[1], instrs[1])
        self.assertIs(front.instr_queue[2], instrs[2])

        #fetching should return the first instruction and remove it from the queue
        next_instr_two = front.pop_instruction_from_queue()
        self.assertIs(next_instr_two, instrs[0])
        self.assertEqual(len(front.instr_queue), 2)
        self.assertIs(front.instr_queue[0], instrs[1])
        self.assertIs(front.instr_queue[1], instrs[2])

        #flushing should empty the queue
        front.flush_instruction_queue()
        self.assertEqual(len(front.instr_queue), 0)

        #check correct handling of branch instruction when no jump is predicted
        cpu_bpu.update(2, False)
        cpu_bpu.update(2, False)
        front.add_instructions_to_queue()
        next_instr_three = front.pop_instruction_from_queue()
        front.add_instructions_to_queue()
        self.assertIs(next_instr_three, instrs[0])
        self.assertEqual(len(front.instr_queue), 3)
        self.assertIs(front.instr_queue[0], instrs[1])
        self.assertIs(front.instr_queue[1], instrs[2])
        self.assertIs(front.instr_queue[2], instrs[3])

        #check handling of µ-progrm
        micro_program = list([instructions.Instruction(
            addi, [1, 1, 2]), instructions.Instruction(beq, [0, 0, 1])])
        front.add_micro_program(micro_program)
        self.assertEqual(len(front.instr_queue), 5)
        self.assertIs(front.instr_queue[0], instrs[1])
        self.assertIs(front.instr_queue[1], instrs[2])
        self.assertIs(front.instr_queue[2], instrs[3])
        self.assertIs(front.instr_queue[3], micro_program[0])
        self.assertIs(front.instr_queue[4], micro_program[1])

        front.add_instructions_to_queue()
        self.assertEqual(len(front.instr_queue), 5)
        self.assertIs(front.instr_queue[0], instrs[1])
        self.assertIs(front.instr_queue[1], instrs[2])
        self.assertIs(front.instr_queue[2], instrs[3])
        self.assertIs(front.instr_queue[3], micro_program[0])
        self.assertIs(front.instr_queue[4], micro_program[1])

        #check jump out of µ-prog
        _ = front.pop_instruction_from_queue()
        _ = front.pop_instruction_from_queue()
        _ = front.pop_instruction_from_queue()
        front.add_instructions_to_queue()
        self.assertEqual(front.get_pc(), 1)
        self.assertEqual(len(front.instr_queue), 3)
        self.assertIs(front.instr_queue[0], micro_program[0])
        self.assertIs(front.instr_queue[1], micro_program[1])
        self.assertIs(front.instr_queue[2], instrs[0])

        #check pc setter
        _ = front.pop_instruction_from_queue()
        _ = front.pop_instruction_from_queue()
        with self.assertRaises(Exception) as context:
            front.set_pc(-1)
        self.assertTrue('new pc out of range' in str(context.exception))
        with self.assertRaises(Exception) as context:
            front.set_pc(6)
        self.assertTrue('new pc out of range' in str(context.exception))
        front.set_pc(4)
        self.assertEqual(front.get_pc(), 4)

        #check handling of the end of the program
        with self.assertRaises(Exception) as context:
             front.add_instructions_to_queue()
        self.assertTrue('end of program reached by instruction queue' in str(context.exception))


if __name__ == '__main__':
    unittest.main()
