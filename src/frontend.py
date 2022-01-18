"""
Frontend for the CPU instruction management.

Holds and manages a queue of instructions.
Instructions are taken from a list provided by the parser and added to the queue with respect to branch management (bpu).
Instructions can be fetched from the queue, e.g. by reservation stations.
Supports flushing the queue and adding a micro program directly to the queue.

# Example

>>> import bpu
>>> import parser

>>> cpu_bpu = bpu.BPU()
>>> addi = parser.InstructionType("addi", ["reg", "reg", "imm"])
>>> j = parser.InstrBranch("j", ["label"], "condition needed")
>>> p = parser.Parser()
>>> p.add_instruction(addi)
>>> p.add_instruction(j)
>>> instrs = p.parse('''
...     a:
...     addi r1, r0, 100
...     addi r1, r0, 99
...     j a    
...     addi r1, r0, 98
... ''')

>>> front = Frontend(cpu_bpu, instrs, 3)
>>> cpu_bpu.update(2, True)

>>> front.add_instructions_to_queue()
>>> print(front.instr_queue)
deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 100]), Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 99]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[0])])
>>> print(front.get_pc())
0

>>> next_instr = front.fetch_instruction_from_queue()
>>> print(next_instr)
Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 100])
>>> print(front.instr_queue)
deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 99]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[0])])

>>> front.add_instructions_to_queue()
>>> print(front.instr_queue)
deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 99]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[0]), Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 100])])

>>> micro_program=list([parser.Instruction(addi, [1, 1, 2]), parser.Instruction(j, [1])])
>>> front.add_micro_program(micro_program)
>>> print(front.instr_queue)
deque([Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 99]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[0]), Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 0, 100]), Instruction(ty=InstructionType(name='addi', operands=['reg', 'reg', 'imm']), ops=[1, 1, 2]), Instruction(ty=InstrBranch(name='j', operands=['label'], condition='condition needed'), ops=[1])])

>>> front.flush_instruction_queue()
>>> print(front.instr_queue)
deque([])

>>> front.set_pc(4)
>>> front.add_instructions_to_queue()
Error: end of program reached by instruction queue
"""


from . import parser
from . import bpu
from collections import deque



class Frontend:
    '''
    Holds and manages a queue of at most max_length instructions.
    An exception to this max length is made when adding micro programs.
    Expects an already initialised bpu (e.g. shallow copy of the bpu from a surrounding cpu class) and a list of instructions (e.g. as provided by the Parser in paser.py) upon initilisation.
    Max_length can be initialised, too, otherwise a default of 5 is used.
    Uses a program counter pc to keep track of the next instruction from the provided instruction list that should be added to the queue.
    '''

    max_length : int
    pc: int 
    bpu : bpu.BPU

    def __init__(self, cpu_bpu : bpu.BPU, cpu_instr_list, maximum=5) -> None:

        self.max_length = maximum
        self.current_length = 0
        self.pc = 0
        self.bpu = cpu_bpu
        self.instr_list = cpu_instr_list
        self.instr_queue = deque()

    def add_instructions_to_queue(self) -> None:
        '''
        Adds the next instructions from the instruction list, as indicated by the pc, to the queue, until the queue is full.

        Only adds an instruction, if max_langth is not yet reached.
        If the queue is full, the function returns withput further effect.
        Notifies the user if the end of the program is reached, i.e. the pc exceeds the number of instructions in the instr_list.

        If the intruction currently added to the list is of the type InstrBranch, the pc for the next instruction is set 
        according to the label/ number provided by the instruction and the bpu prediction for the branch instruction.
        Important: jump and branching instructions need to be explicitly registered as InstrBranch, not the more generic InstructionType, in the instruction list from the parser.
        For all other instructions, the pc is set to the next instruction in the list.

        Currently, this functions interacts directly with the bpu to get predictions.
        This has to be modified if a branch order buffer should be used.
        '''

        while (len(self.instr_queue) < self.max_length):

            if self.pc >= len(self.instr_list):

                raise IndexError("end of program reached by instruction queue")

            #sanity check, should never happen since the set_pc function checks for this too and jump goals are set by the parser from labels within the code
            if self.pc < 0:
                raise IndexError("pc negative")
            
            current_instr : parser.Instruction = self.instr_list[self.pc]
            self.instr_queue.append(current_instr)

            #this needs to be modified if further jump instruction types are implemented
            if type(current_instr.ty) == parser.InstrBranch:
            
                #true if branch was/ should be taken
                prediction : bool = self.bpu.predict(self.pc)

                if prediction == True:
                    self.pc = current_instr.ops[0]

                else:
                    self.pc = self.pc + 1

            else:            
                
                self.pc = self.pc + 1
        return

    def fetch_instruction_from_queue(self) -> parser.Instruction:
        '''
        Takes the first (current first in) instruction from the instruction queue and returns it.
        '''

        if len(self.instr_queue)>0:
            return self.instr_queue.popleft()

        else:
            #TODO: discuss whether throwing an error makes sense here; can occur in a normal program sequence, e.g. after the queue was flushed
            raise LookupError("instruction queue is empty")
            return None


    def flush_instruction_queue(self) -> None:
        '''
        Empties the queue.
        Does not adjust the pc. This has to be done separately, otherwise the instructions that were flushed from the queue will be silently skipped.
        '''
        self.instr_queue.clear()
        return


    def add_micro_program(self, micro_prog : list[parser.Instruction]) -> None:
        '''
        Adds a list of instructions as a µ-program to the queue.
        The queue is not automatically flushed.
        This can be done separately as a "mitigation" against Meltdown.
        The max_length of the queue is disregarded when adding the µ-program, so µ-programs can be arbitrarily long and added to full queues.
        If the µ-code contains jump instructions, the pc will be set according to the last of these jump instructions.
        '''
        
        for current_instr in micro_prog:

            self.instr_queue.append(current_instr)

            if type(current_instr.ty) == parser.InstrBranch:
        
                self.pc = current_instr.ops[0]
        return

    def set_pc(self, new_pc : int) -> None:
        '''
        Provides an interface to change the program counter to an arbitrary position within the instruction list.
        Does not consider or change the instructions which are already in the instruction queue.
        '''
        if (new_pc >= 0 and new_pc < len(self.instr_list)):

            self.pc = new_pc

        else: 
            raise IndexError ("new pc out of range")

        return

    def get_pc(self) -> int:
        '''
        Interface to retrieve the current value of the program counter.
        '''
        return self.pc
