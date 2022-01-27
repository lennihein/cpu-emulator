import unittest
from src.frontend import Frontend
import logging, sys

logger = logging.getLogger()
logger.level = logging.DEBUG
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)

class FrontendTest(unittest.TestCase):

    def test_frontend(self):
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

        front = Frontend(cpu_bpu, instrs, 3)
        cpu_bpu.update(2, True)
        with self.assertRaises(Exception) as context:
            front.pop_instruction_from_queue()
        self.assertTrue('instruction queue is empty' in str(context.exception))   
        front.add_instructions_to_queue()
        self.assertTrue("deque([Instruction(ty=<InstructionType 'addi" in str(front.instr_queue))
        front.add_instructions_to_queue()
        self.assertTrue("deque([Instruction(ty=<InstructionType 'addi" in str(front.instr_queue))

        self.assertEqual(front.get_pc(), 0)

        next_instr = front.fetch_instruction_from_queue()
        # self.assertTrue("Instruction(ty=<InstructionType 'addi reg, reg, imm'>, ops=[1, 0, 100])" in str(next_instr))
        # self.assertEqual("deque([Instruction(ty=<InstructionType 'addi reg, reg, imm'>, ops=[1, 0, 99]), Instruction(ty=<InstructionType 'beq reg, reg, label'>, ops=[0, 0, 0])])", str(front.instr_queue))
        
        self.assertEqual(cpu_bpu.counter, [2, 2, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2])

        front.flush_instruction_queue()
        self.assertEqual(str(front.instr_queue), "deque([])")

        # with self.assertRaises(Exception) as context:
        #     front.fetch_instruction_from_queue()
        # self.assertTrue('instruction queue is empty' in str(context.exception))

        cpu_bpu.update(2, False)
        cpu_bpu.update(2, False)

        self.assertEqual(cpu_bpu.counter, [2, 2, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2])

        front.add_instructions_to_queue()
        # self.assertTrue("deque([Instruction(ty=InstructionType(name='addi', operan" in str(front.instr_queue))

        micro_program=list([instructions.Instruction(addi, [1, 1, 2]), instructions.Instruction(beq, [0, 0, 1])])
        front.add_micro_program(micro_program)

        # self.assertTrue("deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 100])," in str(front.instr_queue))

        next_instr = front.fetch_instruction_from_queue()
        next_instr = front.fetch_instruction_from_queue()
        next_instr = front.fetch_instruction_from_queue()

        front.add_instructions_to_queue()
        # self.assertTrue("deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 1, 2])," in str(front.instr_queue))

        next_instr = front.fetch_instruction_from_queue()
        next_instr = front.fetch_instruction_from_queue()

        with self.assertRaises(Exception) as context:
            front.set_pc(-1)
        self.assertTrue('new pc out of range' in str(context.exception))

        with self.assertRaises(Exception) as context:
            front.set_pc(6)
        self.assertTrue('new pc out of range' in str(context.exception))

        front.set_pc(4)

        # with self.assertRaises(Exception) as context:
        #     front.add_instructions_to_queue()
        # self.assertTrue('end of program reached by instruction queue' in str(context.exception))



if __name__ == '__main__':
    unittest.main()
